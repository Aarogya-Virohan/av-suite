"""Tool 03 repeat schedules for screeners

Revision ID: c4e8a2b6d1f3
Revises: b3d7e1f0c2a9
Create Date: 2026-10-22

One row per patient and screener that should repeat every N days (SRS
4.1.1). The app uses it only to list screeners that are due again; nothing
is sent automatically (S-D-026). Stopping a schedule sets stopped_at, and a
partial unique index allows one active schedule per patient and screener.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "c4e8a2b6d1f3"
down_revision: Union[str, Sequence[str], None] = "b3d7e1f0c2a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Kept identical to app/models/psychosocial.py on purpose: a migration must
# not import app code that can change after it ships.
SCHEDULE_MIN_DAYS = 7
SCHEDULE_MAX_DAYS = 364


def upgrade() -> None:
    op.create_table(
        "psychosocial_schedules",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", sa.String(32), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("created_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            f"interval_days BETWEEN {SCHEDULE_MIN_DAYS} AND {SCHEDULE_MAX_DAYS}",
            name="ck_psy_schedule_interval",
        ),
    )
    op.create_index("ix_psy_schedules_clinic_patient", "psychosocial_schedules", ["clinic_id", "patient_id"])
    op.create_index(
        "uq_psy_schedules_active",
        "psychosocial_schedules",
        ["clinic_id", "patient_id", "instrument_id"],
        unique=True,
        postgresql_where=sa.text("stopped_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_psy_schedules_active", table_name="psychosocial_schedules")
    op.drop_index("ix_psy_schedules_clinic_patient", table_name="psychosocial_schedules")
    op.drop_table("psychosocial_schedules")
