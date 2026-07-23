"""add_front_desk_role

Revision ID: a3f5e8c2d1b7
Revises: 9f3c7a21e6b4
Create Date: 2026-07-23

Adds 'front_desk' to the userrole enum for the CRM module.
ALTER TYPE ADD VALUE must run outside a transaction block in Postgres.
"""
from alembic import op

revision = 'a3f5e8c2d1b7'
down_revision = '9f3c7a21e6b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'front_desk'")


def downgrade() -> None:
    # Postgres does not support removing enum values directly.
    # A downgrade would require recreating the type; left as a no-op
    # since this is additive and safe to leave in place.
    pass
