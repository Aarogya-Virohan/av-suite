"""merge release/el-nov and dev heads

Revision ID: 81ebc274f369
Revises: a3d8f1c5e7b2, f2b6c8d0a134
Create Date: 2026-11-12

Joins the Exercise Library head (a3d8f1c5e7b2, exercise templates) with the
production head from the October CRM round (f2b6c8d0a134, profile fields).
No schema change: the two branches touch different tables.
"""

from typing import Sequence, Union

revision: str = "81ebc274f369"
down_revision: Union[str, Sequence[str], None] = ("a3d8f1c5e7b2", "f2b6c8d0a134")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
