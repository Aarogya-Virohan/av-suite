"""make invoice numbers unique within each clinic

Revision ID: b72a91c4d605
Revises: 7899ed1701fb
Create Date: 2026-10-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b72a91c4d605"
down_revision: Union[str, Sequence[str], None] = "a91c2d7e4f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    invoices = sa.table(
        "invoices",
        sa.column("id", sa.Uuid()),
        sa.column("clinic_id", sa.Uuid()),
        sa.column("invoice_number", sa.String(length=64)),
    )
    rows = bind.execute(
        sa.select(invoices.c.id, invoices.c.clinic_id, invoices.c.invoice_number)
        .order_by(invoices.c.clinic_id, invoices.c.invoice_number, invoices.c.id)
    ).all()

    reserved = {(row.clinic_id, row.invoice_number) for row in rows}
    used: set[tuple[object, str]] = set()
    for row in rows:
        key = (row.clinic_id, row.invoice_number)
        if key not in used:
            used.add(key)
            continue

        suffix = 1
        while True:
            candidate = f"INV-MIGRATED-{row.id.hex.upper()}"
            if suffix > 1:
                ending = f"-{suffix}"
                candidate = f"{candidate[:64 - len(ending)]}{ending}"
            candidate = candidate[:64]
            candidate_key = (row.clinic_id, candidate)
            if candidate_key not in used and candidate_key not in reserved:
                break
            suffix += 1

        bind.execute(
            invoices.update()
            .where(invoices.c.id == row.id)
            .values(invoice_number=candidate)
        )
        used.add(candidate_key)

    op.create_unique_constraint(
        "uq_invoices_clinic_invoice_number",
        "invoices",
        ["clinic_id", "invoice_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_invoices_clinic_invoice_number", "invoices", type_="unique"
    )
