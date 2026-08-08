from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.enums.booking import AppointmentRequestStatus
from app.enums.shared import Gender
from app.models.clinic import Clinic


def _appointment_request_status_values(enum_cls: type[AppointmentRequestStatus]) -> list[str]:
    """Return database enum values for appointment request status."""

    return [member.value for member in enum_cls]


class AppointmentRequest(UUIDMixin, TimestampMixin, Base):
    """Public booking appointment request entity."""

    __tablename__: str = "appointment_requests"
    __table_args__: tuple[Index, ...] = (
        Index("ix_appointment_requests_clinic_id", "clinic_id"),
        Index("ix_appointment_requests_status", "status"),
        Index("ix_appointment_requests_phone", "phone"),
        Index("ix_appointment_requests_preferred_date", "preferred_date"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    phone: Mapped[str] = mapped_column(String(length=50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, name="gender_type", create_type=False), nullable=True
    )

    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_slot: Mapped[str | None] = mapped_column(String(length=50), nullable=True)

    status: Mapped[AppointmentRequestStatus] = mapped_column(
        Enum(
            AppointmentRequestStatus,
            name="appointment_request_status",
            values_callable=_appointment_request_status_values,
            create_type=False,
        ),
        default=AppointmentRequestStatus.PENDING,
        nullable=False,
    )
