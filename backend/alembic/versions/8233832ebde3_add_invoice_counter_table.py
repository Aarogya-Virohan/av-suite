"""Add invoice counter table

Revision ID: 8233832ebde3
Revises: a0b1c2d3e4f5
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "8233832ebde3"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade():
    # Create the invoice_counters table if it doesn't exist
    op.create_table(
        "invoice_counters",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("clinic_id", name="pk_invoice_counters"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
    )

    # Seed only clinics that already have invoices. Ignore legacy invoice
    # formats when choosing the sequential counter value.
    op.execute("""
        INSERT INTO invoice_counters (clinic_id, last_number)
        SELECT clinic_id,
               COALESCE(MAX(CASE
                   WHEN invoice_number ~ '^INV-[0-9]+$'
                   THEN substring(invoice_number from '^INV-([0-9]+)$')::integer
                   ELSE 0
               END), 0)
        FROM invoices
        GROUP BY clinic_id
    """)


def downgrade():
    # Drop the invoice_counters table
    op.drop_table("invoice_counters")
