"""
Head-to-toe order of exercise body parts (founders' feedback, 23 Oct 2026:
"change sequence, head to toe as per joints").

One list, used by the exercise list query (ORDER BY) and by
GET /exercises/body-parts, so every client shows the same order.

Matching is case-insensitive on the stored `body_part` text. Several
spellings map to one position (e.g. "Neck" and "Cervical"). A body part
that is not in the list sorts after all known ones, alphabetically, and
"Other" always comes last. The order follows the joints from the head
down the arm, then down the trunk and the leg; founders can reorder it.
"""

from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement

# Each entry: the spellings that share one position.
HEAD_TO_TOE: tuple[tuple[str, ...], ...] = (
    ("head",),
    ("face",),
    ("jaw", "tmj"),
    ("neck", "cervical", "cervical spine"),
    ("shoulder", "shoulders"),
    ("arms", "arm", "upper arm"),
    ("elbow", "elbows"),
    ("forearm", "forearms"),
    ("wrist", "wrists"),
    ("hand", "hands", "fingers", "wrist & hand", "wrist and hand"),
    ("upper back", "thoracic", "thoracic spine"),
    ("chest",),
    ("spine",),
    ("core", "abdomen", "abs", "abdominals"),
    ("lower back", "lumbar", "lumbar spine"),
    ("pelvis", "pelvic floor"),
    ("hip", "hips"),
    ("glutes", "gluteal", "buttocks"),
    ("thigh", "thighs"),
    ("hamstrings", "hamstring"),
    ("quadriceps", "quads"),
    ("knee", "knees"),
    ("legs", "leg", "lower leg"),
    ("calf", "calves"),
    ("ankle", "ankles"),
    ("foot", "feet", "toes", "ankle & foot", "ankle and foot"),
    ("full body", "whole body"),
)

OTHER = "other"

_RANK: dict[str, int] = {
    name: index for index, names in enumerate(HEAD_TO_TOE) for name in names
}
UNKNOWN_RANK = len(HEAD_TO_TOE)
OTHER_RANK = UNKNOWN_RANK + 1


def region_rank(body_part: str | None) -> int:
    key = (body_part or "").strip().lower()
    if not key or key == OTHER:
        return OTHER_RANK
    return _RANK.get(key, UNKNOWN_RANK)


def sort_key(body_part: str | None) -> tuple[int, str]:
    return (region_rank(body_part), (body_part or "").strip().lower())


def region_rank_sql(column) -> ColumnElement[int]:
    """SQL expression with the same rank as region_rank(), for ORDER BY."""
    key = func.lower(func.trim(func.coalesce(column, "")))
    whens = [(key == name, rank) for name, rank in _RANK.items()]
    whens.append((key.in_(["", OTHER]), OTHER_RANK))
    return case(*whens, else_=UNKNOWN_RANK)
