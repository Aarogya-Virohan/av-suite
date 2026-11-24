"""clinics.code: stored prefix of the Patient ID (delivery item 10, 24 Nov 2026).

Until now the CRM worked the "ADP" in ADP-000003 out of the clinic name on every
screen. This adds clinics.code, filled for every existing clinic with exactly
that value, unique across clinics, and editable in Settings.

Backfill rule (same as frontend/crm/src/lib/patientNumber.ts): first letter of
up to 3 words, else the first 3 letters of a one-word name, else "PT". If two
clinics would get the same code, the one created first keeps it and the next
gets a number added (ADP, ADP2, ADP3). The count is written to the migration log.

Downgrade drops the column only; no other data is touched.

Revision ID: crm10code20261124
Revises: be1fixes20261124
"""
import logging
import re

import sqlalchemy as sa
from alembic import op

revision = "crm10code20261124"
down_revision = "be1fixes20261124"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def _derive(name):
    words = _WORD.findall(name or "")
    if not words:
        return "PT"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def _next_free(base, taken):
    if base not in taken:
        return base
    n = 2
    while True:
        suffix = str(n)
        candidate = base[: 6 - len(suffix)] + suffix
        if candidate not in taken:
            return candidate
        n += 1


def upgrade() -> None:
    op.add_column("clinics", sa.Column("code", sa.String(length=6), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, name FROM clinics ORDER BY created_at ASC, id ASC")
    ).fetchall()
    taken: set[str] = set()
    changed = 0
    for clinic_id, name in rows:
        base = _derive(name)
        code = _next_free(base, taken)
        if code != base:
            changed += 1
        taken.add(code)
        bind.execute(
            sa.text("UPDATE clinics SET code = :code WHERE id = :id"),
            {"code": code, "id": clinic_id},
        )
    if changed:
        log.warning(
            "clinics.code: %d of %d clinics share their name initials with an earlier "
            "clinic and got a number added",
            changed,
            len(rows),
        )
    op.alter_column("clinics", "code", nullable=False)
    op.create_unique_constraint("uq_clinics_code", "clinics", ["code"])
    op.create_check_constraint("ck_clinics_code_length", "clinics", "length(code) BETWEEN 1 AND 6")


def downgrade() -> None:
    op.drop_constraint("ck_clinics_code_length", "clinics", type_="check")
    op.drop_constraint("uq_clinics_code", "clinics", type_="unique")
    op.drop_column("clinics", "code")
