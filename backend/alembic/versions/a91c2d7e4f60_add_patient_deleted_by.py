"""add patient deleted_by attribution

Revision ID: a91c2d7e4f60
Revises: 7899ed1701fb
Create Date: 2026-10-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a91c2d7e4f60"
down_revision: Union[str, Sequence[str], None] = "8a4c1e6b2d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("deleted_by", sa.UUID(), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "deleted_by")
