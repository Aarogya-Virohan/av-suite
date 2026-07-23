import uuid
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Date, ForeignKey, Text, Enum, DateTime
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import date, datetime
from typing import Optional
from app.models.base import Base, TimestampMixin


class PatientStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    discharged = "discharged"


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    age: Mapped[Optional[int]] = mapped_column(nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referral_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[PatientStatus] = mapped_column(Enum(PatientStatus), nullable=False, default=PatientStatus.active)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    clinic = relationship("Clinic", back_populates="patients")
    user = relationship("User", back_populates="patient_profile")
    prescriptions = relationship("Prescription", back_populates="patient")
    posture_sessions = relationship("PostureSession", back_populates="patient")

    @hybrid_property
    def full_name(self) -> str:
        """Read: combines first_name + last_name. Write: splits back into both.

        Works both on Python instances (patient.full_name) and in SQL
        queries (Patient.full_name.ilike(...)), which the CRM repository
        layer relies on for search.
        """
        return f"{self.first_name} {self.last_name}".strip()

    @full_name.inplace.setter
    def _full_name_setter(self, value: str) -> None:
        parts = (value or "").strip().split(" ", 1)
        self.first_name = parts[0] if parts else ""
        self.last_name = parts[1] if len(parts) > 1 else ""

    @full_name.inplace.expression
    @classmethod
    def _full_name_expression(cls):
        from sqlalchemy import func
        return func.concat(cls.first_name, ' ', cls.last_name)
