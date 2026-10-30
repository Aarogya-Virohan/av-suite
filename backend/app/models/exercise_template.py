"""
Exercise templates: a saved program of exercises with their default dose.

Founders' questions EL-7 and EL-8, decided with Onkar on 30 Oct 2026 (EL-D-009):
- A template is a generic program (name, description, exercises with sets,
  reps, hold, frequency and a note). It is not tied to a patient.
- Using a template only fills a new prescription. The physio can still change
  it, and the PDF is always made from the saved prescription, so a template
  carries no branding of its own.
- clinic_id NULL is kept for AV templates (shared with every clinic), the same
  rule as global exercises. This release only lets a clinic make its own; AV
  templates come later as data, with no schema change.
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ExerciseTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "exercise_templates"

    clinic_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    items = relationship(
        "ExerciseTemplateItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ExerciseTemplateItem.position",
        lazy="selectin",
    )


class ExerciseTemplateItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "exercise_template_items"
    __table_args__ = (
        UniqueConstraint("template_id", "exercise_id", name="uq_exercise_template_items_template_exercise"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("exercise_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sets: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    hold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False, default="Daily")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    template = relationship("ExerciseTemplate", back_populates="items")
    exercise = relationship("Exercise", lazy="selectin")
