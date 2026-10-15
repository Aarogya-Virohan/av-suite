"""add unique clinic slug

Revision ID: 8a4c1e6b2d90
Revises: 7899ed1701fb
Create Date: 2026-10-15
"""

import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a4c1e6b2d90"
down_revision: Union[str, Sequence[str], None] = "7899ed1701fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "clinic"


def _valid_slug(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value))


def upgrade() -> None:
    op.add_column("clinics", sa.Column("slug", sa.String(length=120), nullable=True))
    bind = op.get_bind()
    clinics = sa.table(
        "clinics",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
    )
    rows = bind.execute(sa.select(clinics.c.id, clinics.c.name, clinics.c.slug).order_by(clinics.c.id)).all()

    # Reserve valid legacy values first so a generated name slug cannot steal one.
    valid_values = [row.slug for row in rows if _valid_slug(row.slug)]
    reserved = set(valid_values)
    used: set[str] = set()
    for row in rows:
        existing = row.slug
        if _valid_slug(existing) and existing not in used:
            slug = existing
        else:
            base = _slugify(existing if existing else row.name)[:120].rstrip("-") or "clinic"
            slug = base
            suffix = 2
            while slug in used or slug in reserved:
                ending = f"-{suffix}"
                slug = f"{base[:120-len(ending)].rstrip('-')}{ending}"
                suffix += 1
        used.add(slug)
        bind.execute(
            clinics.update().where(clinics.c.id == row.id).values(slug=slug)
        )

    op.alter_column("clinics", "slug", nullable=False)
    op.create_unique_constraint("uq_clinics_slug", "clinics", ["slug"])


def downgrade() -> None:
    op.drop_constraint("uq_clinics_slug", "clinics", type_="unique")
    op.drop_column("clinics", "slug")
