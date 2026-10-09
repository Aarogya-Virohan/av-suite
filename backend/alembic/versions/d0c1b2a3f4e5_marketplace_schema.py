"""marketplace schema changes

Revision ID: d0c1b2a3f4e5
Revises: 6b0f1d2c3a4e
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d0c1b2a3f4e5"
down_revision = "6b0f1d2c3a4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Add allowed_clinic_types to products table
    op.add_column(
        "products",
        sa.Column(
            "allowed_clinic_types",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("ARRAY['clinic','solo','personal']"),
        ),
    )
    # Add valid_from and valid_until to workspace_products table
    op.add_column(
        "workspace_products",
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "workspace_products",
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )

    # Update allowed_clinic_types for each product based on worksWith
    # We'll use the same worksWith as in the frontend
    products_allowed = {
        "crm": ["clinic", "solo", "personal"],
        "exercise-library": ["clinic", "solo", "personal"],
        "exercise-prescription": ["clinic", "solo", "personal"],
        "posture-tool": ["clinic", "solo", "personal"],
        "clinical-decision-support": ["clinic", "solo", "personal"],
        "psycho-social-screening": ["clinic", "solo", "personal"],
        "analytics": ["clinic", "solo", "personal"],
    }

    for product_id, allowed_types in products_allowed.items():
        bind.execute(
            sa.text(
                "UPDATE products SET allowed_clinic_types = :allowed_types "
                "WHERE id = :product_id"
            ).bindparams(
                sa.bindparam("allowed_types", type_=sa.ARRAY(sa.String())),
                sa.bindparam("product_id", type_=sa.String()),
            ),
            {"allowed_types": allowed_types, "product_id": product_id},
        )


def downgrade() -> None:
    # Remove columns
    op.drop_column("workspace_products", "valid_until")
    op.drop_column("workspace_products", "valid_from")
    op.drop_column("products", "allowed_clinic_types")
