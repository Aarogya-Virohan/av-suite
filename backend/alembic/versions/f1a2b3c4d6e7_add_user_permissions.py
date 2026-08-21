"""add_user_permissions

Revision ID: f1a2b3c4d6e7
Revises: e9f1a2b3c4d5
Create Date: 2026-08-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision: str = "f1a2b3c4d6e7"
down_revision: Union[str, Sequence[str], None] = "e9f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


capability_scope = sa.Enum("none", "own", "all", name="capability_scope")


def upgrade() -> None:
    bind = op.get_bind()
    capability_scope.create(bind, checkfirst=True)

    op.create_table(
        "user_permissions",
        sa.Column("id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("user_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("capability_key", sa.String(length=150), nullable=False),
        sa.Column("scope", capability_scope, nullable=False),
        sa.Column("granted_by", PGUUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "capability_key", name="uq_user_permissions_user_capability"),
    )
    op.create_index(
        "ix_user_permissions_clinic_user",
        "user_permissions",
        ["clinic_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_permissions_clinic_user", table_name="user_permissions")
    op.drop_table("user_permissions")
    capability_scope.drop(op.get_bind(), checkfirst=True)
