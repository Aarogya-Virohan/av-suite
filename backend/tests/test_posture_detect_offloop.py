"""POS-10 (24 Nov 2026): POST /posture/detect runs off the event loop.

MediaPipe and OpenCV hold no await points, so run directly in the route they
froze every other request for the whole detection (pipeline report, 24 Nov).
The route now hands the work to a worker thread; the models sit behind a lock
because MediaPipe's graphs are not safe to call from two threads at once.
"""

from __future__ import annotations

import asyncio
import threading
import time

import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import posture as posture_api
from app.enums.user import UserRole
from app.services.posture import detector
from tests.test_posture_auth import make_user

pytestmark = pytest.mark.asyncio

URL = "/api/v1/posture/detect"


async def _ticker(gaps: list[float], stop: asyncio.Event) -> None:
    last = time.perf_counter()
    while not stop.is_set():
        await asyncio.sleep(0.01)
        now = time.perf_counter()
        gaps.append(now - last)
        last = now


async def test_detect_does_not_block_the_event_loop(client: AsyncClient, db_session: AsyncSession, monkeypatch):
    def slow_detect(*_a):
        time.sleep(0.6)  # stands in for three MediaPipe passes
        return {"detectionToken": "t", "views": {}}

    monkeypatch.setattr(posture_api, "_detect_all", slow_detect)
    headers = await make_user(db_session, role=UserRole.ADMIN)
    files = {k: (f"{k}.jpg", b"x", "image/jpeg") for k in ("front_image", "side_image", "back_image")}

    gaps: list[float] = []
    stop = asyncio.Event()
    ticker = asyncio.create_task(_ticker(gaps, stop))
    response = await client.post(URL, headers=headers, files=files)
    stop.set()
    await ticker

    assert response.status_code == 200 and response.json()["detectionToken"] == "t"
    # Blocked loop: one gap of about 0.6 s. Free loop: the 10 ms ticks keep coming.
    assert max(gaps) < 0.25, f"event loop stalled for {max(gaps):.2f}s"


async def test_a_detect_error_keeps_its_422_across_the_thread(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    files = {k: (f"{k}.jpg", b"not an image", "image/jpeg") for k in ("front_image", "side_image", "back_image")}
    response = await client.post(URL, headers=headers, files=files)
    assert response.status_code == 422
    assert "image: pose detection failed" in response.json()["detail"]


def test_models_are_never_entered_by_two_threads_at_once(monkeypatch):
    inside = 0
    overlap = 0
    guard = threading.Lock()

    class FakePose:
        def process(self, _rgb):
            nonlocal inside, overlap
            with guard:
                inside += 1
                overlap = max(overlap, inside)
            time.sleep(0.05)
            with guard:
                inside -= 1
            return type("R", (), {"pose_landmarks": None})()

    monkeypatch.setattr(detector, "pose", FakePose())
    monkeypatch.setattr(detector, "decode_image_bytes", lambda _b: np.zeros((8, 8, 3), dtype=np.uint8))

    def run():
        try:
            detector.detect_pose_full(b"x")
        except ValueError:
            pass  # "No person detected" from the fake

    threads = [threading.Thread(target=run) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert overlap == 1
