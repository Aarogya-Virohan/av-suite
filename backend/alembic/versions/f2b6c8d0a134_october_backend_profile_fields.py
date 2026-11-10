"""Add lead loss details, invoice percentages, and clinic profile fields.

Revision ID: f2b6c8d0a134
Revises: a8c4e2f1d903
"""
from alembic import op
import sqlalchemy as sa

revision = "f2b6c8d0a134"
down_revision = "a8c4e2f1d903"
branch_labels = None
depends_on = None

lead_lost_reason = sa.Enum(
    "denied", "better_price", "asked_for_discount", "offer", "call_not_picked", "other",
    name="lead_lost_reason",
)


def upgrade() -> None:
    bind = op.get_bind()
    lead_lost_reason.create(bind, checkfirst=True)
    op.add_column("leads", sa.Column("lost_reason", lead_lost_reason, nullable=True))
    op.add_column("leads", sa.Column("lost_remark", sa.String(length=500), nullable=True))
    op.add_column("invoices", sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("invoices", sa.Column("tax_percent", sa.Numeric(5, 2), nullable=True))
    for name, kind in (
        ("address_line", sa.Text()),
        ("city", sa.String(120)),
        ("state", sa.String(120)),
        ("pincode", sa.String(6)),
        ("phone", sa.String(50)),
        ("email", sa.String(255)),
        ("registration_number", sa.String(120)),
        ("gstin", sa.String(15)),
        ("authorised_person", sa.String(255)),
    ):
        op.add_column("clinics", sa.Column(name, kind, nullable=True))


def downgrade() -> None:
    for name in ("authorised_person", "gstin", "registration_number", "email", "phone", "pincode", "state", "city", "address_line"):
        op.drop_column("clinics", name)
    op.drop_column("invoices", "tax_percent")
    op.drop_column("invoices", "discount_percent")
    op.drop_column("leads", "lost_remark")
    op.drop_column("leads", "lost_reason")
    lead_lost_reason.drop(op.get_bind(), checkfirst=True)
