"""
Clinic photos of an exercise, front and side (EL-D-004).
"""

from __future__ import annotations

import io
import os
import uuid

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.exercise_photo import ExercisePhoto
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission
from app.services import exercise_photos, prescription_pdf, prescription_service

pytestmark = pytest.mark.asyncio
API = settings.API_V1_PREFIX


def _jpeg(size=(2400, 1800), color=(200, 40, 40), gps=False) -> bytes:
    img = Image.new("RGB", size, color)
    out = io.BytesIO()
    if gps:
        exif = Image.Exif()
        exif[0x010F] = "PhoneMaker"  # Make
        exif[0x8825] = {1: "N", 2: (28.0, 36.0, 0.0)}  # GPS IFD
        img.save(out, format="JPEG", exif=exif)
    else:
        img.save(out, format="JPEG")
    return out.getvalue()


def _png_rgba(size=(400, 300)) -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", size, (10, 120, 80, 0)).save(out, format="PNG")
    return out.getvalue()


# ---------------------------------------------------------------- processing


async def test_process_strips_exif_and_caps_size() -> None:
    raw = _jpeg(gps=True)
    with Image.open(io.BytesIO(raw)) as src:
        assert src.getexif()  # the input really has EXIF
    out = exercise_photos.process_upload(raw)
    with Image.open(io.BytesIO(out.data)) as img:
        assert img.format == "JPEG"
        assert max(img.size) == exercise_photos.MAX_SIDE_PX
        assert (img.width, img.height) == (out.width, out.height)
        assert not img.getexif()
        assert "exif" not in img.info


async def test_process_png_with_transparency_becomes_jpeg() -> None:
    out = exercise_photos.process_upload(_png_rgba())
    with Image.open(io.BytesIO(out.data)) as img:
        assert img.format == "JPEG" and img.mode == "RGB" and img.size == (400, 300)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"", "empty"),
        (b"hello, not a photo", "not a readable photo"),
        (_jpeg(size=(150, 900)), "too small"),
    ],
)
async def test_process_refuses_bad_files(raw: bytes, message: str) -> None:
    with pytest.raises(exercise_photos.PhotoError, match=message):
        exercise_photos.process_upload(raw)


async def test_process_refuses_gif_and_oversize(monkeypatch: pytest.MonkeyPatch) -> None:
    gif = io.BytesIO()
    Image.new("RGB", (400, 400)).save(gif, format="GIF")
    with pytest.raises(exercise_photos.PhotoError, match="JPG, PNG or WebP"):
        exercise_photos.process_upload(gif.getvalue())
    monkeypatch.setattr(exercise_photos, "MAX_UPLOAD_BYTES", 1000)
    with pytest.raises(exercise_photos.PhotoError, match="10 MB"):
        exercise_photos.process_upload(_jpeg())


# ---------------------------------------------------------------- API


async def _clinic(db: AsyncSession, role: UserRole = UserRole.ADMIN, clinic: Clinic | None = None):
    if clinic is None:
        clinic = Clinic(name=f"Photo Clinic {uuid.uuid4().hex[:6]}")
        db.add(clinic)
        await db.flush()
        for product in ("exercise-library", "exercise-prescription"):
            db.add(WorkspaceProduct(clinic_id=clinic.id, product_id=product, status=EntitlementStatus.ENABLED))
    user = User(
        id=uuid.uuid4(), clinic_id=clinic.id, email=f"ph-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=role, first_name="Asha", last_name="Rao", is_active=True,
    )
    db.add(user)
    await db.flush()
    db.add(Membership(user_id=user.id, clinic_id=clinic.id, role=role))
    await db.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=role.value)
    return clinic, user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def local_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EXERCISE_PHOTOS_LOCAL_DIR", str(tmp_path))
    return tmp_path


async def _global_exercise(db: AsyncSession, title="Photo Global") -> uuid.UUID:
    ex = Exercise(clinic_id=None, title=f"{title} {uuid.uuid4().hex[:6]}", body_part="Neck", is_free=True)
    db.add(ex)
    await db.flush()
    ex_id = ex.id
    await db.commit()
    return ex_id


def _files(raw: bytes, name="photo.jpg", ctype="image/jpeg"):
    return {"file": (name, raw, ctype)}


async def _count(db: AsyncSession, **where) -> int:
    q = select(func.count()).select_from(ExercisePhoto)
    for k, v in where.items():
        q = q.where(getattr(ExercisePhoto, k) == v)
    return (await db.execute(q)).scalar_one()


async def test_upload_view_list_replace_delete(
    client: AsyncClient, db_session: AsyncSession, local_dir
) -> None:
    clinic, user, headers = await _clinic(db_session)
    clinic_id, user_id = clinic.id, user.id
    ex_id = await _global_exercise(db_session)

    up = await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=headers, files=_files(_jpeg(gps=True)))
    assert up.status_code == 200, up.text
    assert up.json()["data"]["angle"] == "front"
    assert up.json()["data"]["width"] == 1600

    db_session.expire_all()
    row = (await db_session.execute(select(ExercisePhoto).where(ExercisePhoto.exercise_id == ex_id))).scalar_one()
    assert row.clinic_id == clinic_id and row.uploaded_by == user_id
    assert row.storage_key.startswith(f"local:exercise-photos/{clinic_id}/{ex_id}/front-")
    first_key = row.storage_key
    first_file = os.path.join(local_dir, first_key[len("local:"):])
    assert os.path.exists(first_file)

    got = await client.get(f"{API}/exercises/{ex_id}/photos/front", headers=headers)
    assert got.status_code == 200 and got.headers["content-type"] == "image/jpeg"
    assert got.headers["cache-control"].startswith("private")
    with Image.open(io.BytesIO(got.content)) as img:
        assert not img.getexif()

    detail = await client.get(f"{API}/exercises/{ex_id}", headers=headers)
    assert [p["angle"] for p in detail.json()["data"]["photos"]] == ["front"]

    side = await client.put(f"{API}/exercises/{ex_id}/photos/side", headers=headers, files=_files(_png_rgba(), "s.png", "image/png"))
    assert side.status_code == 200
    listing = await client.get(f"{API}/exercises", headers=headers, params={"search": "Photo Global", "page_size": 100})
    rows = {r["id"]: r for r in listing.json()["data"]}
    assert [p["angle"] for p in rows[str(ex_id)]["photos"]] == ["front", "side"]

    # Replace: still one front row, old file removed, new file there.
    again = await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=headers, files=_files(_jpeg(color=(0, 0, 200))))
    assert again.status_code == 200
    db_session.expire_all()
    assert await _count(db_session, exercise_id=ex_id, angle="front") == 1
    new_row = (await db_session.execute(select(ExercisePhoto).where(ExercisePhoto.exercise_id == ex_id, ExercisePhoto.angle == "front"))).scalar_one()
    assert new_row.storage_key != first_key
    assert not os.path.exists(first_file)
    assert os.path.exists(os.path.join(local_dir, new_row.storage_key[len("local:"):]))

    # Delete.
    gone = await client.delete(f"{API}/exercises/{ex_id}/photos/front", headers=headers)
    assert gone.status_code == 200
    db_session.expire_all()
    assert await _count(db_session, exercise_id=ex_id, angle="front") == 0
    assert (await client.get(f"{API}/exercises/{ex_id}/photos/front", headers=headers)).status_code == 404
    assert (await client.delete(f"{API}/exercises/{ex_id}/photos/front", headers=headers)).status_code == 404


async def test_other_clinic_never_sees_photos(
    client: AsyncClient, db_session: AsyncSession, local_dir
) -> None:
    _c1, _u1, h1 = await _clinic(db_session)
    _c2, _u2, h2 = await _clinic(db_session)
    ex_id = await _global_exercise(db_session, "Photo Shared")
    assert (await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=h1, files=_files(_jpeg()))).status_code == 200

    assert (await client.get(f"{API}/exercises/{ex_id}/photos/front", headers=h2)).status_code == 404
    detail = await client.get(f"{API}/exercises/{ex_id}", headers=h2)
    assert detail.status_code == 200 and detail.json()["data"]["photos"] == []
    assert (await client.delete(f"{API}/exercises/{ex_id}/photos/front", headers=h2)).status_code == 404
    db_session.expire_all()
    assert await _count(db_session, exercise_id=ex_id) == 1


async def test_cannot_add_photo_to_another_clinics_exercise(
    client: AsyncClient, db_session: AsyncSession, local_dir
) -> None:
    c1, _u1, _h1 = await _clinic(db_session)
    _c2, _u2, h2 = await _clinic(db_session)
    own = Exercise(clinic_id=c1.id, title="Private one", body_part="Knee", is_free=True)
    db_session.add(own)
    await db_session.flush()
    own_id = own.id
    await db_session.commit()
    resp = await client.put(f"{API}/exercises/{own_id}/photos/front", headers=h2, files=_files(_jpeg()))
    assert resp.status_code == 404
    db_session.expire_all()
    assert await _count(db_session, exercise_id=own_id) == 0


async def test_bad_input_and_permissions(
    client: AsyncClient, db_session: AsyncSession, local_dir
) -> None:
    clinic, _u, headers = await _clinic(db_session)
    ex_id = await _global_exercise(db_session)
    assert (await client.put(f"{API}/exercises/{ex_id}/photos/back", headers=headers, files=_files(_jpeg()))).status_code == 422
    bad = await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=headers, files=_files(b"not an image", "x.jpg"))
    assert bad.status_code == 422 and "readable photo" in bad.text
    assert (await client.put(f"{API}/exercises/{uuid.uuid4()}/photos/front", headers=headers, files=_files(_jpeg()))).status_code == 404

    # A therapist with view only can see photos but not add them.
    _c, therapist, th_headers = await _clinic(db_session, UserRole.THERAPIST, clinic=clinic)
    db_session.add(UserPermission(user_id=therapist.id, clinic_id=clinic.id,
                                  capability_key="exercises.view", scope=CapabilityScope.ALL))
    await db_session.commit()
    assert (await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=th_headers, files=_files(_jpeg()))).status_code == 403
    assert (await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=headers, files=_files(_jpeg()))).status_code == 200
    assert (await client.get(f"{API}/exercises/{ex_id}/photos/front", headers=th_headers)).status_code == 200
    assert (await client.delete(f"{API}/exercises/{ex_id}/photos/front", headers=th_headers)).status_code == 403

    # Given exercises.edit by the admin, the therapist can add photos.
    db_session.add(UserPermission(user_id=therapist.id, clinic_id=clinic.id,
                                  capability_key="exercises.edit", scope=CapabilityScope.ALL))
    await db_session.commit()
    assert (await client.put(f"{API}/exercises/{ex_id}/photos/side", headers=th_headers, files=_files(_jpeg()))).status_code == 200


class _FakeBucket:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def upload_file(self, path, data, content_type):
        assert content_type == "image/jpeg"
        self.files[path] = data
        return path

    def download_file(self, path):
        from app.core.storage import StorageUnavailableError

        if path not in self.files:
            raise StorageUnavailableError()
        return self.files[path]

    def delete_file(self, path):
        self.deleted.append(path)
        self.files.pop(path, None)


async def test_bucket_storage_and_no_silent_local_fallback(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("EXERCISE_PHOTOS_LOCAL_DIR", raising=False)
    clinic, _u, headers = await _clinic(db_session)
    clinic_id = clinic.id
    ex_id = await _global_exercise(db_session)

    # No storage: clear 503, nothing saved.
    monkeypatch.setattr(exercise_photos, "_storage_client", lambda: None)
    resp = await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=headers, files=_files(_jpeg()))
    assert resp.status_code == 503
    db_session.expire_all()
    assert await _count(db_session, exercise_id=ex_id) == 0

    bucket = _FakeBucket()
    monkeypatch.setattr(exercise_photos, "_storage_client", lambda: bucket)
    assert (await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=headers, files=_files(_jpeg()))).status_code == 200
    [key] = list(bucket.files)
    assert key.startswith(f"exercise-photos/{clinic_id}/{ex_id}/front-") and key.endswith(".jpg")
    assert (await client.get(f"{API}/exercises/{ex_id}/photos/front", headers=headers)).content == bucket.files[key]

    assert (await client.put(f"{API}/exercises/{ex_id}/photos/front", headers=headers, files=_files(_jpeg(color=(1, 2, 3))))).status_code == 200
    assert bucket.deleted == [key] and key not in bucket.files and len(bucket.files) == 1

    # File gone from the bucket: 503, not a crash.
    bucket.files.clear()
    assert (await client.get(f"{API}/exercises/{ex_id}/photos/front", headers=headers)).status_code == 503


async def test_pdf_uses_clinic_photos(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, local_dir
) -> None:
    monkeypatch.setattr(prescription_service, "_storage_client", lambda: None)
    asked: list[list[str]] = []

    async def fake_embed(urls, transport=None):
        asked.append(list(urls))
        return {u: "" for u in urls}

    monkeypatch.setattr(prescription_pdf, "embed_images", fake_embed)
    seen: list[str] = []
    real_render = prescription_pdf._render
    monkeypatch.setattr(prescription_pdf, "_render", lambda h: (seen.append(h), real_render(h))[1])

    clinic, _u, headers = await _clinic(db_session)
    patient = Patient(clinic_id=clinic.id, first_name="Priya", last_name="Sharma", phone="9876543210")
    with_photos = Exercise(clinic_id=None, title="Has photos", body_part="Neck", is_free=True,
                           video_url="https://blogger.googleusercontent.com/img/a")
    without = Exercise(clinic_id=None, title="No photos", body_part="Hip", is_free=True,
                       video_url="https://blogger.googleusercontent.com/img/b")
    db_session.add_all([patient, with_photos, without])
    await db_session.flush()
    ids = (patient.id, with_photos.id, without.id)
    await db_session.commit()
    for angle in ("front", "side"):
        assert (await client.put(f"{API}/exercises/{ids[1]}/photos/{angle}", headers=headers, files=_files(_jpeg()))).status_code == 200

    rx = await client.post(f"{API}/prescriptions", headers=headers, json={
        "patient_id": str(ids[0]),
        "items": [{"exercise_id": str(i), "sets": 3, "reps": 10, "hold": 0, "frequency": "Once daily"} for i in ids[1:]],
    })
    assert rx.status_code == 201, rx.text
    gen = await client.post(f"{API}/prescriptions/{rx.json()['data']['id']}/pdf", headers=headers)
    assert gen.status_code == 200, gen.text
    # Library picture fetched only for the exercise without clinic photos.
    assert asked == [["https://blogger.googleusercontent.com/img/b"]]
    html_out = seen[0]
    assert html_out.count('<img class="photo" src="data:image/jpeg;base64,') == 2
    assert 'class="ex-img two"' in html_out
