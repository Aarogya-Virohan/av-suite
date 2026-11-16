"""
A clinic's own photo of an exercise, from one angle (front or side).

Founders' feedback item 2 (23 Oct 2026), answer 2A (27 Oct): the clinic adds
its own photos of an exercise from two angles and only that clinic sees them.
Photos of patients are out of scope (they would need recorded consent).
The file lives in the private storage bucket; this row only points to it.
"""

import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

PHOTO_ANGLES = ("front", "side")


class ExercisePhoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "exercise_photos"
    __table_args__ = (
        UniqueConstraint("clinic_id", "exercise_id", "angle", name="uq_exercise_photos_clinic_exercise_angle"),
        CheckConstraint("angle IN ('front', 'side')", name="ck_exercise_photos_angle"),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    angle: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/jpeg")
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
