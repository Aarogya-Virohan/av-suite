from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate
from app.schemas.common import PaginationParams
from typing import Optional, List, Tuple
import uuid

async def get_exercises(
    db: AsyncSession,
    clinic_id: str,
    pagination: PaginationParams,
    body_part: Optional[str] = None,
    is_free: Optional[bool] = None,
    search: Optional[str] = None
) -> Tuple[List[Exercise], int]:
    
    # Filter by clinic_id OR global exercises (clinic_id == None)
    query = select(Exercise).where(
        or_(
            Exercise.clinic_id == uuid.UUID(clinic_id),
            Exercise.clinic_id.is_(None)
        )
    )

    if body_part:
        query = query.where(Exercise.body_part == body_part)
    
    if is_free is not None:
        query = query.where(Exercise.is_free == is_free)
    
    if search:
        query = query.where(Exercise.title.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size)
    
    result = await db.execute(query)
    exercises = result.scalars().all()

    return list(exercises), total

async def create_exercise(
    db: AsyncSession,
    clinic_id: str,
    exercise_in: ExerciseCreate
) -> Exercise:
    
    exercise = Exercise(
        clinic_id=uuid.UUID(clinic_id),
        **exercise_in.model_dump()
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    return exercise

async def get_exercise_by_id(
    db: AsyncSession,
    clinic_id: str,
    exercise_id: str
) -> Optional[Exercise]:
    
    query = select(Exercise).where(
        Exercise.id == uuid.UUID(exercise_id),
        or_(
            Exercise.clinic_id == uuid.UUID(clinic_id),
            Exercise.clinic_id.is_(None)
        )
    )
    result = await db.execute(query)
    return result.scalars().first()
