"""user_permissions unique per clinic (AUD-07, BE-1)

The old UNIQUE (user_id, capability_key) ignored clinic_id, so a user with an
override in clinic A could not get the same override in clinic B (500).
Overrides are per clinic everywhere in the code, so the key is now
(clinic_id, user_id, capability_key). Only widens what is allowed: no data
change on upgrade.

Revision ID: a7d2c4e6f8b1
Revises: f3b9d1e5a7c4 (PR #75 EL head; was 6ab832834814 before the L2 rebase)
Create Date: 2026-11-20 19:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7d2c4e6f8b1"
down_revision: Union[str, Sequence[str], None] = "f3b9d1e5a7c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_user_permissions_user_capability", "user_permissions", type_="unique"
    )
    op.create_unique_constraint(
        "uq_user_permissions_clinic_user_capability",
        "user_permissions",
        ["clinic_id", "user_id", "capability_key"],
    )


def downgrade() -> None:
    dupes = op.get_bind().execute(
        sa.text(
            "SELECT count(*) FROM (SELECT user_id, capability_key FROM user_permissions"
            " GROUP BY user_id, capability_key HAVING count(*) > 1) d"
        )
    ).scalar()
    if dupes:
        raise RuntimeError(
            f"Cannot restore UNIQUE (user_id, capability_key): {dupes} user/capability"
            " pairs have overrides in more than one clinic. Remove those rows first."
        )
    op.drop_constraint(
        "uq_user_permissions_clinic_user_capability", "user_permissions", type_="unique"
    )
    op.create_unique_constraint(
        "uq_user_permissions_user_capability",
        "user_permissions",
        ["user_id", "capability_key"],
    )
