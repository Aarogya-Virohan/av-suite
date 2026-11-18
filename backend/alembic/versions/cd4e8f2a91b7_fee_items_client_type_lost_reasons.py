"""Add clinic fee items, client type, and additional lead lost reasons.

Revision ID: cd4e8f2a91b7
Revises: ab91ce42d730
"""
from alembic import op
import sqlalchemy as sa

revision = "cd4e8f2a91b7"
down_revision = "ab91ce42d730"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clinics", sa.Column("client_type", sa.String(length=20), nullable=False, server_default="clinic"))
    op.create_check_constraint("ck_clinics_client_type", "clinics", "client_type IN ('clinic', 'hospital', 'home_care')")
    op.create_table(
        "clinic_fee_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("default_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_editable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("category IN ('consultation', 'posture', 'exercise_rx', 'custom')", name="ck_clinic_fee_items_category"),
        sa.CheckConstraint("default_price >= 0", name="ck_clinic_fee_items_default_price_nonnegative"),
    )
    op.create_index("ix_clinic_fee_items_clinic_active_sort", "clinic_fee_items", ["clinic_id", "active", "sort_order"])
    for reason in ("too_far", "timing_mismatch", "needs_home_visit", "cannot_afford", "went_to_competitor"):
        op.execute(sa.text(f"ALTER TYPE lead_lost_reason ADD VALUE IF NOT EXISTS '{reason}'"))


def downgrade() -> None:
    op.drop_index("ix_clinic_fee_items_clinic_active_sort", table_name="clinic_fee_items")
    op.drop_table("clinic_fee_items")
    op.drop_constraint("ck_clinics_client_type", "clinics", type_="check")
    op.drop_column("clinics", "client_type")
    # PostgreSQL enum values cannot be removed with ordinary ALTER TYPE downgrade operations.
    # Keep the added values in the enum; downgrade only reverses the table and column changes.
