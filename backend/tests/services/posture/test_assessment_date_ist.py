"""
Assessed-on date and report ID in IST, not the server's UTC date
(17 Nov 2026). Prod run at 01:44 IST on 17 Nov printed 16 Nov.
"""

import io
from datetime import datetime, timezone

from PIL import Image

from app.api.v1 import posture
from app.services.posture.schemas import Landmark

W, H = 600, 1000


class _At0144IST(datetime):
    @classmethod
    def now(cls, tz=None):
        utc = datetime(2026, 11, 16, 20, 14, tzinfo=timezone.utc)  # 01:44 IST, 17 Nov
        return utc.astimezone(tz) if tz else utc.replace(tzinfo=None)


def _view(points: dict[int, tuple[float, float]]) -> posture.DetectedView:
    out = io.BytesIO()
    Image.new("RGB", (W, H), (220, 220, 220)).save(out, format="JPEG")
    lms = [Landmark(i, *points.get(i, (0.5, 0.5)), 0.0, 0.95) for i in range(33)]
    return posture.DetectedView(lms, W, H, out.getvalue())


def _standing() -> dict[int, tuple[float, float]]:
    p = {0: (0.5, 0.11)}
    for left, right, dx, y in [(1, 4, .02, .10), (2, 5, .03, .10), (3, 6, .04, .10), (7, 8, .06, .11),
                               (9, 10, .02, .13), (11, 12, .17, .21), (13, 14, .2, .36), (15, 16, .21, .49),
                               (17, 18, .21, .51), (19, 20, .21, .51), (21, 22, .21, .51), (23, 24, .1, .5),
                               (25, 26, .1, .7), (27, 28, .1, .89), (29, 30, .1, .9), (31, 32, .11, .92)]:
        p[left], p[right] = (0.5 + dx, y), (0.5 - dx, y)
    return p


def test_report_date_and_id_are_ist(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(posture, "datetime", _At0144IST)
    side = _standing()
    for i in (2, 5, 8, 12, 14, 16, 24, 26, 28, 30, 32):
        side[i] = side[i - 1] if i % 2 == 0 else side[i]
    report = posture._report_from_points(
        side=_view(side), front=_view(_standing()), back=_view(_standing()),
        patient_name="Sample Patient", age=30, gender="", case_ref="", patient_height_cm=170.0,
        clinician_name="", front_source="camera", side_source="camera", back_source="camera",
    )
    assert report["patient"]["assessmentDate"] == "2026-11-17"
    assert report["reportId"].startswith("PT-20261117-")


def test_no_server_local_date_left_in_the_route():
    import inspect

    assert "date.today()" not in inspect.getsource(posture)
