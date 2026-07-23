from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.enums.appointment import AppointmentSource, AppointmentStatus
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User


def _appointment_status_values(enum_cls: type[AppointmentStatus]) -> list[str]:
    """Return database enum values for appointment status."""

    return [member.value for member in enum_cls]


def _appointment_source_values(enum_cls: type[AppointmentSource]) -> list[str]:
    """Return database enum values for appointment source."""

    return [member.value for member in enum_cls]


class Appointment(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Clinic-scoped appointment entity representing scheduled clinical visits."""

    __tablename__: str = "appointments"
    __table_args__: tuple[Index, ...] = (
        Index("ix_appointments_clinic_id", "clinic_id"),
        Index("ix_appointments_patient_id", "patient_id"),
        Index("ix_appointments_therapist_id", "therapist_id"),
        Index("ix_appointments_scheduled_at", "scheduled_at"),
        Index("ix_appointments_status", "status"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    patient: Mapped[Patient] = relationship()

    therapist_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    therapist: Mapped[User] = relationship()

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
            values_callable=_appointment_status_values,
        ),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
    )

    source: Mapped[AppointmentSource] = mapped_column(
        Enum(
            AppointmentSource,
            name="appointment_source",
            values_callable=_appointment_source_values,
        ),
        nullable=False,
        default=AppointmentSource.MANUAL,
    )
