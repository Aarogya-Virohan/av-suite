"""merge tool03 psychosocial and fee items heads

Revision ID: 6ab832834814
Revises: b8d4f0c6e3a1, cd4e8f2a91b7
Create Date: 2026-11-18 14:34:35.195040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ab832834814'
down_revision: Union[str, Sequence[str], None] = ('b8d4f0c6e3a1', 'cd4e8f2a91b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
