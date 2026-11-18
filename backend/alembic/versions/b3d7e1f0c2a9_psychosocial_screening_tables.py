"""Tool 03 psycho-social screening tables

Revision ID: b3d7e1f0c2a9
Revises: a8c4e2f1d903
Create Date: 2026-10-20

Creates assignments (patient links), sessions (one per instrument),
consent log and referral action log, plus the trigger that makes completed
sessions immutable. No product entitlement is granted here: clinics get
psycho-social-screening through the marketplace install flow (S-D-012).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

revision: str = "b3d7e1f0c2a9"
down_revision: Union[str, Sequence[str], None] = "a8c4e2f1d903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Kept identical to app/models/psychosocial.py on purpose: a migration must
# not import app code that can change after it ships.
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


def _in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "psychosocial_assignments",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(_in("status", ASSIGNMENT_STATUSES), name="ck_psy_assignment_status"),
    )
    op.create_index("ix_psy_assignments_clinic_patient", "psychosocial_assignments", ["clinic_id", "patient_id"])

    op.create_table(
        "psychosocial_sessions",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assignment_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("psychosocial_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("instrument_id", sa.String(32), nullable=False),
        sa.Column("instrument_version", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("responses", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("referral_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("risk_item_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
        sa.CheckConstraint(_in("status", SESSION_STATUSES), name="ck_psy_session_status"),
    )
    op.create_index("ix_psychosocial_sessions_assignment_id", "psychosocial_sessions", ["assignment_id"])
    op.create_index(
        "ix_psy_sessions_clinic_patient_instrument",
        "psychosocial_sessions",
        ["clinic_id", "patient_id", "instrument_id"],
    )
    op.create_index("ix_psy_sessions_clinic_status", "psychosocial_sessions", ["clinic_id", "status"])

    op.create_table(
        "psychosocial_consents",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "assignment_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("psychosocial_assignments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("text_version", sa.String(32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_in("status", CONSENT_STATUSES), name="ck_psy_consent_status"),
    )
    op.create_index("ix_psy_consents_clinic_patient", "psychosocial_consents", ["clinic_id", "patient_id"])

    op.create_table(
        "psychosocial_referral_actions",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "session_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("psychosocial_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("recorded_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_in("action", REFERRAL_ACTIONS), name="ck_psy_referral_action"),
    )
    op.create_index(
        "ix_psychosocial_referral_actions_session_id", "psychosocial_referral_actions", ["session_id"]
    )
    op.create_index("ix_psy_referrals_clinic_patient", "psychosocial_referral_actions", ["clinic_id", "patient_id"])

    op.execute(IMMUTABLE_FUNCTION_SQL)
    op.execute(IMMUTABLE_TRIGGER_SQL)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_psychosocial_sessions_immutable ON psychosocial_sessions")
    op.execute("DROP FUNCTION IF EXISTS psychosocial_sessions_block_completed_update()")
    op.drop_table("psychosocial_referral_actions")
    op.drop_table("psychosocial_consents")
    op.drop_table("psychosocial_sessions")
    op.drop_table("psychosocial_assignments")
