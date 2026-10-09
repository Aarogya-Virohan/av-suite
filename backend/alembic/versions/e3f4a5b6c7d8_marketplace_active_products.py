"""add marketplace active state and bundle validity

Revision ID: e3f4a5b6c7d8
Revises: d0c1b2a3f4e5
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "e3f4a5b6c7d8"
down_revision = "d0c1b2a3f4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "platform_bundles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "platform_bundle_products",
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_bundle_products", "valid_until")
    op.drop_column("platform_bundles", "is_active")
    op.drop_column("products", "is_active")