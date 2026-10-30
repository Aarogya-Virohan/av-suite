"""Exercise templates (EL-D-009).

A clinic sees its own templates and AV templates (clinic_id NULL). It can
create, change and delete only its own. Every exercise in a template must be
one the clinic can see (its own or global), checked on each write.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.models.exercise_template import ExerciseTemplate, ExerciseTemplateItem
from app.schemas.exercise_template import TemplateIn


class TemplateError(Exception):
    """A write that cannot be saved; the message is safe to show."""


class GlobalTemplateReadOnly(Exception):
    pass


def _visible(clinic_id: uuid.UUID):
    return or_(ExerciseTemplate.clinic_id == clinic_id, ExerciseTemplate.clinic_id.is_(None))


async def list_templates(db: AsyncSession, clinic_id: uuid.UUID) -> List[ExerciseTemplate]:
    rows = await db.execute(
        select(ExerciseTemplate)
        .where(_visible(clinic_id))
        # The clinic's own first, then AV templates; each by name.
        .order_by(ExerciseTemplate.clinic_id.is_(None), ExerciseTemplate.name)
    )
    return list(rows.scalars().all())


async def get_template(db: AsyncSession, clinic_id: uuid.UUID, template_id: uuid.UUID) -> Optional[ExerciseTemplate]:
    row = await db.execute(
        select(ExerciseTemplate).where(ExerciseTemplate.id == template_id, _visible(clinic_id))
    )
    return row.scalar_one_or_none()


async def _check_exercises(db: AsyncSession, clinic_id: uuid.UUID, data: TemplateIn) -> None:
    ids = {i.exercise_id for i in data.items}
    rows = await db.execute(
        select(Exercise.id).where(
            Exercise.id.in_(ids),
            or_(Exercise.clinic_id == clinic_id, Exercise.clinic_id.is_(None)),
        )
    )
    found = set(rows.scalars().all())
    if found != ids:
        raise TemplateError(f"{len(ids - found)} exercise(s) not found in this clinic's library")


def _items(data: TemplateIn) -> List[ExerciseTemplateItem]:
    return [
        ExerciseTemplateItem(
            exercise_id=i.exercise_id,
            position=pos,
            sets=i.sets,
            reps=i.reps,
            hold=i.hold,
            frequency=i.frequency.strip() or "Daily",
            note=(i.note or "").strip() or None,
        )
        for pos, i in enumerate(data.items)
    ]


async def _reload(db: AsyncSession, template_id: uuid.UUID) -> ExerciseTemplate:
    db.expire_all()
    row = await db.execute(select(ExerciseTemplate).where(ExerciseTemplate.id == template_id))
    return row.scalar_one()


async def create_template(
    db: AsyncSession, clinic_id: uuid.UUID, user_id: Optional[uuid.UUID], data: TemplateIn
) -> ExerciseTemplate:
    await _check_exercises(db, clinic_id, data)
    template = ExerciseTemplate(
        clinic_id=clinic_id, name=data.name, description=data.description, created_by=user_id
    )
    template.items = _items(data)
    db.add(template)
    await db.commit()
    return await _reload(db, template.id)


async def update_template(
    db: AsyncSession, clinic_id: uuid.UUID, template_id: uuid.UUID, data: TemplateIn
) -> Optional[ExerciseTemplate]:
    template = await get_template(db, clinic_id, template_id)
    if not template:
        return None
    if template.clinic_id is None:
        raise GlobalTemplateReadOnly()
    await _check_exercises(db, clinic_id, data)
    template.name = data.name
    template.description = data.description
    template.items.clear()
    await db.flush()
    template.items.extend(_items(data))
    await db.commit()
    return await _reload(db, template.id)


async def delete_template(db: AsyncSession, clinic_id: uuid.UUID, template_id: uuid.UUID) -> bool:
    template = await get_template(db, clinic_id, template_id)
    if not template:
        return False
    if template.clinic_id is None:
        raise GlobalTemplateReadOnly()
    await db.delete(template)
    await db.commit()
    return True
