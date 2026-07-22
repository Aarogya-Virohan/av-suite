"""create appointment requests table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-22 21:55:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

appointment_request_status = postgresql.ENUM(
    "pending", "approved", "rejected",
    name="appointment_request_status",
    create_type=False,
)


def upgrade() -> None:
    postgresql.ENUM(
        "pending", "approved", "rejected",
        name="appointment_request_status",
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "appointment_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("preferred_date", sa.Date(), nullable=True),
        sa.Column("preferred_slot", sa.String(length=50), nullable=True),
        sa.Column("status", appointment_request_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointment_requests_clinic_id", "appointment_requests", ["clinic_id"], unique=False)
    op.create_index("ix_appointment_requests_status", "appointment_requests", ["status"], unique=False)
    op.create_index("ix_appointment_requests_phone", "appointment_requests", ["phone"], unique=False)
    op.create_index("ix_appointment_requests_preferred_date", "appointment_requests", ["preferred_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_appointment_requests_preferred_date", table_name="appointment_requests")
    op.drop_index("ix_appointment_requests_phone", table_name="appointment_requests")
    op.drop_index("ix_appointment_requests_status", table_name="appointment_requests")
    op.drop_index("ix_appointment_requests_clinic_id", table_name="appointment_requests")
    op.drop_table("appointment_requests")
    postgresql.ENUM(name="appointment_request_status").drop(op.get_bind(), checkfirst=True)
