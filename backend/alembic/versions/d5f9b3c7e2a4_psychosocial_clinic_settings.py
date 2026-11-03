"""Tool 03 clinic settings per screener

Revision ID: d5f9b3c7e2a4
Revises: c4e8a2b6d1f3
Create Date: 2026-10-22

One row per clinic and screener (SRS 4.3.2). Today it holds the clinic-wide
default repeat interval in weeks, which prefills the Repeat field when a
screener is sent. NULL means "just once". Referral thresholds are not stored:
they stay at the published norms until the founders decide (S-D-027).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "d5f9b3c7e2a4"
down_revision: Union[str, Sequence[str], None] = "c4e8a2b6d1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Kept identical to app/models/psychosocial.py on purpose: a migration must
# not import app code that can change after it ships.
DEFAULT_REPEAT_MIN_WEEKS = 1
DEFAULT_REPEAT_MAX_WEEKS = 52


def upgrade() -> None:
    op.create_table(
        "psychosocial_clinic_settings",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", sa.String(32), nullable=False),
        sa.Column("default_repeat_weeks", sa.Integer(), nullable=True),
        sa.Column("updated_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "default_repeat_weeks IS NULL OR default_repeat_weeks BETWEEN "
            f"{DEFAULT_REPEAT_MIN_WEEKS} AND {DEFAULT_REPEAT_MAX_WEEKS}",
            name="ck_psy_setting_repeat_weeks",
        ),
    )
    op.create_index(
        "uq_psy_settings_clinic_instrument",
        "psychosocial_clinic_settings",
        ["clinic_id", "instrument_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_psy_settings_clinic_instrument", table_name="psychosocial_clinic_settings")
    op.drop_table("psychosocial_clinic_settings")
