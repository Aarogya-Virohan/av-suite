"""merge workspace membership and exercise payment migration heads

Revision ID: 197a7f16b87d
Revises: 65d7c21a9d4e, c3a5f9d2e714
Create Date: 2026-10-07 08:45:56.536469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '197a7f16b87d'
down_revision: Union[str, Sequence[str], None] = ('65d7c21a9d4e', 'c3a5f9d2e714')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
