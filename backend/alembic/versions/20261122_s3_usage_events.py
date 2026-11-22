"""Create append-only platform usage events.

Revision ID: s3usage20261122
Revises: s2plat20261120
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s3usage20261122"
down_revision = "s2plat20261120"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usage_events",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("product_key", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_usage_events_clinic_created_at", "usage_events", ["clinic_id", "created_at"])
    op.create_index("ix_usage_events_product_created_at", "usage_events", ["product_key", "created_at"])


def downgrade():
    op.drop_index("ix_usage_events_product_created_at", table_name="usage_events")
    op.drop_index("ix_usage_events_clinic_created_at", table_name="usage_events")
    op.drop_table("usage_events")
