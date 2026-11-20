"""
Build the description data for Migration B (EL-D-016) from the D1-D4 CSVs.

Usage (Sat 21 Nov, after the four description chats deliver):

    python alembic/data/build_el_descriptions.py \
        --prod-export prod_exercises_20Nov.csv \
        --out alembic/data/el_descriptions_21nov.py \
        d1.csv d2.csv d3.csv d4.csv

CSV columns (all four files): key, title or name, old_description,
new_description, action, words. D1-D3 key = prod exercise id (uuid),
D4 key = bank Exercise ID (e.g. "BAL-FAC-01072-v1").

Rules (Onkar 20 Nov):
- refused: more than 30 words, or contains "prescribed" (any case);
- skipped: action EDIT-SUGGEST (a clinic's own text), empty new_description;
- test-clinic rows are never written (ON-7): only global exercises;
- a D4 row maps to the new bank row (uuid5 of its ID) or, for a bank row
  that matched an existing exercise (SAME), to that exercise; if D1-D3 also
  wrote that exercise, D1-D3 wins;
- warned, not refused: "the therapist" or "preset" in the text (plan C4).
- The neck isometric row saved under "Other" gets the title D2 gives it
  (EL-4); no other title changes.

Prints a report and writes a frozen data module. Nothing touches a database.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import pprint
import re
import sys
import uuid
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK_NS = uuid.UUID("b7e0c3a2-5d14-5f6e-9a8b-2c4d6e8f0a13")
MAX_WORDS = 30
LATERAL_FLEXION_ID = "1b16c80a-a684-4cec-8762-60ef44203647"


def _structure():
    spec = importlib.util.spec_from_file_location("el_structure_20nov", HERE / "el_structure_20nov.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'’-]+", text or ""))


def _get(row: dict, *names: str) -> str:
    for n in names:
        for k, v in row.items():
            if k and k.strip().lower() == n:
                return (v or "").strip()
    return ""


def build(files: list[Path], prod_export: Path):
    st = _structure()
    prod_rows = list(csv.DictReader(open(prod_export, encoding="utf-8")))
    global_ids = {r["id"] for r in prod_rows if r["clinic_id"] in ("null", "", None)}
    old_desc = {r["id"]: (None if r["description"] in ("null", "") else r["description"]) for r in prod_rows}
    old_title = {r["id"]: r["title"] for r in prod_rows}
    new_ids = {row[1]: row[0] for row in st.NEW}
    same = {key: ex_id for ex_id, _cat, key in st.PROD if key}

    chosen: dict[str, tuple[str, str, str]] = {}  # exercise id -> (text, source, title)
    report = Counter()
    rejected, warned, unknown, conflicts = [], [], [], []
    title_fix = None

    for path in files:
        for row in csv.DictReader(open(path, encoding="utf-8-sig")):
            key = _get(row, "key")
            text = " ".join(_get(row, "new_description").split())
            action = _get(row, "action").upper()
            title = _get(row, "title", "name")
            report["rows"] += 1
            if not key:
                report["no key"] += 1
                continue
            if action == "EDIT-SUGGEST":
                report["skipped EDIT-SUGGEST"] += 1
                continue
            if not text:
                report["skipped empty"] += 1
                continue
            is_bank = not re.fullmatch(r"[0-9a-fA-F-]{36}", key)
            if is_bank:
                ex_id = new_ids.get(key) or same.get(key)
                source = "bank"
            else:
                ex_id, source = key.lower(), "prod"
                if ex_id not in global_ids:
                    report["skipped not global (test clinic or unknown)"] += 1
                    unknown.append((path.name, key, title))
                    continue
            if not ex_id:
                unknown.append((path.name, key, title))
                report["unknown key"] += 1
                continue
            n = words(text)
            if n > MAX_WORDS or "prescribed" in text.lower():
                rejected.append((path.name, key, title, n, text))
                report["refused"] += 1
                continue
            if re.search(r"\bthe therapist\b|\bpreset\b", text, re.I):
                warned.append((path.name, key, title, text))
            if ex_id in chosen:
                prev = chosen[ex_id]
                if prev[1] == "prod" and source == "bank":
                    conflicts.append((ex_id, "kept D1-D3, dropped D4", key))
                    continue
                conflicts.append((ex_id, f"duplicate {source} row, last one kept", key))
            chosen[ex_id] = (text, source, title)
            if ex_id == LATERAL_FLEXION_ID and title and title != old_title.get(ex_id):
                title_fix = (ex_id, title, old_title.get(ex_id))
    report["accepted"] = len(chosen)
    descriptions = sorted([ex_id, text, old_desc.get(ex_id)] for ex_id, (text, _s, _t) in chosen.items())
    return descriptions, title_fix, report, rejected, warned, unknown, conflicts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod-export", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("files", nargs="+", type=Path)
    a = ap.parse_args(argv)
    descriptions, title_fix, report, rejected, warned, unknown, conflicts = build(a.files, a.prod_export)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write('"""Descriptions for Migration B (EL-D-016). Generated by build_el_descriptions.py; do not edit."""\n\n')
        f.write("# [exercise id, new description, description before (prod 20 Nov export) or None]\n")
        f.write("DESCRIPTIONS = " + pprint.pformat(descriptions, width=200) + "\n\n")
        f.write("# (exercise id, new title, old title) or None\n")
        f.write("TITLE_FIX = " + pprint.pformat(title_fix) + "\n")
    print("report:", dict(report))
    for name, items in (("refused", rejected), ("warned", warned), ("unknown", unknown), ("conflicts", conflicts)):
        print(f"{name}: {len(items)}")
        for it in items[:200]:
            print("   ", it)
    return 0


if __name__ == "__main__":
    sys.exit(main())
