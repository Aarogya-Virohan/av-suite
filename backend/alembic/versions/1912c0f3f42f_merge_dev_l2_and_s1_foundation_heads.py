"""merge dev L2 head and S1 platform foundation heads

No schema change. Joins a7d2c4e6f8b1 (dev, PR #77) and s1fnd20261120
(PR #74) so dev keeps a single Alembic head.

Rollback: never `downgrade -1` here. Use
`alembic downgrade a7d2c4e6f8b1` then `alembic downgrade s1fnd20261120@-1`.

Revision ID: 1912c0f3f42f
Revises: a7d2c4e6f8b1, s1fnd20261120
Create Date: 2026-11-21 23:00:00

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "1912c0f3f42f"
down_revision: Union[str, Sequence[str], None] = ("a7d2c4e6f8b1", "s1fnd20261120")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
