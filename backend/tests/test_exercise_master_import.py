"""Checks on the frozen exercise list of migration f4a9c2e7b1d3 (EL-D-007).

The import must never add a second copy of an exercise: not inside the list,
not against the original global exercises, and not against the twelve sheet
exercises added by SQL on 27 Oct. Each rule below is one parametrized case.
"""

import hashlib
import importlib.util
import re
import uuid
from pathlib import Path

import pytest

from app.services.body_regions import UNKNOWN_RANK, region_rank

_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "f4a9c2e7b1d3_import_av_exercise_master_list.py"
_spec = importlib.util.spec_from_file_location("master_import", _PATH)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

SEED_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "22021104ec07_seed_exercises.py"

# Sheet exercises already in production (5 renamed originals and 12 added by SQL, 27 Oct).
IN_LIBRARY = {
    "0035", "0109", "0096", "0048", "0218", "0059", "0064", "0077", "0171",
    "0187", "0227", "0229", "0254", "0258", "0318", "0503", "0293",
}
PROD_TITLES = {
    "Upper trapezius stretch", "Biceps curl", "Wall push-up", "Cat-camel", "Glute bridge",
    "Shoulder abduction active ROM", "Dowel shoulder flexion", "Band external rotation", "Bird dog",
    "Prone press-up", "Clamshell", "Side-lying hip abduction", "Straight leg raise", "Mini squat",
    "Sit-to-stand", "Hamstring stretch standing", "Double-leg heel raise",
}
REGION_PARTS = {"Jaw", "Neck", "Shoulder", "Upper Back", "Elbow", "Hand", "Thoracic", "Lower Back",
                "Pelvis", "Hip", "Knee", "Ankle & Foot"}


def norm(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip()).lower()


def loose(title: str) -> str:
    """Same words in any order, singular, punctuation ignored."""
    words = re.sub(r"[^a-z0-9 ]+", " ", title.lower()).split()
    return " ".join(sorted(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words))


def seed_titles() -> list[str]:
    return re.findall(r"'title': '([^']*)'", SEED_PATH.read_text())


SHEETS = [s for s, _t, _b in mig.EXERCISES]
TITLES = [t for _s, t, _b in mig.EXERCISES] + [new for _s, _id, new, _old in mig.RENAMES]


def check_sheet_numbers_unique():
    all_numbers = SHEETS + [s for s, *_ in mig.RENAMES]
    assert len(all_numbers) == len(set(all_numbers))


def check_sheet_number_format():
    assert all(re.fullmatch(r"\d{4}", s) and 1 <= int(s) <= 1500 for s in SHEETS)


def check_ids_unique_and_not_seed():
    ids = {uuid.UUID(hashlib.md5(f"AV-EX-{s}".encode()).hexdigest()) for s in SHEETS}
    assert len(ids) == len(SHEETS)
    seed_ids = {uuid.UUID(i) for i in re.findall(r"'id': '([0-9a-f-]{36})'", SEED_PATH.read_text())}
    assert len(seed_ids) == 13 and not ids & seed_ids


def check_titles_unique_normalized():
    keys = [norm(t) for t in TITLES]
    assert len(keys) == len(set(keys))


def check_titles_unique_loose():
    keys = [loose(t) for t in TITLES]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, dupes


def check_no_clash_with_production():
    taken = {loose(t) for t in PROD_TITLES} | {loose(t) for t in seed_titles()}
    renamed_old = {loose(old) for *_x, old in mig.RENAMES}
    clash = [t for t in (t for _s, t, _b in mig.EXERCISES) if loose(t) in taken - renamed_old]
    assert not clash, clash


def check_already_in_library_not_inserted():
    assert not IN_LIBRARY & set(SHEETS)


def check_renames_point_at_seed_rows():
    seed = dict(re.findall(r"'id': '([0-9a-f-]{36})', 'title': '([^']*)'", SEED_PATH.read_text()))
    for _s, ex_id, new, old in mig.RENAMES:
        assert seed.get(ex_id) == old and new and new != old


def check_column_lengths():
    assert all(0 < len(t) <= 255 and t == t.strip() and "  " not in t for t in TITLES)
    assert all(0 < len(b) <= 100 for *_x, b in mig.EXERCISES)


def check_body_parts_order():
    for *_x, b in mig.EXERCISES:
        if b in REGION_PARTS:
            assert region_rank(b) < UNKNOWN_RANK, b


def check_count():
    assert len(mig.EXERCISES) == 1442 and len(mig.RENAMES) == 7


@pytest.mark.parametrize(
    "check",
    [
        check_sheet_numbers_unique,
        check_sheet_number_format,
        check_ids_unique_and_not_seed,
        check_titles_unique_normalized,
        check_titles_unique_loose,
        check_no_clash_with_production,
        check_already_in_library_not_inserted,
        check_renames_point_at_seed_rows,
        check_column_lengths,
        check_body_parts_order,
        check_count,
    ],
    ids=lambda f: f.__name__.removeprefix("check_"),
)
def test_master_import_list(check):
    check()
