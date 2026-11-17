"""Add audit hardening fields for billing actions.

Revision ID: ab91ce42d730
Revises: c7d9e1a4b602
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ab91ce42d730"
down_revision = "c7d9e1a4b602"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("cancel_reason", sa.Text(), nullable=True))
    op.add_column("invoices", sa.Column("discount_reason", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("void_reason", sa.Text(), nullable=True))
    op.add_column(
        "payments",
        sa.Column(
            "voided_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_constraint("payments_voided_by_fkey", "payments", type_="foreignkey")
    op.drop_column("payments", "voided_by")
    op.drop_column("payments", "void_reason")
    op.drop_column("invoices", "discount_reason")
    op.drop_column("invoices", "cancel_reason")
