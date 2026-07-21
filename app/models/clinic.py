from __future__ import annotations

from sqlalchemy import Enum, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base
from app.common.mixins import TimestampMixin, UUIDMixin
from app.enums.clinic import ClinicStatus


class Clinic(UUIDMixin, TimestampMixin, Base):
    """Clinic profile and contact details."""

    __tablename__ = "clinics"
    __table_args__ = (
        Index("ix_clinics_name", "name"),
        Index("ix_clinics_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
        server_default=text("'UTC'"),
    )
    status: Mapped[ClinicStatus] = mapped_column(
        Enum(ClinicStatus, name="clinic_status"),
        nullable=False,
        default=ClinicStatus.ACTIVE,
    )
