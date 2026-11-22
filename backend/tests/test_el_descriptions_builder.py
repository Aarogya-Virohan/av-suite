"""Migration B data builder (EL-D-016): refuse > 30 words and "prescribed",
skip EDIT-SUGGEST and test-clinic rows, map bank IDs, D1-D3 wins over D4,
only the neck isometric row may get a new title."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("builder", ROOT / "alembic" / "data" / "build_el_descriptions.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
data_spec = importlib.util.spec_from_file_location("eldata", ROOT / "alembic" / "data" / "el_structure_20nov.py")
eldata = importlib.util.module_from_spec(data_spec)
data_spec.loader.exec_module(eldata)

GLOBAL = [r[0] for r in eldata.PROD]
TEST_CLINIC_ID = "26864332-f65d-4778-87a7-027a2baeaff5"
H = ["key", "title", "old_description", "new_description", "action", "words"]


def _csv(path: Path, rows: list[list]) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(H)
        w.writerows(rows)
    return path


def test_rules(tmp_path: Path) -> None:
    same_prod, same_bank = next((ex, key) for ex, _c, key in eldata.PROD if key)
    export = _csv(tmp_path / "export.csv", [])
    with open(export, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "clinic_id", "title", "body_part", "description", "video_url", "is_free"])
        for i in GLOBAL[:5] + [same_prod]:
            w.writerow([i, "null", "T", "Hip", "null", "null", "true"])
        w.writerow([builder.LATERAL_FLEXION_ID, "null", "LATERAL FLEXION  ISOMETRIC  – Right Side", "Other",
                    "old text", "null", "true"])
        w.writerow([TEST_CLINIC_ID, "abc", "Test", "Neck", "null", "null", "true"])
    new_bank, new_id = eldata.NEW[0][1], eldata.NEW[0][0]
    d1 = _csv(tmp_path / "d1.csv", [
        [GLOBAL[0], "T", "", "Stand tall and march on the spot.", "NEW", 7],
        [GLOBAL[1], "T", "", "x " * 31, "NEW", 31],
        [GLOBAL[2], "T", "", "Do it as Prescribed.", "NEW", 4],
        [GLOBAL[3], "T", "", "Clinic text.", "EDIT-SUGGEST", 2],
        [TEST_CLINIC_ID, "Test", "", "Never written.", "NEW", 2],
        [builder.LATERAL_FLEXION_ID, "Neck side-bend isometric (right)", "old text",
         "Sit tall. Press your head into your right hand. Hold, then relax.", "REWRITE", 12],
        [same_prod, "T", "", "From D1.", "NEW", 2],
    ])
    d4 = _csv(tmp_path / "d4.csv", [
        [new_bank, "N", "", "From D4 for a new row.", "NEW", 6],
        [same_bank, "N", "", "From D4 for a SAME row.", "NEW", 6],
        ["ZZZ-ZZZ-00000-v1", "N", "", "Unknown.", "NEW", 1],
    ])
    desc, title_fix, report, rejected, _w, unknown, conflicts = builder.build([d1, d4], export)
    got = {i: t for i, t, _old in desc}
    assert got[GLOBAL[0]] == "Stand tall and march on the spot."
    assert GLOBAL[1] not in got and GLOBAL[2] not in got and GLOBAL[3] not in got
    assert TEST_CLINIC_ID not in got
    assert got[new_id] == "From D4 for a new row."
    assert got[same_prod] == "From D1."  # D1-D3 wins
    assert len(rejected) == 2 and report["skipped EDIT-SUGGEST"] == 1
    assert any(u[1] == "ZZZ-ZZZ-00000-v1" for u in unknown)
    assert conflicts and conflicts[0][1].startswith("kept D1-D3")
    assert title_fix == (builder.LATERAL_FLEXION_ID, "Neck side-bend isometric (right)",
                         "LATERAL FLEXION  ISOMETRIC  – Right Side")
    old = {i: o for i, _t, o in desc}
    assert old[builder.LATERAL_FLEXION_ID] == "old text" and old[new_id] is None
