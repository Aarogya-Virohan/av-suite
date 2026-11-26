import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Index, String, ForeignKey, Integer, Text, UniqueConstraint
from typing import Optional
from app.models.base import Base, TimestampMixin

class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"
    # Hot lists (report E4): clinic list newest first, per patient, per physio.
    __table_args__ = (
        Index("ix_prescriptions_clinic_created", "clinic_id", "created_at"),
        Index("ix_prescriptions_patient_id", "patient_id"),
        Index("ix_prescriptions_physio_id", "physio_id"),
        UniqueConstraint("clinic_id", "number", name="uq_prescriptions_clinic_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    physio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    physio_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    pdf_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # D-043: <clinic code>-RX-<6 digits>, given by the server on create.
    number: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)

    clinic = relationship("Clinic", back_populates="prescriptions")
    patient = relationship("Patient", back_populates="prescriptions")
    physio = relationship("User", back_populates="prescriptions_given")
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base, TimestampMixin):
    __tablename__ = "prescription_items"
    __table_args__ = (Index("ix_prescription_items_prescription_id", "prescription_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id", ondelete="CASCADE"))
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    sets: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    hold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False, default="Daily")
    hold_angle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # "left" / "right" for exercises that need a side (EL-D-014).
    side: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    prescription = relationship("Prescription", back_populates="items")
    exercise = relationship("Exercise", back_populates="prescription_items")

