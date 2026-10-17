from __future__ import annotations

import uuid
from typing import Optional, Tuple, List

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.repositories.base import BaseRepository
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from app.schemas.common import PaginationParams


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
        search: Optional[str] = None
    ) -> Tuple[List[Exercise], int]:
        
        query = select(Exercise).where(
            or_(
                Exercise.clinic_id == uuid.UUID(clinic_id),
                Exercise.clinic_id.is_(None)
            )
        )

        if body_part:
            if "," in body_part:
                parts = [p.strip() for p in body_part.split(",") if p.strip()]
                query = query.where(Exercise.body_part.in_(parts))
            else:
                query = query.where(Exercise.body_part == body_part)
        
        if is_free is not None:
            query = query.where(Exercise.is_free == is_free)
        
        if search:
            query = query.where(Exercise.title.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.offset(
            (pagination.page - 1) * pagination.page_size
        ).limit(pagination.page_size)
        
        result = await self.session.execute(query)
        exercises = result.scalars().all()
        
        return list(exercises), total

    async def create_exercise(self, clinic_id: str, exercise_in: ExerciseCreate) -> Exercise:
        exercise = Exercise(
            clinic_id=uuid.UUID(clinic_id),
            **exercise_in.model_dump()
        )
        self.session.add(exercise)
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
        update_data = exercise_in.model_dump(exclude_unset=True)
        updated = await self.update(db_obj, update_data)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def delete_exercise(self, db_obj: Exercise) -> None:
        await self.delete(db_obj)
        await self.session.commit()
