"""workspace_membership_foundation

Revision ID: 65d7c21a9d4e
Revises: f1a2b3c4d6e7
Create Date: 2026-10-06

Adds workspace typing and explicit user-workspace memberships while preserving the
legacy clinic_id/role relationship as a compatibility layer.
"""

from typing import Sequence, Union
from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "65d7c21a9d4e"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        clinic_type = sa.Enum("clinic", "solo", "personal", name="clinic_type")
        clinic_type.create(bind, checkfirst=True)

    clinic_type_enum = sa.Enum(
        "clinic",
        "solo",
        "personal",
        name="clinic_type",
        create_type=False,
    )
    user_role_enum = sa.Enum(
        "admin",
        "therapist",
        "front_desk",
        "patient",
        name="user_role",
        create_type=False,
    )

    op.add_column(
        "clinics",
        sa.Column(
            "type",
            clinic_type_enum,
            nullable=False,
            server_default="clinic",
        ),
    )
    op.execute("UPDATE clinics SET type = 'clinic' WHERE type IS NULL")

    op.alter_column(
        "users",
        "clinic_id",
        existing_type=PGUUID(as_uuid=True),
        nullable=True,
    )

    op.create_table(
        "memberships",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("user_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "clinic_id", name="uq_memberships_user_clinic"),
    )
    op.create_index(
        "ix_memberships_clinic_user",
        "memberships",
        ["clinic_id", "user_id"],
        unique=False,
    )

    user_rows = (
        op.get_bind()
        .execute(
            sa.text("SELECT id, clinic_id, role FROM users WHERE clinic_id IS NOT NULL")
        )
        .fetchall()
    )

    if user_rows:
        now = datetime.now(timezone.utc)
        memberships = [
            {
                "id": str(uuid.uuid4()),
                "user_id": str(row[0]),
                "clinic_id": str(row[1]),
                "role": row[2],
                "created_at": now,
                "updated_at": now,
            }
            for row in user_rows
        ]
        op.bulk_insert(
            sa.table(
                "memberships",
                sa.column("id", PGUUID(as_uuid=True)),
                sa.column("user_id", PGUUID(as_uuid=True)),
                sa.column("clinic_id", PGUUID(as_uuid=True)),
                sa.column("role", user_role_enum),
                sa.column("created_at", sa.DateTime(timezone=True)),
                sa.column("updated_at", sa.DateTime(timezone=True)),
            ),
            memberships,
        )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_memberships_clinic_user", table_name="memberships")
    op.drop_table("memberships")
    op.drop_column("clinics", "type")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS clinic_type")
