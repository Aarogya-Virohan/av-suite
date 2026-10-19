"""Tool 03 Psycho-Social Screening tables.

One assignment is one patient link. It holds a hashed access token and one
session per instrument (PHQ-9, GAD-7, DASS-21). Sessions keep the raw
responses, the instrument id and version, and the computed result, so a
result can always be re-derived and explained.

Completed sessions are immutable. Besides the service-layer checks, a
Postgres trigger rejects any UPDATE of a session row whose status is
already 'completed' (see the DDL at the bottom of this file and migration
b3d7e1f0c2a9).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy import DDL
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

# JSONB on Postgres, plain JSON elsewhere (SQLite test runs).
JSONType = JSON().with_variant(JSONB(), "postgresql")

ASSIGNMENT_STATUSES = ("active", "completed", "cancelled")
SESSION_STATUSES = ("pending", "in_progress", "completed", "cancelled")
CONSENT_STATUSES = ("granted", "withdrawn")
REFERRAL_ACTIONS = (
    "referred_gp",
    "referred_psychologist",
    "referred_psychiatrist",
    "already_under_care",
    "patient_declined",
    "monitor_and_rescreen",
    "other",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


class PsychosocialAssignment(Base, TimestampMixin):
    __tablename__ = "psychosocial_assignments"
    __table_args__ = (
        CheckConstraint(_in("status", ASSIGNMENT_STATUSES), name="ck_psy_assignment_status"),
        Index("ix_psy_assignments_clinic_patient", "clinic_id", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # SHA-256 hex of the URL token. The token itself is never stored.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    sessions: Mapped[list["PsychosocialSession"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="PsychosocialSession.position",
        lazy="selectin",
    )


class PsychosocialSession(Base, TimestampMixin):
    __tablename__ = "psychosocial_sessions"
    __table_args__ = (
        CheckConstraint(_in("status", SESSION_STATUSES), name="ck_psy_session_status"),
        Index("ix_psy_sessions_clinic_patient_instrument", "clinic_id", "patient_id", "instrument_id"),
        Index("ix_psy_sessions_clinic_status", "clinic_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("psychosocial_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False)
    instrument_version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    # {item_id: value}. Items are answered strictly in order.
    responses: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Serialised ScoreResult, written once on submit.
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    referral_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_item_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    assignment: Mapped[PsychosocialAssignment] = relationship(back_populates="sessions")


class PsychosocialConsent(Base):
    """Append-only consent log. The latest row per patient is the current state."""

    __tablename__ = "psychosocial_consents"
    __table_args__ = (
        CheckConstraint(_in("status", CONSENT_STATUSES), name="ck_psy_consent_status"),
        Index("ix_psy_consents_clinic_patient", "clinic_id", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("psychosocial_assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    text_version: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PsychosocialReferralAction(Base):
    """Append-only log of what the physio did about a referral flag."""

    __tablename__ = "psychosocial_referral_actions"
    __table_args__ = (
        CheckConstraint(_in("action", REFERRAL_ACTIONS), name="ck_psy_referral_action"),
        Index("ix_psy_referrals_clinic_patient", "clinic_id", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("psychosocial_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --- Immutability guard (Postgres only) ------------------------------------
# Same SQL as migration b3d7e1f0c2a9, so tests that build the schema with
# create_all() get exactly the trigger production has. DDL() treats % as a
# format character, hence the escaping below.
IMMUTABLE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION psychosocial_sessions_block_completed_update()
RETURNS trigger AS $$
BEGIN
    IF OLD.status = 'completed' THEN
        RAISE EXCEPTION 'psychosocial session % is completed and immutable', OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

IMMUTABLE_TRIGGER_SQL = """
CREATE TRIGGER trg_psychosocial_sessions_immutable
BEFORE UPDATE ON psychosocial_sessions
FOR EACH ROW EXECUTE FUNCTION psychosocial_sessions_block_completed_update();
"""

event.listen(
    PsychosocialSession.__table__,
    "after_create",
    DDL(IMMUTABLE_FUNCTION_SQL.replace("%", "%%")).execute_if(dialect="postgresql"),
)
event.listen(
    PsychosocialSession.__table__,
    "after_create",
    DDL(IMMUTABLE_TRIGGER_SQL).execute_if(dialect="postgresql"),
)
