"""add product entitlements

Revision ID: 6b0f1d2c3a4e
Revises: 197a7f16b87d
Create Date: 2026-10-07
"""

from datetime import datetime, timezone
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID as PGUUID

revision: str = "6b0f1d2c3a4e"
down_revision: Union[str, Sequence[str], None] = "197a7f16b87d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CANONICAL_PRODUCTS = (
    {
        "id": "crm",
        "slug": "crm",
        "name": "CRM",
        "description": "Patient management, scheduling and clinic operations.",
        "category": "Patient Management",
    },
    {
        "id": "exercise-library",
        "slug": "exercise-library",
        "name": "Exercise Library",
        "description": "Clinical exercise resources and structured exercise programs.",
        "category": "Clinical",
    },
    {
        "id": "exercise-prescription",
        "slug": "exercise-prescription",
        "name": "Exercise Prescription",
        "description": "Build and manage personalized exercise programs.",
        "category": "Clinical",
    },
    {
        "id": "posture-tool",
        "slug": "posture-tool",
        "name": "Posture Tool",
        "description": "Posture assessment and movement analysis.",
        "category": "Clinical",
    },
    {
        "id": "clinical-decision-support",
        "slug": "clinical-decision-support",
        "name": "Clinical Decision Support",
        "description": "Structured clinical insights for better decision-making.",
        "category": "Clinical",
    },
    {
        "id": "psycho-social-screening",
        "slug": "psycho-social-screening",
        "name": "Psycho-social Screening",
        "description": "Screening and tracking for psycho-social factors.",
        "category": "Clinical",
    },
    {
        "id": "analytics",
        "slug": "analytics",
        "name": "Analytics",
        "description": "Clinical and operational insights for your workspace.",
        "category": "Analytics",
    },
)


entitlement_status = ENUM(
    "enabled",
    "disabled",
    name="entitlement_status",
    create_type=False,
)
entitlement_source = ENUM(
    "direct",
    "bundle",
    name="entitlement_source",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        entitlement_status.create(bind, checkfirst=True)
        entitlement_source.create(bind, checkfirst=True)

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
    )
    op.create_table(
        "platform_bundles",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_platform_bundles_slug"),
    )
    op.create_table(
        "platform_bundle_products",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bundle_id"], ["platform_bundles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bundle_id",
            "product_id",
            name="uq_platform_bundle_products_bundle_product",
        ),
    )
    op.create_index(
        "ix_platform_bundle_products_product_id",
        "platform_bundle_products",
        ["product_id"],
        unique=False,
    )
    op.create_table(
        "workspace_products",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("status", entitlement_status, nullable=False),
        sa.Column("source", entitlement_source, nullable=False),
        sa.Column("bundle_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bundle_id"], ["platform_bundles.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "clinic_id",
            "product_id",
            name="uq_workspace_products_clinic_product",
        ),
    )
    op.create_index(
        "ix_workspace_products_clinic_status",
        "workspace_products",
        ["clinic_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_products_product_id",
        "workspace_products",
        ["product_id"],
        unique=False,
    )

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        sa.table(
            "products",
            sa.column("id", sa.String(length=80)),
            sa.column("slug", sa.String(length=120)),
            sa.column("name", sa.String(length=255)),
            sa.column("description", sa.Text()),
            sa.column("category", sa.String(length=100)),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {**product, "created_at": now, "updated_at": now}
            for product in CANONICAL_PRODUCTS
        ],
    )

    clinic_rows = bind.execute(sa.text("SELECT id FROM clinics")).fetchall()
    if clinic_rows:
        op.bulk_insert(
            sa.table(
                "workspace_products",
                sa.column("id", PGUUID(as_uuid=True)),
                sa.column("clinic_id", PGUUID(as_uuid=True)),
                sa.column("product_id", sa.String(length=80)),
                sa.column("status", entitlement_status),
                sa.column("source", entitlement_source),
                sa.column("bundle_id", PGUUID(as_uuid=True)),
                sa.column("created_at", sa.DateTime(timezone=True)),
                sa.column("updated_at", sa.DateTime(timezone=True)),
            ),
            [
                {
                    "id": uuid.uuid4(),
                    "clinic_id": uuid.UUID(str(row[0])),
                    "product_id": "crm",
                    "status": "enabled",
                    "source": "direct",
                    "bundle_id": None,
                    "created_at": now,
                    "updated_at": now,
                }
                for row in clinic_rows
            ],
        )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_workspace_products_product_id", table_name="workspace_products")
    op.drop_index(
        "ix_workspace_products_clinic_status", table_name="workspace_products"
    )
    op.drop_table("workspace_products")
    op.drop_index(
        "ix_platform_bundle_products_product_id",
        table_name="platform_bundle_products",
    )
    op.drop_table("platform_bundle_products")
    op.drop_table("platform_bundles")
    op.drop_table("products")

    if bind.dialect.name == "postgresql":
        entitlement_source.drop(bind, checkfirst=True)
        entitlement_status.drop(bind, checkfirst=True)
