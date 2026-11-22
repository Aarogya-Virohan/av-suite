"""Add organization foundation and clinic suspension state.

Revision ID: s1fnd20261120
Revises: 6ab832834814
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "s1fnd20261120"
down_revision = "6ab832834814"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "type IN ('individual', 'clinic', 'chain', 'franchise', 'hospital', 'government', 'partner_platform')",
            name="ck_organizations_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended')", name="ck_organizations_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "role IN ('org_owner', 'org_admin', 'org_viewer')",
            name="ck_organization_memberships_role",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_organization_memberships_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_organization_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "organization_id", name="uq_organization_memberships_user_org"
        ),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )

    op.add_column(
        "clinics", sa.Column("organization_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_clinics_organization_id_organizations",
        "clinics",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.add_column(
        "clinics",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_clinics_status", "clinics", "status IN ('active', 'suspended')"
    )

    connection = op.get_bind()
    clinics = connection.execute(
        sa.text("SELECT id, name, slug, type::text AS clinic_type FROM clinics")
    ).mappings()
    clinic_org_ids: dict[uuid.UUID, uuid.UUID] = {}
    for clinic in clinics:
        organization_id = uuid.uuid4()
        clinic_id = clinic["id"]
        clinic_org_ids[clinic_id] = organization_id
        clinic_type = clinic["clinic_type"]
        organization_type = (
            "individual" if clinic_type in ("solo", "personal") else "clinic"
        )
        connection.execute(
            sa.text(
                """INSERT INTO organizations (id, name, slug, type, status)
                   VALUES (:id, :name, :slug, :type, 'active')"""
            ),
            {
                "id": organization_id,
                "name": clinic["name"],
                "slug": clinic["slug"],
                "type": organization_type,
            },
        )
        connection.execute(
            sa.text("UPDATE clinics SET organization_id = :organization_id WHERE id = :id"),
            {"organization_id": organization_id, "id": clinic_id},
        )

    admin_memberships = connection.execute(
        sa.text(
            """SELECT user_id, clinic_id
               FROM memberships
               WHERE role::text = 'admin'"""
        )
    ).mappings()
    for membership in admin_memberships:
        organization_id = clinic_org_ids.get(membership["clinic_id"])
        if organization_id is None:
            continue
        connection.execute(
            sa.text(
                """INSERT INTO organization_memberships
                       (id, user_id, organization_id, role)
                   SELECT :id, :user_id, :organization_id, 'org_owner'
                   WHERE NOT EXISTS (
                       SELECT 1 FROM organization_memberships
                       WHERE user_id = :user_id AND organization_id = :organization_id
                   )"""
            ),
            {
                "id": uuid.uuid4(),
                "user_id": membership["user_id"],
                "organization_id": organization_id,
            },
        )

    op.alter_column("clinics", "organization_id", nullable=False)
    op.create_index("ix_clinics_organization_id", "clinics", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_clinics_organization_id", table_name="clinics")
    op.drop_constraint("ck_clinics_status", "clinics", type_="check")
    op.drop_column("clinics", "status")
    op.drop_constraint(
        "fk_clinics_organization_id_organizations", "clinics", type_="foreignkey"
    )
    op.drop_column("clinics", "organization_id")
    op.drop_index(
        "ix_organization_memberships_organization_id",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
