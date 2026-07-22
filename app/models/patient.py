from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base
from app.common.mixins import TimestampMixin, UUIDMixin
from app.enums.patient import PatientStatus
from app.models.clinic import Clinic


def _patient_status_values(enum_cls: type[PatientStatus]) -> list[str]:
    """Return database enum values for patient status."""

    return [member.value for member in enum_cls]


class Patient(UUIDMixin, TimestampMixin, Base):
    """Clinic-scoped patient entity representing demographic and clinical intake data."""

    __tablename__: str = "patients"
    __table_args__: tuple[Index, ...] = (
        Index("ix_patients_clinic_id", "clinic_id"),
        Index("ix_patients_full_name", "full_name"),
        Index("ix_patients_phone", "phone"),
        Index("ix_patients_status", "status"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    referral_source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[PatientStatus] = mapped_column(
        Enum(
            PatientStatus,
            name="patient_status",
            values_callable=_patient_status_values,
        ),
        nullable=False,
        default=PatientStatus.ACTIVE,
    )
