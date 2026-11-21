"""EL structure: domains + categories, new bank exercises, rx_mode, Rx side

Revision ID: e7c3a9f1b5d2
Revises: 6ab832834814
Create Date: 2026-11-20

Exercise Library structure for the 22 Nov launch (EL-D-012..EL-D-016,
claude/ref/el-content-plan.md v3 section 5):

1. Columns: exercises.rx_mode (PATIENT / CAREGIVER / BLOCKED, default
   PATIENT), exercises.requires_side, exercises.bank_key (exercise bank ID);
   prescription_items.side ("left" / "right").
2. Two more tag groups in exercise_categories: "domain" (9) and "category"
   (51), ids uuid5("<group>:<name>") like EL-D-005.
3. New exercises from the founders' exercise bank that are not already in the
   library (v4 matcher: one-to-one SAME, default equipment, body-region
   filter, opposite movements, synonyms): global, visible, fixed ids
   uuid5(BANK_NS, bank Exercise ID), rx_mode from "Performed by" and SR24.
   A row is skipped if a global exercise with the same title exists.
4. Every global exercise (existing and new) gets its domain and category.
   Existing rows are never deleted or renamed; matched rows get bank_key.
5. EL-4: the 8 Blogspot picture links are cleared; the neck isometric row
   saved under "Other" gets body part "Neck". Downgrade puts both back.

Data: alembic/data/el_structure_20nov.py (frozen, generated).

Downgrade removes the two tag groups (links go with them), the new exercises
that no prescription, template or clinic photo uses, the Blogspot / body
part fixes, and the columns. Roll back by name: `alembic downgrade
6ab832834814` (never a8c4e2f1d903).
"""

from __future__ import annotations

import importlib.util
import json
import uuid
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7c3a9f1b5d2"
down_revision: Union[str, Sequence[str], None] = "6ab832834814"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same namespace as app/services/exercise_categories.py (EL-D-005). Never change.
NAMESPACE = uuid.UUID("6f1c2b8e-4a7d-5e93-9b1f-0c3d5a7e9f21")
# Namespace of new bank exercise ids. Never change.
BANK_NS = uuid.UUID("b7e0c3a2-5d14-5f6e-9a8b-2c4d6e8f0a13")


def _data():
    path = Path(__file__).resolve().parents[1] / "data" / "el_structure_20nov.py"
    spec = importlib.util.spec_from_file_location("el_structure_20nov", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sid(group: str, name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{group}:{name}"))


def _norm(column: str) -> str:
    return f"lower(regexp_replace(btrim({column}), '\\s+', ' ', 'g'))"


def upgrade() -> None:
    d = _data()
    bind = op.get_bind()

    # 1. columns
    op.add_column(
        "exercises",
        sa.Column("rx_mode", sa.String(16), nullable=False, server_default=sa.text("'PATIENT'")),
    )
    op.create_check_constraint(
        "ck_exercises_rx_mode", "exercises", "rx_mode IN ('PATIENT', 'CAREGIVER', 'BLOCKED')"
    )
    op.add_column(
        "exercises",
        sa.Column("requires_side", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("exercises", sa.Column("bank_key", sa.String(32), nullable=True))
    op.create_index("ix_exercises_bank_key", "exercises", ["bank_key"])
    op.add_column("prescription_items", sa.Column("side", sa.String(10), nullable=True))
    op.create_check_constraint(
        "ck_prescription_items_side", "prescription_items", "side IS NULL OR side IN ('left', 'right')"
    )

    # 2. domain + category tag values
    cats = [
        {"id": _sid("domain", name), "g": "domain", "n": name, "s": i} for i, name in enumerate(d.DOMAINS)
    ] + [
        {"id": _sid("category", c), "g": "category", "n": c, "s": i} for i, (_dom, c) in enumerate(d.CATEGORIES)
    ]
    bind.execute(
        sa.text(
            "INSERT INTO exercise_categories (id, group_key, name, sort_order, is_active) "
            "SELECT CAST(r.id AS uuid), r.g, r.n, r.s, true "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(id text, g text, n text, s int) "
            "ON CONFLICT DO NOTHING"
        ),
        {"rows": json.dumps(cats)},
    )

    # 3. new exercises from the bank
    new = [
        {"id": i, "k": key, "t": title, "b": body, "m": mode, "r": bool(side)}
        for i, key, title, body, _cat, mode, side in d.NEW
    ]
    bind.execute(
        sa.text(
            "INSERT INTO exercises (id, clinic_id, title, description, body_part, is_free, video_url, "
            "rx_mode, requires_side, bank_key) "
            "SELECT CAST(r.id AS uuid), NULL, r.t, NULL, r.b, true, NULL, r.m, r.r, r.k "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(id text, k text, t text, b text, m text, r boolean) "
            "WHERE NOT EXISTS (SELECT 1 FROM exercises e WHERE e.clinic_id IS NULL "
            "AND " + _norm("e.title") + " = " + _norm("r.t") + ") "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"rows": json.dumps(new)},
    )

    # 4. domain + category links for every global exercise; bank_key on matches
    cat_domain = {c: dom for dom, c in d.CATEGORIES}
    pairs = [(i, cat) for i, cat, _key in d.PROD] + [(row[0], row[4]) for row in d.NEW]
    links = []
    for ex_id, cat in pairs:
        links.append({"e": ex_id, "c": _sid("category", cat)})
        links.append({"e": ex_id, "c": _sid("domain", cat_domain[cat])})
    bind.execute(
        sa.text(
            "INSERT INTO exercise_category_links (exercise_id, category_id) "
            "SELECT CAST(r.e AS uuid), CAST(r.c AS uuid) "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(e text, c text) "
            "WHERE EXISTS (SELECT 1 FROM exercises x WHERE x.id = CAST(r.e AS uuid) AND x.clinic_id IS NULL) "
            "ON CONFLICT DO NOTHING"
        ),
        {"rows": json.dumps(links)},
    )
    keys = [{"e": i, "k": key} for i, _cat, key in d.PROD if key]
    bind.execute(
        sa.text(
            "UPDATE exercises x SET bank_key = r.k "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(e text, k text) "
            "WHERE x.id = CAST(r.e AS uuid) AND x.clinic_id IS NULL AND x.bank_key IS NULL"
        ),
        {"rows": json.dumps(keys)},
    )

    # 5. EL-4 data clean
    bind.execute(
        sa.text(
            "UPDATE exercises x SET video_url = NULL, updated_at = now() "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(e text, u text) "
            "WHERE x.id = CAST(r.e AS uuid) AND x.clinic_id IS NULL AND x.video_url = r.u"
        ),
        {"rows": json.dumps([{"e": e, "u": u} for e, u in d.BLOGSPOT])},
    )
    for ex_id, new_part, old_part in d.BODY_PART_FIX:
        bind.execute(
            sa.text(
                "UPDATE exercises SET body_part = :new, updated_at = now() "
                "WHERE id = CAST(:id AS uuid) AND clinic_id IS NULL AND body_part = :old"
            ),
            {"id": ex_id, "new": new_part, "old": old_part},
        )


def downgrade() -> None:
    d = _data()
    bind = op.get_bind()

    for ex_id, new_part, old_part in d.BODY_PART_FIX:
        bind.execute(
            sa.text(
                "UPDATE exercises SET body_part = :old, updated_at = now() "
                "WHERE id = CAST(:id AS uuid) AND clinic_id IS NULL AND body_part = :new"
            ),
            {"id": ex_id, "new": new_part, "old": old_part},
        )
    bind.execute(
        sa.text(
            "UPDATE exercises x SET video_url = r.u, updated_at = now() "
            "FROM jsonb_to_recordset(CAST(:rows AS jsonb)) AS r(e text, u text) "
            "WHERE x.id = CAST(r.e AS uuid) AND x.clinic_id IS NULL AND x.video_url IS NULL"
        ),
        {"rows": json.dumps([{"e": e, "u": u} for e, u in d.BLOGSPOT])},
    )

    # Links go with their categories (ON DELETE CASCADE).
    bind.execute(sa.text("DELETE FROM exercise_categories WHERE group_key IN ('domain', 'category')"))

    bind.execute(
        sa.text(
            "DELETE FROM exercises e USING jsonb_array_elements_text(CAST(:ids AS jsonb)) AS n(v) "
            "WHERE e.id = CAST(n.v AS uuid) AND e.clinic_id IS NULL "
            "AND NOT EXISTS (SELECT 1 FROM prescription_items p WHERE p.exercise_id = e.id) "
            "AND NOT EXISTS (SELECT 1 FROM exercise_template_items t WHERE t.exercise_id = e.id) "
            "AND NOT EXISTS (SELECT 1 FROM exercise_photos ph WHERE ph.exercise_id = e.id)"
        ),
        {"ids": json.dumps([row[0] for row in d.NEW])},
    )

    op.drop_constraint("ck_prescription_items_side", "prescription_items", type_="check")
    op.drop_column("prescription_items", "side")
    op.drop_index("ix_exercises_bank_key", table_name="exercises")
    op.drop_column("exercises", "bank_key")
    op.drop_column("exercises", "requires_side")
    op.drop_constraint("ck_exercises_rx_mode", "exercises", type_="check")
    op.drop_column("exercises", "rx_mode")
