"""
Exercise categories: read the list with counts, filter exercises by
category, and set the categories of an exercise (EL-D-005).

Filter rule (same as the reference platform's filter panel): values picked
inside one group widen the result (Knee OR Hips), values from different
groups narrow it (Knee AND Standing).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Iterable, Sequence

from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.exercise import Exercise
from app.models.exercise_category import ExerciseCategory, exercise_category_links
from app.services.exercise_categories import GROUP_KEYS, GROUP_LABELS, GROUP_RANK


class CategoryError(ValueError):
    """Unknown or inactive category id."""


def parse_ids(raw: Iterable[str] | None) -> list[uuid.UUID]:
    """Category ids from query values; commas are accepted too."""
    ids: list[uuid.UUID] = []
    for value in raw or []:
        for part in str(value).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(uuid.UUID(part))
            except ValueError:
                raise CategoryError(f"Invalid category id: {part}")
    return list(dict.fromkeys(ids))


async def _active(db: AsyncSession, ids: Sequence[uuid.UUID]) -> list[ExerciseCategory]:
    if not ids:
        return []
    rows = await db.execute(
        select(ExerciseCategory).where(
            ExerciseCategory.id.in_(ids), ExerciseCategory.is_active.is_(True)
        )
    )
    found = list(rows.scalars().all())
    missing = set(ids) - {c.id for c in found}
    if missing:
        raise CategoryError(
            "Unknown category id: " + ", ".join(sorted(str(m) for m in missing))
        )
    return found


async def check_ids(db: AsyncSession, ids: Sequence[uuid.UUID] | None) -> list[uuid.UUID]:
    """The ids, de-duplicated, after checking each is an active category."""
    unique = list(dict.fromkeys(ids or []))
    await _active(db, unique)
    return unique


async def set_categories(
    db: AsyncSession, exercise_id: uuid.UUID, ids: Sequence[uuid.UUID]
) -> None:
    """Replace the exercise's categories. Does not commit."""
    await db.execute(
        delete(exercise_category_links).where(
            exercise_category_links.c.exercise_id == exercise_id
        )
    )
    if ids:
        await db.execute(
            insert(exercise_category_links),
            [{"exercise_id": exercise_id, "category_id": cid} for cid in ids],
        )


async def filter_conditions(
    db: AsyncSession, ids: Sequence[uuid.UUID]
) -> list[ColumnElement[bool]]:
    """WHERE conditions on Exercise.id for the picked categories."""
    by_group: dict[str, list[uuid.UUID]] = defaultdict(list)
    for category in await _active(db, ids):
        by_group[category.group_key].append(category.id)
    conditions: list[ColumnElement[bool]] = []
    for group_ids in by_group.values():
        conditions.append(
            Exercise.id.in_(
                select(exercise_category_links.c.exercise_id).where(
                    exercise_category_links.c.category_id.in_(group_ids)
                )
            )
        )
    return conditions


async def categories_for(
    db: AsyncSession, exercise_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[ExerciseCategory]]:
    """Active categories of each exercise, in panel order."""
    if not exercise_ids:
        return {}
    rows = await db.execute(
        select(exercise_category_links.c.exercise_id, ExerciseCategory)
        .join(ExerciseCategory, ExerciseCategory.id == exercise_category_links.c.category_id)
        .where(
            exercise_category_links.c.exercise_id.in_(exercise_ids),
            ExerciseCategory.is_active.is_(True),
        )
    )
    out: dict[uuid.UUID, list[ExerciseCategory]] = defaultdict(list)
    for exercise_id, category in rows.all():
        out[exercise_id].append(category)
    for items in out.values():
        items.sort(key=lambda c: (GROUP_RANK.get(c.group_key, len(GROUP_KEYS)), c.sort_order))
    return dict(out)


async def list_with_counts(db: AsyncSession, clinic_id: str) -> list[dict]:
    """Every group with its active values and how many exercises the clinic
    can see (its own and global) carry each value. Counts do not depend on
    the filters picked."""
    visible = select(Exercise.id).where(
        or_(Exercise.clinic_id == uuid.UUID(str(clinic_id)), Exercise.clinic_id.is_(None))
    )
    counts_q = (
        select(exercise_category_links.c.category_id, func.count())
        .where(exercise_category_links.c.exercise_id.in_(visible))
        .group_by(exercise_category_links.c.category_id)
    )
    counts = dict((await db.execute(counts_q)).all())
    rows = await db.execute(
        select(ExerciseCategory).where(ExerciseCategory.is_active.is_(True))
    )
    by_group: dict[str, list[ExerciseCategory]] = defaultdict(list)
    for category in rows.scalars().all():
        by_group[category.group_key].append(category)
    groups = []
    for key in sorted(by_group, key=lambda k: GROUP_RANK.get(k, len(GROUP_KEYS))):
        values = sorted(by_group[key], key=lambda c: c.sort_order)
        groups.append(
            {
                "key": key,
                "label": GROUP_LABELS.get(key, key),
                "values": [
                    {"id": c.id, "name": c.name, "count": counts.get(c.id, 0)}
                    for c in values
                ],
            }
        )
    return groups
