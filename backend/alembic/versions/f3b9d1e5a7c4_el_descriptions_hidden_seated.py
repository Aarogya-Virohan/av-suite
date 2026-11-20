"""EL descriptions (D1-D4), hidden "(seated)" copies, neck row rename

Revision ID: f3b9d1e5a7c4
Revises: e7c3a9f1b5d2
Create Date: 2026-11-20

Migration B (EL-D-016, EL-D-017). Data frozen in
alembic/data/el_descriptions_20nov.py, built by build_el_migration_b.py from
the D1-D4 CSVs (Onkar 20 Nov 10:30):

1. rx_mode may also be HIDDEN (not listed, searched or prescribed; row kept).
2. exercises.description for 2,863 global exercises (max 30 words, no
   "prescribed", no "the therapist" in patient rows). Only global rows; a
   row is written only while its description is still the 20 Nov value.
3. 73 "(seated)" copies that cannot be done seated -> HIDDEN.
4. Head-down postural drainage (RES-THO-01340, 01341) -> BLOCKED.
5. Row 660 renamed "Neck side-bend isometric (right)"; one body part fix.

Downgrade puts every value back (only where it still holds this
migration's value) and restores the rx_mode check. Roll back by name:
`alembic downgrade e7c3a9f1b5d2`.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3b9d1e5a7c4"
down_revision: Union[str, Sequence[str], None] = "e7c3a9f1b5d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _data():
    path = Path(__file__).resolve().parents[1] / "data" / "el_descriptions_20nov.py"
    spec = importlib.util.spec_from_file_location("el_descriptions_20nov", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_mode(ids, new: str, old: str) -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE exercises SET rx_mode = :new, updated_at = now() "
            "WHERE id IN (SELECT CAST(v AS uuid) FROM jsonb_array_elements_text(CAST(:ids AS jsonb)) AS t(v)) "
            "AND clinic_id IS NULL AND rx_mode = :old"
        ),
        {"ids": json.dumps(list(ids)), "new": new, "old": old},
    )


def upgrade() -> None:
    d = _data()
    bind = op.get_bind()
    op.drop_constraint("ck_exercises_rx_mode", "exercises", type_="check")
    op.create_check_constraint(
        "ck_exercises_rx_mode", "exercises", "rx_mode IN ('PATIENT', 'CAREGIVER', 'BLOCKED', 'HIDDEN')"
    )
    bind.execute(
        sa.text(
            "UPDATE exercises x SET description = r.d, updated_at = now() "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(e text, d text, o text) "
            "WHERE x.id = CAST(r.e AS uuid) AND x.clinic_id IS NULL "
            "AND x.description IS NOT DISTINCT FROM r.o"
        ),
        {"rows": json.dumps([{"e": e, "d": t, "o": o} for e, t, o in d.DESCRIPTIONS])},
    )
    _set_mode(d.HIDDEN, "HIDDEN", "PATIENT")
    _set_mode(d.BLOCKED, "BLOCKED", "PATIENT")
    ex_id, new_title, old_title = d.TITLE_FIX
    bind.execute(
        sa.text("UPDATE exercises SET title = :new, updated_at = now() WHERE id = CAST(:id AS uuid) AND title = :old"),
        {"id": ex_id, "new": new_title, "old": old_title},
    )
    for ex_id, new, old in d.BODY_PART_FIX:
        bind.execute(
            sa.text(
                "UPDATE exercises SET body_part = :new, updated_at = now() "
                "WHERE id = CAST(:id AS uuid) AND body_part = :old"
            ),
            {"id": ex_id, "new": new, "old": old},
        )


def downgrade() -> None:
    d = _data()
    bind = op.get_bind()
    for ex_id, new, old in d.BODY_PART_FIX:
        bind.execute(
            sa.text(
                "UPDATE exercises SET body_part = :old, updated_at = now() "
                "WHERE id = CAST(:id AS uuid) AND body_part = :new"
            ),
            {"id": ex_id, "new": new, "old": old},
        )
    ex_id, new_title, old_title = d.TITLE_FIX
    bind.execute(
        sa.text("UPDATE exercises SET title = :old, updated_at = now() WHERE id = CAST(:id AS uuid) AND title = :new"),
        {"id": ex_id, "new": new_title, "old": old_title},
    )
    _set_mode(d.BLOCKED, "PATIENT", "BLOCKED")
    _set_mode(d.HIDDEN, "PATIENT", "HIDDEN")
    bind.execute(
        sa.text(
            "UPDATE exercises x SET description = r.o, updated_at = now() "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(e text, d text, o text) "
            "WHERE x.id = CAST(r.e AS uuid) AND x.clinic_id IS NULL AND x.description = r.d"
        ),
        {"rows": json.dumps([{"e": e, "d": t, "o": o} for e, t, o in d.DESCRIPTIONS])},
    )
    # Any HIDDEN row left (set by hand later) goes back to PATIENT so the old check holds.
    bind.execute(sa.text("UPDATE exercises SET rx_mode = 'PATIENT' WHERE rx_mode = 'HIDDEN'"))
    op.drop_constraint("ck_exercises_rx_mode", "exercises", type_="check")
    op.create_check_constraint(
        "ck_exercises_rx_mode", "exercises", "rx_mode IN ('PATIENT', 'CAREGIVER', 'BLOCKED')"
    )
