import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, Text
from typing import Optional
from app.models.base import Base, TimestampMixin

class Exercise(Base, TimestampMixin):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_part: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    video_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    clinic = relationship("Clinic", back_populates="exercises")
    prescription_items = relationship("PrescriptionItem", back_populates="exercise")
