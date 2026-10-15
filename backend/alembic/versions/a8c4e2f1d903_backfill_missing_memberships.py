"""backfill users that are missing memberships

Revision ID: a8c4e2f1d903
Revises: 7899ed1701fb
Create Date: 2026-10-15
"""

from datetime import datetime, timezone
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID as PGUUID

revision: str = "a8c4e2f1d903"
down_revision: Union[str, Sequence[str], None] = "7899ed1701fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role_enum = ENUM(
    "admin",
    "therapist",
    "front_desk",
    "patient",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    missing_users = bind.execute(
        sa.text(
            "SELECT users.id, users.clinic_id, users.role "
            "FROM users "
            "WHERE users.clinic_id IS NOT NULL "
            "AND NOT EXISTS ("
            "    SELECT 1 FROM memberships "
            "    WHERE memberships.user_id = users.id"
            ")"
        )
    ).fetchall()
    if not missing_users:
        return

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        sa.table(
            "memberships",
            sa.column("id", PGUUID(as_uuid=True)),
            sa.column("user_id", PGUUID(as_uuid=True)),
            sa.column("clinic_id", PGUUID(as_uuid=True)),
            sa.column("role", user_role_enum),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": uuid.uuid4(),
                "user_id": row.id,
                "clinic_id": row.clinic_id,
                "role": row.role,
                "created_at": now,
                "updated_at": now,
            }
            for row in missing_users
        ],
    )


def downgrade() -> None:
    # Backfilled memberships are indistinguishable from later memberships, so
    # reversing this data migration could delete valid membership changes.
    pass
