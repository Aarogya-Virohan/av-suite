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

    # Populate the counter table with the max invoice number per clinic
    bind = op.get_bind()
    # We assume the invoice_number format is INV- followed by digits.
    # We extract the numeric part and take the max per clinic.
    # If there are no invoices for a clinic, we set last_number to 0.
    # We'll do this in two steps: first, insert a row for each clinic with last_number=0.
    # Then, update it with the max invoice number.
    # However, note that the invoice_number might not be in the format INV-<digits> if there are legacy values.
    # We'll follow the same logic as in the original migration: we extract the number from the pattern ^INV-([0-9]+)$.
    # If the invoice_number does not match, we ignore it (treat as 0 for the max?).
    # But note: the unique constraint on (clinic_id, invoice_number) ensures that we can have at most one invoice per clinic with a given number.
    # We want to find the maximum numeric suffix for each clinic.

    # We'll use a SQL query to update the counter table.
    # We'll update the counter table by joining with a subquery that computes the max invoice number per clinic.
    # We'll only consider invoice_numbers that match the pattern.
    # We'll use the regexp to extract the digits.
    # Note: This is specific to PostgreSQL.
    op.execute("""
        UPDATE invoice_counters ic
        SET last_number = COALESCE((
            SELECT MAX(
                CASE
                    WHEN invoice_number ~ '^INV-([0-9]+)$' THEN
                        substring(invoice_number from '^INV-([0-9]+)$')::integer
                    ELSE
                        0
                END
            )
            FROM invoices i
            WHERE i.clinic_id = ic.clinic_id
        ), 0)
    """)


def downgrade():
    # Drop the invoice_counters table
    op.drop_table("invoice_counters")
