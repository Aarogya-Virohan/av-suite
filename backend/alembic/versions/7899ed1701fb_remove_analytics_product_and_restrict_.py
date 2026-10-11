"""remove analytics product and restrict crm to clinics

Revision ID: 7899ed1701fb
Revises: e3f4a5b6c7d8
Create Date: 2026-10-11 13:23:19.235796

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7899ed1701fb"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Analytics is part of CRM, not a standalone product.
    bind.execute(
        sa.text("DELETE FROM products WHERE id = :product_id"),
        {"product_id": "analytics"},
    )

    # CRM is sellable only to clinic workspaces.
    bind.execute(
        sa.text(
            "UPDATE products "
            "SET allowed_clinic_types = :allowed_types "
            "WHERE id = :product_id"
        ).bindparams(
            sa.bindparam("allowed_types", type_=sa.ARRAY(sa.String())),
            sa.bindparam("product_id", type_=sa.String()),
        ),
        {
            "allowed_types": ["clinic"],
            "product_id": "crm",
        },
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Restore CRM eligibility for all workspace types.
    bind.execute(
        sa.text(
            "UPDATE products "
            "SET allowed_clinic_types = :allowed_types "
            "WHERE id = :product_id"
        ).bindparams(
            sa.bindparam("allowed_types", type_=sa.ARRAY(sa.String())),
            sa.bindparam("product_id", type_=sa.String()),
        ),
        {
            "allowed_types": ["clinic", "solo", "personal"],
            "product_id": "crm",
        },
    )

    # Restore Analytics as a standalone product.
    bind.execute(
        sa.text("""
            INSERT INTO products (
                id,
                slug,
                name,
                description,
                category
            )
            VALUES (
                :id,
                :slug,
                :name,
                :description,
                :category
            )
            """),
        {
            "id": "analytics",
            "slug": "analytics",
            "name": "Analytics",
            "description": "Clinical and operational insights for your workspace.",
            "category": "Analytics",
        },
    )
