"""Document numbers (D-043, decided 26 Nov 2026).

document_counters holds the last number given out per clinic, document type
and period. Clinical documents (RX, POS, PSY) never reset, so their period is
"" (empty). Invoices (INV) and receipts (RCP) count per Indian financial year,
period "2627" for April 2026 to March 2027.

psychosocial_reports has one row per psychosocial PDF export, so every printed
psychosocial report carries its own PSY number and can be traced back.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DocumentCounter(Base):
    __tablename__ = "document_counters"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), primary_key=True
    )
    doc_type: Mapped[str] = mapped_column(String(8), primary_key=True)
    period: Mapped[str] = mapped_column(String(8), primary_key=True, default="")
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PsychosocialReport(Base):
    __tablename__ = "psychosocial_reports"
    __table_args__ = (
        UniqueConstraint("clinic_id", "number", name="uq_psychosocial_reports_clinic_number"),
        Index("ix_psychosocial_reports_clinic_patient", "clinic_id", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(24), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
