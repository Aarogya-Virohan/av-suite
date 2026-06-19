"""add_user_names

Revision ID: 9f3c7a21e6b4
Revises: 17720d35ae64
Create Date: 2026-06-17

Adds first_name/last_name to users table so the prescribing physio's
actual name can be shown (e.g. on prescription PDFs). RegisterRequest
already collected these fields but they were never persisted.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '9f3c7a21e6b4'
down_revision: Union[str, Sequence[str], None] = '17720d35ae64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('first_name', sa.String(length=100), nullable=False))
    op.add_column('users', sa.Column('last_name', sa.String(length=100), nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
