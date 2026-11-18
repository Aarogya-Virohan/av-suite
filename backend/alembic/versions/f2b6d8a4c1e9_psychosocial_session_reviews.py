"""Tool 03 session reviews (Priority review)

Revision ID: f2b6d8a4c1e9
Revises: e7a1c4b9d2f6
Create Date: 2026-11-07

One row each time a provider opens a result. A risk result stays in the
Priority review list until a provider has opened it after it was completed
(founders' decision F4 = 4A). Append-only; completed sessions stay immutable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "f2b6d8a4c1e9"
down_revision: Union[str, Sequence[str], None] = "e7a1c4b9d2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "psychosocial_session_reviews",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", PGUUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", PGUUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "session_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("psychosocial_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewed_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_psy_reviews_clinic_session", "psychosocial_session_reviews", ["clinic_id", "session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_psy_reviews_clinic_session", table_name="psychosocial_session_reviews")
    op.drop_table("psychosocial_session_reviews")
