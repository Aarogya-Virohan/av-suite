from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Enum, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.enums.shared import Specialty


class TreatmentSession(UUIDMixin, TimestampMixin, Base):
    """Clinic-scoped treatment session record."""

    __tablename__: str = "treatment_sessions"
    __table_args__: tuple[Index | CheckConstraint, ...] = (
        Index("ix_treatment_sessions_clinic_id", "clinic_id"),
        Index("ix_treatment_sessions_patient_id", "patient_id"),
        Index("ix_treatment_sessions_appointment_id", "appointment_id"),
        Index("ix_treatment_sessions_therapist_id", "therapist_id"),
        Index("ix_treatment_sessions_treatment_date", "treatment_date"),
        CheckConstraint("pain_score >= 0 AND pain_score <= 10", name="ck_treatment_sessions_pain_score")
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

    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=True,
    )
    appointment: Mapped[Appointment | None] = relationship()

    therapist_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    therapist: Mapped[User] = relationship()

    treatment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pain_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    treatment: Mapped[str] = mapped_column(Text, nullable=False)
    home_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)


class SoapAssessment(UUIDMixin, TimestampMixin, Base):
    """Clinic-scoped SOAP assessment record storing dynamic assessment data in JSONB."""

    __tablename__: str = "soap_assessments"
    __table_args__: tuple[Index, ...] = (
        Index("ix_soap_assessments_clinic_id", "clinic_id"),
        Index("ix_soap_assessments_patient_id", "patient_id"),
        Index("ix_soap_assessments_appointment_id", "appointment_id"),
        Index("ix_soap_assessments_therapist_id", "therapist_id"),
        Index("ix_soap_assessments_specialty", "specialty"),
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

    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=True,
    )
    appointment: Mapped[Appointment | None] = relationship()

    therapist_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    therapist: Mapped[User | None] = relationship()

    specialty: Mapped[Specialty] = mapped_column(Enum(Specialty, name="specialty_type", values_callable=lambda x: [e.value for e in x], create_type=False), nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_reassessment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    form_data: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict)
