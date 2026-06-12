"""
Module: exercise_service.py
Purpose: Exercise database operations aur business logic
Yeh module exercise CRUD operations handle karta hai (create, read, list).
Clinic-specific aur global exercises ko query aur manage karta hai.

Key Components:
- get_exercises: Clinic ke exercises with advanced filtering aur pagination
- create_exercise: New exercise create karna
- get_exercise_by_id: Single exercise by ID fetch karna

Features:
- Multi-tenant support: Clinic-specific aur global exercises
- Advanced filtering: Body part, free/paid, search
- Pagination support: Large exercise libraries handle karne ke liye
- Global exercises: Shared exercises across clinics (clinic_id = NULL)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate
from app.schemas.common import PaginationParams
from typing import Optional, List, Tuple
import uuid
import logging

logger = logging.getLogger(__name__)


async def get_exercises(
    db: AsyncSession,
    clinic_id: str,
    pagination: PaginationParams,
    body_part: Optional[str] = None,
    is_free: Optional[bool] = None,
    search: Optional[str] = None
) -> Tuple[List[Exercise], int]:
    """
    Function ka purpose: Clinic aur global exercises ko list karna advanced filters ke saath
    Yeh function exercises ko retrieve karta hai with filtering aur pagination.
    Global exercises (clinic_id = NULL) sab clinics ko visible hote hain.
    
    Input:
    - db (AsyncSession): Database session
    - clinic_id (str): Clinic UUID (filtering ke liye)
    - pagination (PaginationParams): Page number aur page size
    - body_part (Optional[str]): Filter by body part (e.g., "Shoulder")
    - is_free (Optional[bool]): Filter by free/paid status
    - search (Optional[str]): Search in exercise title (case-insensitive)
    
    Output: Tuple[List[Exercise], int]
    - List[Exercise]: Current page ke exercises
    - int: Total exercises count (pagination metadata)
    
    Error:
    - SQLAlchemy exceptions (database issues)
    - Invalid UUID format to ValueError
    
    Business Logic:
    1. Clinic aur global exercises include karte hain (OR condition)
    2. Optional filters apply karte hain (body_part, is_free, search)
    3. Total count calculate karte hain
    4. Pagination apply karte hain
    5. Results return karte hain
    
    Filtering Logic:
    - Clinic exercises: clinic_id == specified_clinic
    - Global exercises: clinic_id IS NULL (shared across all clinics)
    - OR condition: Both types combined results
    - Body part filter: Case-sensitive exact match
    - Free filter: Boolean comparison
    - Search: ILIKE for case-insensitive substring search
    
    Database Query Optimization:
    - Multiple conditions combined efficiently
    - Subquery use karte hain counting ke liye
    - Index usage: clinic_id, is_free, body_part par
    
    Usage:
    pagination = PaginationParams(page=1, page_size=10)
    exercises, total = await get_exercises(
        db, clinic_id, pagination,
        body_part="Shoulder",
        is_free=True,
        search="rotation"
    )
    return {
        "data": exercises,
        "total": total,
        "filters_applied": {
            "body_part": body_part,
            "is_free": is_free,
            "search": search
        }
    }
    """
    
    try:
        logger.debug(f"Fetching exercises for clinic {clinic_id}")
        
        # Base query: Clinic-specific aur global exercises
        # OR condition: clinic_id matches OR clinic_id is NULL (global)
        # Yeh multi-tenant + global exercises support provide karta hai
        query = select(Exercise).where(
            or_(
                Exercise.clinic_id == uuid.UUID(clinic_id),  # Clinic-specific
                Exercise.clinic_id.is_(None)  # Global exercises
            )
        )

        # Body part filter - optional
        # Supports comma-separated body parts for multi-select (e.g. "Shoulder,Knee")
        if body_part:
            if "," in body_part:
                parts = [p.strip() for p in body_part.split(",") if p.strip()]
                query = query.where(Exercise.body_part.in_(parts))
            else:
                query = query.where(Exercise.body_part == body_part)
            logger.debug(f"Filter applied: body_part = {body_part}")
        
        # Free/paid filter - optional
        # Boolean comparison - subscription/pricing logic ke liye
        # Note: is_free parameter None ho sakta hai (no filter)
        if is_free is not None:
            query = query.where(Exercise.is_free == is_free)
            logger.debug(f"Filter applied: is_free = {is_free}")
        
        # Search filter - optional
        # ILIKE: Case-insensitive substring search
        # Substring matching: Exercise title mein search term
        if search:
            query = query.where(Exercise.title.ilike(f"%{search}%"))
            logger.debug(f"Filter applied: search = {search}")

        # Total count calculate karte hain pagination metadata ke liye
        # Subquery use karte hain counting ke liye (all filters included)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        logger.debug(f"Total exercises matching filters: {total}")

        # Pagination apply karte hain
        # offset: Skip karte hain (page-1) * page_size records
        # limit: Take karte hain page_size records
        query = query.offset(
            (pagination.page - 1) * pagination.page_size
        ).limit(pagination.page_size)
        
        # Query execute karte hain
        result = await db.execute(query)
        exercises = result.scalars().all()
        
        logger.info(f"Retrieved {len(exercises)} exercises, total: {total}")
        return list(exercises), total
        
    except ValueError as e:
        logger.error(f"Invalid clinic_id format: {clinic_id}")
        raise
    except Exception as e:
        logger.error(f"Get exercises error: {str(e)}")
        raise


async def create_exercise(
    db: AsyncSession,
    clinic_id: str,
    exercise_in: ExerciseCreate
) -> Exercise:
    """
    Function ka purpose: New exercise create karna clinic mein
    Yeh function exercise registration handle karta hai.
    
    Input:
    - db (AsyncSession): Database session
    - clinic_id (str): Clinic UUID (exercise associate karne ke liye)
    - exercise_in (ExerciseCreate): Exercise data from request
      - title: Required
      - description: Optional
      - body_part: Optional
      - is_free: Optional (default False)
      - video_url: Optional
    
    Output: Exercise
    - Created exercise database record
    
    Error:
    - SQLAlchemy exceptions (constraint violations)
    - Invalid UUID format to ValueError
    - Validation errors from schema
    
    Business Logic:
    1. Exercise object create karte hain clinic_id ke saath
    2. Database mein insert karte hain
    3. Created record return karte hain
    
    Database Operations:
    - add(): Exercise ko session mein add karte hain
    - commit(): Database mein save karte hain
    - refresh(): Auto-generated fields load karte hain (id, timestamps)
    
    Security:
    - Clinic ID: Exercise always clinic se associated
    - Schema validation: Pydantic schema se validation
    
    Usage:
    exercise_data = ExerciseCreate(
        title="Shoulder Rotation",
        description="Rotate shoulder in circular motion",
        body_part="Shoulder",
        is_free=True,
        video_url="https://cdn.example.com/exercise.mp4"
    )
    new_exercise = await create_exercise(db, clinic_id, exercise_data)
    return new_exercise
    """
    
    try:
        logger.info(f"Creating exercise in clinic {clinic_id}")
        
        # Exercise object create karte hain
        # model_dump(): Pydantic schema se dict extract karte hain
        exercise = Exercise(
            clinic_id=uuid.UUID(clinic_id),
            **exercise_in.model_dump()  # Unpacking schema fields
        )
        
        # Database mein add karte hain
        db.add(exercise)
        
        # Transaction commit karte hain
        await db.commit()
        
        # Auto-generated fields load karte hain (id, created_at, updated_at)
        await db.refresh(exercise)
        
        logger.info(f"Exercise created successfully: {exercise.id}")
        return exercise
        
    except ValueError as e:
        logger.error(f"Invalid clinic_id format: {clinic_id}")
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Create exercise error: {str(e)}")
        await db.rollback()
        raise


async def get_exercise_by_id(
    db: AsyncSession,
    clinic_id: str,
    exercise_id: str
) -> Optional[Exercise]:
    """
    Function ka purpose: Specific exercise ko fetch karna clinic context mein
    Yeh function exercise details retrieve karta hai ID se.
    Clinic-level security + global exercises: Clinic ke exercise ya global exercise.
    
    Input:
    - db (AsyncSession): Database session
    - clinic_id (str): Clinic UUID (security ke liye)
    - exercise_id (str): Exercise UUID
    
    Output: Optional[Exercise]
    - Exercise object agar found, None otherwise
    
    Error:
    - SQLAlchemy exceptions (database issues)
    - Invalid UUID format to ValueError
    
    Business Logic:
    1. Exercise ID from database search karte hain
    2. Clinic verification: Clinic-specific ya global exercise
    3. Exercise record fetch karte hain
    4. NULL if not found
    
    Security:
    - Clinic isolation: Sirf clinic ke exercises accessible
    - Global exercises: Sab clinics ko accessible
    - OR condition: clinic_id matches OR clinic_id is NULL
    
    Database Query:
    - Multiple conditions: exercise_id AND (clinic_id OR NULL)
    - Single result: first() use karte hain
    - Optional return: Not found ke liye None
    
    Usage:
    exercise = await get_exercise_by_id(db, clinic_id, exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise
    """
    
    try:
        logger.debug(f"Fetching exercise {exercise_id} for clinic {clinic_id}")
        
        # Query construct karte hain multiple conditions ke saath
        # Exercise ID aur (Clinic ID OR NULL) check karte hain
        query = select(Exercise).where(
            Exercise.id == uuid.UUID(exercise_id),
            or_(
                Exercise.clinic_id == uuid.UUID(clinic_id),  # Clinic-specific
                Exercise.clinic_id.is_(None)  # Global exercises
            )
        )
        
        # Query execute karte hain
        result = await db.execute(query)
        
        # first() use karte hain single result ke liye
        # None return hota hai if not found
        exercise = result.scalars().first()
        
        if exercise:
            logger.info(f"Exercise found: {exercise_id}")
        else:
            logger.warning(f"Exercise not found: {exercise_id}")
            
        return exercise
        
    except ValueError as e:
        logger.error(f"Invalid UUID format - clinic_id: {clinic_id}, exercise_id: {exercise_id}")
        raise
    except Exception as e:
        logger.error(f"Get exercise by id error: {str(e)}")
        raise

