from __future__ import annotations

from sqlalchemy import Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.base import Base
from app.common.mixins import TimestampMixin, UUIDMixin
from app.enums.clinic import ClinicPlanTier


def _clinic_plan_tier_values(enum_cls: type[ClinicPlanTier]) -> list[str]:
    """Return database enum values for clinic plan tiers."""

    return [member.value for member in enum_cls]


class Clinic(UUIDMixin, TimestampMixin, Base):
    """Clinic foundation record for CRM tenancy and branding."""

    __tablename__: str = "clinics"
    __table_args__: tuple[Index, ...] = (
        Index("ix_clinics_name", "name"),
        Index("ix_clinics_plan_tier", "plan_tier"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    branding_logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    branding_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plan_tier: Mapped[ClinicPlanTier] = mapped_column(
        Enum(
            ClinicPlanTier,
            name="clinic_plan_tier",
            values_callable=_clinic_plan_tier_values,
        ),
        nullable=False,
    )
    is_partner_clinic: Mapped[bool] = mapped_column(nullable=False, default=False)
