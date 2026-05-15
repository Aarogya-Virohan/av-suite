from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid

from app.core.database import get_db
from app.schemas.exercise import ExerciseCreate, ExerciseRead
from app.schemas.envelope import ResponseEnvelope, MetaPagination
from app.schemas.common import PaginationParams
from app.dependencies.pagination import get_pagination_params
from app.services import exercise_service

router = APIRouter()

@router.get("", response_model=ResponseEnvelope[List[ExerciseRead]])
async def list_exercises(
    request: Request,
    body_part: Optional[str] = None,
    is_free: Optional[bool] = None,
    search: Optional[str] = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    clinic_id = request.state.clinic_id
    exercises, total = await exercise_service.get_exercises(
        db, clinic_id, pagination, body_part, is_free, search
    )
    
    meta = MetaPagination(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )
    return ResponseEnvelope(data=exercises, meta=meta)

@router.post("", response_model=ResponseEnvelope[ExerciseRead], status_code=201)
async def create_exercise(
    request: Request,
    exercise_in: ExerciseCreate,
    db: AsyncSession = Depends(get_db)
):
    role = request.state.role
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create exercises"
        )
    
    clinic_id = request.state.clinic_id
    exercise = await exercise_service.create_exercise(db, clinic_id, exercise_in)
    return ResponseEnvelope(data=exercise)

@router.get("/{id}", response_model=ResponseEnvelope[ExerciseRead])
async def get_exercise(
    request: Request,
    id: str,
    db: AsyncSession = Depends(get_db)
):
    clinic_id = request.state.clinic_id
    exercise = await exercise_service.get_exercise_by_id(db, clinic_id, id)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found or not in caller's clinic"
        )
    return ResponseEnvelope(data=exercise)
