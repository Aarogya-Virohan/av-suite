"""Tool 03 provider-shared reports

Revision ID: b8d4f0c6e3a1
Revises: a7c3e9b5d2f8
Create Date: 2026-11-09

After the consultation the provider can share a report with the patient:
their advice, a patient-friendly score summary and chosen resources
(founders' decision, F2 follow-up). Only the token hash is stored.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "b8d4f0c6e3a1"
down_revision: Union[str, Sequence[str], None] = "a7c3e9b5d2f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "psychosocial_shared_reports",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "assignment_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("psychosocial_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("shared_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("advice", sa.Text(), nullable=True),
        sa.Column("resource_keys", JSONB(), nullable=False),
        sa.Column("custom_links", JSONB(), nullable=False),
        sa.Column("birth_year_check", sa.Boolean(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("open_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_psy_shared_reports_clinic_patient", "psychosocial_shared_reports", ["clinic_id", "patient_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_psy_shared_reports_clinic_patient", table_name="psychosocial_shared_reports")
    op.drop_table("psychosocial_shared_reports")
