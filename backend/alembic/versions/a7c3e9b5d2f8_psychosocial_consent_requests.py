"""Tool 03 consent requests (re-consent after a withdrawal)

Revision ID: a7c3e9b5d2f8
Revises: f2b6d8a4c1e9
Create Date: 2026-11-08

A consent-only link the provider sends after a patient withdrew. The patient
chooses again on their own phone (founders' decision Q7 = 7B).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "a7c3e9b5d2f8"
down_revision: Union[str, Sequence[str], None] = "f2b6d8a4c1e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "psychosocial_consent_requests",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'granted', 'declined', 'cancelled')", name="ck_psy_consent_request_status"
        ),
    )
    op.create_index(
        "ix_psy_consent_requests_clinic_patient", "psychosocial_consent_requests", ["clinic_id", "patient_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_psy_consent_requests_clinic_patient", table_name="psychosocial_consent_requests")
    op.drop_table("psychosocial_consent_requests")
