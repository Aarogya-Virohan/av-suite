"""
A clinic's own exercise photos (front and side), answer 2A of 27 Oct 2026.

Rules:
- Only the clinic that added a photo can see it. Every query filters by the
  caller's clinic, and the photo is served only through an authenticated
  endpoint (no public link).
- Uploads are decoded and re-encoded as JPEG with Pillow: EXIF data (GPS,
  camera, time) is dropped, the long side is capped, and anything that is not
  a readable raster image is refused.
- Files go to the private storage bucket. Railway's disk is wiped on every
  deploy, so there is no silent local fallback: when storage is not available
  the upload fails with a clear error. `EXERCISE_PHOTOS_LOCAL_DIR` (unset in
  production) lets local runs keep photos on disk instead.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise_photo import PHOTO_ANGLES, ExercisePhoto

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SIDE_PX = 1600
MIN_SIDE_PX = 200
JPEG_QUALITY = 85
STORAGE_PREFIX = "exercise-photos"
LOCAL_PREFIX = "local:"


class PhotoError(ValueError):
    """The upload cannot be used; the message is safe to show to the user."""


class PhotoStorageUnavailable(RuntimeError):
    pass


@dataclass
class ProcessedPhoto:
    data: bytes
    width: int
    height: int


def process_upload(raw: bytes) -> ProcessedPhoto:
    """Validate and re-encode an uploaded photo. Raises PhotoError."""
    if not raw:
        raise PhotoError("The file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise PhotoError("The photo is larger than 10 MB.")

    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in ("JPEG", "PNG", "WEBP"):
                raise PhotoError("Use a JPG, PNG or WebP photo.")
            img.load()
            img = ImageOps.exif_transpose(img)
            if min(img.size) < MIN_SIDE_PX:
                raise PhotoError(f"The photo is too small (at least {MIN_SIDE_PX} px on each side).")
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.getchannel("A"))
                img = bg
            else:
                img = img.convert("RGB")
            img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
            out = io.BytesIO()
            # No exif= argument, so no metadata is written.
            img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return ProcessedPhoto(out.getvalue(), img.width, img.height)
    except PhotoError:
        raise
    except Exception as exc:  # not an image, truncated, decompression bomb
        logger.info("Exercise photo refused: %s", type(exc).__name__)
        raise PhotoError("This file is not a readable photo.") from exc


# ---------------------------------------------------------------- storage


def _storage_client():
    try:
        from app.core.storage import storage_client

        return storage_client
    except Exception as exc:
        logger.warning("Photo storage not available: %s", type(exc).__name__)
        return None


def _local_dir() -> str | None:
    return os.environ.get("EXERCISE_PHOTOS_LOCAL_DIR") or None


def _write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


async def _put(key: str, data: bytes) -> str:
    local = _local_dir()
    if local:
        await asyncio.to_thread(_write, os.path.join(local, key), data)
        return LOCAL_PREFIX + key
    client = _storage_client()
    if client is None:
        raise PhotoStorageUnavailable()
    from app.core.storage import StorageUnavailableError

    try:
        await asyncio.to_thread(client.upload_file, key, data, "image/jpeg")
    except StorageUnavailableError as exc:
        raise PhotoStorageUnavailable() from exc
    return key


async def _get(stored_key: str) -> bytes | None:
    if stored_key.startswith(LOCAL_PREFIX):
        local = _local_dir()
        if not local:
            return None
        path = os.path.join(local, stored_key[len(LOCAL_PREFIX):])
        return await asyncio.to_thread(_read, path) if os.path.exists(path) else None
    client = _storage_client()
    if client is None:
        return None
    from app.core.storage import StorageUnavailableError

    try:
        return await asyncio.to_thread(client.download_file, stored_key)
    except StorageUnavailableError:
        logger.warning("Exercise photo download failed")
        return None


async def _remove(stored_key: str) -> None:
    """Best effort: a leftover file is harmless, a failed delete must not
    block removing the row."""
    try:
        if stored_key.startswith(LOCAL_PREFIX):
            local = _local_dir()
            if local:
                path = os.path.join(local, stored_key[len(LOCAL_PREFIX):])
                if os.path.exists(path):
                    os.remove(path)
            return
        client = _storage_client()
        remover = getattr(client, "delete_file", None) if client is not None else None
        if remover is not None:
            await asyncio.to_thread(remover, stored_key)
    except Exception as exc:
        logger.warning("Old exercise photo not removed: %s", type(exc).__name__)


# ---------------------------------------------------------------- rows


def check_angle(angle: str) -> str:
    if angle not in PHOTO_ANGLES:
        raise PhotoError("Angle must be front or side.")
    return angle


async def get_photo(
    db: AsyncSession, clinic_id: uuid.UUID, exercise_id: uuid.UUID, angle: str
) -> ExercisePhoto | None:
    result = await db.execute(
        select(ExercisePhoto).where(
            ExercisePhoto.clinic_id == clinic_id,
            ExercisePhoto.exercise_id == exercise_id,
            ExercisePhoto.angle == angle,
        )
    )
    return result.scalars().first()


async def photos_for(
    db: AsyncSession, clinic_id: uuid.UUID, exercise_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[ExercisePhoto]]:
    """This clinic's photos for the given exercises, front before side."""
    if not exercise_ids:
        return {}
    result = await db.execute(
        select(ExercisePhoto).where(
            ExercisePhoto.clinic_id == clinic_id,
            ExercisePhoto.exercise_id.in_(exercise_ids),
        )
    )
    out: dict[uuid.UUID, list[ExercisePhoto]] = {}
    for row in result.scalars().all():
        out.setdefault(row.exercise_id, []).append(row)
    for rows in out.values():
        rows.sort(key=lambda r: PHOTO_ANGLES.index(r.angle))
    return out


async def save_photo(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    exercise_id: uuid.UUID,
    angle: str,
    raw: bytes,
    user_id: uuid.UUID | None,
) -> ExercisePhoto:
    check_angle(angle)
    processed = await asyncio.to_thread(process_upload, raw)
    key = f"{STORAGE_PREFIX}/{clinic_id}/{exercise_id}/{angle}-{uuid.uuid4().hex}.jpg"
    stored_key = await _put(key, processed.data)

    row = await get_photo(db, clinic_id, exercise_id, angle)
    old_key = row.storage_key if row else None
    if row is None:
        row = ExercisePhoto(clinic_id=clinic_id, exercise_id=exercise_id, angle=angle)
        db.add(row)
    row.storage_key = stored_key
    row.content_type = "image/jpeg"
    row.width = processed.width
    row.height = processed.height
    row.size_bytes = len(processed.data)
    row.uploaded_by = user_id
    await db.commit()
    await db.refresh(row)
    if old_key and old_key != stored_key:
        await _remove(old_key)
    return row


async def delete_photo(
    db: AsyncSession, clinic_id: uuid.UUID, exercise_id: uuid.UUID, angle: str
) -> bool:
    check_angle(angle)
    row = await get_photo(db, clinic_id, exercise_id, angle)
    if row is None:
        return False
    key = row.storage_key
    await db.execute(delete(ExercisePhoto).where(ExercisePhoto.id == row.id))
    await db.commit()
    await _remove(key)
    return True


async def load_photo_bytes(row: ExercisePhoto) -> bytes | None:
    return await _get(row.storage_key)
