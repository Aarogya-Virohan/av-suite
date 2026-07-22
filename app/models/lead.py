from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base
from app.common.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.enums.lead import LeadStage
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User


def _lead_stage_values(enum_cls: type[LeadStage]) -> list[str]:
    """Return database enum values for lead stage."""

    return [member.value for member in enum_cls]


class Lead(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """CRM Lead entity representing prospective patients."""

    __tablename__: str = "leads"
    __table_args__: tuple[Index, ...] = (
        Index("ix_leads_clinic_id", "clinic_id"),
        Index("ix_leads_stage", "stage"),
        Index("ix_leads_assigned_to", "assigned_to"),
        Index("ix_leads_converted_patient_id", "converted_patient_id"),
        Index("ix_leads_phone", "phone"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    phone: Mapped[str] = mapped_column(String(length=50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(length=100), nullable=True)

    stage: Mapped[LeadStage] = mapped_column(
        Enum(
            LeadStage,
            name="lead_stage",
            values_callable=_lead_stage_values,
            create_type=False,
        ),
        default=LeadStage.NEW,
        nullable=False,
    )

    assigned_to: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    assignee: Mapped[User | None] = relationship()

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    converted_patient_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=True,
    )
    converted_patient: Mapped[Patient | None] = relationship()
