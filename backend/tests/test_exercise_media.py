"""
Exercise media split (EL-D-003): the stored link in `video_url` is read as a
picture or a demo video. Nothing in the database changes.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.services import exercise_media, prescription_pdf, prescription_service

pytestmark = pytest.mark.asyncio

BLOGGER = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh/s1600/neck.png"
BLOGGER_NO_EXT = "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh"
VIDEO = "https://media.example.org/clinic/hamstring-stretch.mp4"


@pytest.mark.parametrize(
    ("stored", "image", "video"),
    [
        (BLOGGER, BLOGGER, None),
        (BLOGGER_NO_EXT, BLOGGER_NO_EXT, None),
        ("  " + BLOGGER_NO_EXT + "  ", BLOGGER_NO_EXT, None),
        (VIDEO, None, VIDEO),
        ("https://cdn.test/a/b.MOV?token=1", None, "https://cdn.test/a/b.MOV?token=1"),
        ("https://cdn.test/stream/index.m3u8", None, "https://cdn.test/stream/index.m3u8"),
        ("https://cdn.test/clip.webm#t=3", None, "https://cdn.test/clip.webm#t=3"),
        ("https://www.youtube.com/watch?v=abc", None, "https://www.youtube.com/watch?v=abc"),
        ("https://youtu.be/abc", None, "https://youtu.be/abc"),
        ("https://player.vimeo.com/video/1", None, "https://player.vimeo.com/video/1"),
        # A picture whose query mentions mp4 is still a picture.
        ("https://cdn.test/thumb.jpg?src=a.mp4", "https://cdn.test/thumb.jpg?src=a.mp4", None),
        # A host that only contains a video host name is not that host.
        ("https://notyoutube.com/x.png", "https://notyoutube.com/x.png", None),
        ("hamstring.mp4", None, None),
        ("/static/videos/hamstring.mp4", None, None),
        ("http://cdn.test/a.png", None, None),
        ("http://cdn.test/a.mp4", None, None),
        ("data:image/png;base64,AAAA", None, None),
        ("javascript:alert(1)", None, None),
        ("https://", None, None),
        ("", None, None),
        (None, None, None),
    ],
)
async def test_split_rules(stored, image, video) -> None:
    assert exercise_media.image_url(stored) == image
    assert exercise_media.demo_video_url(stored) == video


async def _clinic(db: AsyncSession):
    clinic = Clinic(name=f"Media Clinic {uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(), clinic_id=None, email=f"media-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=UserRole.ADMIN, first_name="Asha", last_name="Rao", is_active=True,
    )
    db.add_all([clinic, user])
    await db.flush()
    user.clinic_id = clinic.id
    db.add(Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN))
    for product in ("exercise-library", "exercise-prescription"):
        db.add(WorkspaceProduct(clinic_id=clinic.id, product_id=product, status=EntitlementStatus.ENABLED))
    await db.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=UserRole.ADMIN.value)
    return clinic, {"Authorization": f"Bearer {token}"}


async def test_api_returns_split_fields_and_keeps_video_url(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic, headers = await _clinic(db_session)
    pic = Exercise(clinic_id=clinic.id, title="Media pic", body_part="Neck", is_free=True, video_url=BLOGGER_NO_EXT)
    vid = Exercise(clinic_id=clinic.id, title="Media vid", body_part="Neck", is_free=True, video_url=VIDEO)
    none = Exercise(clinic_id=clinic.id, title="Media none", body_part="Neck", is_free=True, video_url="hamstring.mp4")
    db_session.add_all([pic, vid, none])
    await db_session.flush()
    vid_id = vid.id
    await db_session.commit()

    resp = await client.get(
        f"{settings.API_V1_PREFIX}/exercises", headers=headers, params={"search": "Media", "limit": 100}
    )
    assert resp.status_code == 200, resp.text
    rows = {r["title"]: r for r in resp.json()["data"]}
    assert set(rows) >= {"Media pic", "Media vid", "Media none"}
    assert rows["Media pic"]["image_url"] == BLOGGER_NO_EXT and rows["Media pic"]["demo_video_url"] is None
    assert rows["Media vid"]["image_url"] is None and rows["Media vid"]["demo_video_url"] == VIDEO
    assert rows["Media none"]["image_url"] is None and rows["Media none"]["demo_video_url"] is None
    # Old field untouched for existing clients.
    assert rows["Media vid"]["video_url"] == VIDEO
    assert rows["Media none"]["video_url"] == "hamstring.mp4"

    one = await client.get(f"{settings.API_V1_PREFIX}/exercises/{vid_id}", headers=headers)
    assert one.status_code == 200
    assert one.json()["data"]["demo_video_url"] == VIDEO

    # Database unchanged.
    db_session.expire_all()
    assert (await db_session.get(Exercise, vid_id)).video_url == VIDEO


async def test_create_and_update_ignore_computed_fields(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _clinic_row, headers = await _clinic(db_session)
    created = await client.post(
        f"{settings.API_V1_PREFIX}/exercises",
        headers=headers,
        json={"title": "Posted", "body_part": "Knee", "is_free": True, "video_url": VIDEO,
              "image_url": "https://evil.test/x.png"},
    )
    assert created.status_code in (200, 201), created.text
    data = created.json()["data"]
    assert data["image_url"] is None and data["demo_video_url"] == VIDEO
    stored = await db_session.get(Exercise, uuid.UUID(data["id"]))
    assert stored.video_url == VIDEO


async def test_pdf_never_downloads_video_links(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prescription_service, "_storage_client", lambda: None)
    asked: list[list[str]] = []

    async def fake_embed(urls, transport=None):
        asked.append(list(urls))
        return {u: "" for u in urls}

    monkeypatch.setattr(prescription_pdf, "embed_images", fake_embed)
    clinic, headers = await _clinic(db_session)
    patient = Patient(clinic_id=clinic.id, first_name="Priya", last_name="Sharma", phone="9876543210")
    pic = Exercise(clinic_id=clinic.id, title="Pic", body_part="Neck", is_free=True, video_url=BLOGGER)
    vid = Exercise(clinic_id=clinic.id, title="Vid", body_part="Hip", is_free=True, video_url=VIDEO)
    db_session.add_all([patient, pic, vid])
    await db_session.commit()

    rx = await client.post(
        f"{settings.API_V1_PREFIX}/prescriptions",
        headers=headers,
        json={"patient_id": str(patient.id), "items": [
            {"exercise_id": str(pic.id), "sets": 3, "reps": 10, "hold": 0, "frequency": "Once daily"},
            {"exercise_id": str(vid.id), "sets": 3, "reps": 10, "hold": 0, "frequency": "Once daily"},
        ]},
    )
    assert rx.status_code == 201, rx.text
    gen = await client.post(
        f"{settings.API_V1_PREFIX}/prescriptions/{rx.json()['data']['id']}/pdf", headers=headers
    )
    assert gen.status_code == 200, gen.text
    assert asked == [[BLOGGER]]
