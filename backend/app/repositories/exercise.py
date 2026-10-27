from __future__ import annotations

import uuid
from typing import Optional, Sequence, Tuple, List

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.repositories.base import BaseRepository
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from app.schemas.common import PaginationParams
from app.services.body_regions import region_rank_sql, sort_key
from app.services.exercise_category_service import set_categories


class ExerciseRepository(BaseRepository[Exercise]):
    """Repository for exercise operations (both global and clinic-scoped)."""

    def __init__(self, session: AsyncSession) -> None:
        """Create an exercise repository bound to the active session."""
        super().__init__(session, Exercise)

    async def list_exercises(
        self,
        clinic_id: str,
        pagination: PaginationParams,
        body_part: Optional[str] = None,
        is_free: Optional[bool] = None,
        search: Optional[str] = None,
        category_conditions: Sequence = (),
    ) -> Tuple[List[Exercise], int]:
        
        query = select(Exercise).where(
            or_(
                Exercise.clinic_id == uuid.UUID(clinic_id),
                Exercise.clinic_id.is_(None)
            )
        )

        if body_part:
            parts = [p.strip() for p in body_part.split(",") if p.strip()]
            if parts:
                conditions = [Exercise.body_part.in_(parts)]
                # GET /exercises/body-parts lists exercises without a body part
                # as "Other", so filtering by "Other" must include them.
                if any(p.lower() == "other" for p in parts):
                    conditions.append(Exercise.body_part.is_(None))
                    conditions.append(func.trim(Exercise.body_part) == "")
                query = query.where(or_(*conditions))
        
        for condition in category_conditions:
            query = query.where(condition)

        if is_free is not None:
            query = query.where(Exercise.is_free == is_free)
        
        if search:
            query = query.where(Exercise.title.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Head to toe, then by title. The id makes the order total, so
        # offset paging never repeats or skips a row between pages.
        query = query.order_by(
            region_rank_sql(Exercise.body_part),
            func.lower(Exercise.body_part),
            func.lower(Exercise.title),
            Exercise.id,
        ).offset(
            (pagination.page - 1) * pagination.page_size
        ).limit(pagination.page_size)
        
        result = await self.session.execute(query)
        exercises = result.scalars().all()
        
        return list(exercises), total

    async def list_body_parts(self, clinic_id: str) -> List[Tuple[str, int]]:
        """Distinct body parts the clinic can see, head to toe, with counts."""
        visible = or_(
            Exercise.clinic_id == uuid.UUID(clinic_id),
            Exercise.clinic_id.is_(None),
        )
        part = func.coalesce(func.nullif(func.trim(Exercise.body_part), ""), "Other")
        query = select(part, func.count()).where(visible).group_by(part)
        rows = (await self.session.execute(query)).all()
        return sorted(((name, count) for name, count in rows), key=lambda r: sort_key(r[0]))

    async def create_exercise(self, clinic_id: str, exercise_in: ExerciseCreate) -> Exercise:
        exercise = Exercise(
            clinic_id=uuid.UUID(clinic_id),
            **exercise_in.model_dump(exclude={"category_ids"})
        )
        self.session.add(exercise)
        if exercise_in.category_ids:
            await self.session.flush()
            await set_categories(self.session, exercise.id, exercise_in.category_ids)
        await self.session.commit()
        await self.session.refresh(exercise)
        return exercise

    async def get_exercise_by_id(self, clinic_id: str, exercise_id: str) -> Optional[Exercise]:
        query = select(Exercise).where(
            Exercise.id == uuid.UUID(exercise_id),
            or_(
                Exercise.clinic_id == uuid.UUID(clinic_id),
                Exercise.clinic_id.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def update_exercise(self, db_obj: Exercise, exercise_in: ExerciseUpdate) -> Exercise:
        update_data = exercise_in.model_dump(exclude_unset=True, exclude={"category_ids"})
        updated = await self.update(db_obj, update_data)
        if exercise_in.category_ids is not None:
            await set_categories(self.session, updated.id, exercise_in.category_ids)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def delete_exercise(self, db_obj: Exercise) -> None:
        await self.delete(db_obj)
        await self.session.commit()
