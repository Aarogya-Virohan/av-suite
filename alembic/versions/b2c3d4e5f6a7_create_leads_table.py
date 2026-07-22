"""create leads table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-22 21:50:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

lead_stage = postgresql.ENUM(
    "new", "contacted", "qualified", "converted", "lost",
    name="lead_stage",
    create_type=False,
)


def upgrade() -> None:
    postgresql.ENUM(
        "new", "contacted", "qualified", "converted", "lost",
        name="lead_stage",
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("stage", lead_stage, nullable=False, server_default="new"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("converted_patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_patient_id"], ["patients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_clinic_id", "leads", ["clinic_id"], unique=False)
    op.create_index("ix_leads_stage", "leads", ["stage"], unique=False)
    op.create_index("ix_leads_assigned_to", "leads", ["assigned_to"], unique=False)
    op.create_index("ix_leads_converted_patient_id", "leads", ["converted_patient_id"], unique=False)
    op.create_index("ix_leads_phone", "leads", ["phone"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_leads_phone", table_name="leads")
    op.drop_index("ix_leads_converted_patient_id", table_name="leads")
    op.drop_index("ix_leads_assigned_to", table_name="leads")
    op.drop_index("ix_leads_stage", table_name="leads")
    op.drop_index("ix_leads_clinic_id", table_name="leads")
    op.drop_table("leads")
    postgresql.ENUM(name="lead_stage").drop(op.get_bind(), checkfirst=True)
