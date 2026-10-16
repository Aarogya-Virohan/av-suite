"""Extend specialty_type with canonical CRM specialties."""
from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "b72a91c4d605"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires these additions outside a transaction block.
    with op.get_context().autocommit_block():
        for value in ("ortho", "neuro", "cardiopulm", "sports", "paeds", "general"):
            op.execute(f"ALTER TYPE specialty_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum labels without recreating the type.
    pass
