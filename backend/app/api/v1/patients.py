from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.core.database import get_db
from app.schemas.patient import PatientCreate, PatientRead
from app.schemas.envelope import ResponseEnvelope, MetaPagination
from app.schemas.common import PaginationParams
from app.dependencies.pagination import get_pagination_params
from app.services import patient_service

router = APIRouter()

def check_physio_or_admin(request: Request):
    role = request.state.role
    if role not in ["admin", "physio"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only physios or admins can access patients"
        )

@router.get("", response_model=ResponseEnvelope[List[PatientRead]])
async def list_patients(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    check_physio_or_admin(request)
    
    clinic_id = request.state.clinic_id
    patients, total = await patient_service.get_patients(db, clinic_id, pagination)
    
    meta = MetaPagination(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )
    return ResponseEnvelope(data=patients, meta=meta)

@router.post("", response_model=ResponseEnvelope[PatientRead], status_code=201)
async def create_patient(
    request: Request,
    patient_in: PatientCreate,
    db: AsyncSession = Depends(get_db)
):
    check_physio_or_admin(request)
    
    clinic_id = request.state.clinic_id
    patient = await patient_service.create_patient(db, clinic_id, patient_in)
    return ResponseEnvelope(data=patient)

@router.get("/{id}", response_model=ResponseEnvelope[PatientRead])
async def get_patient(
    request: Request,
    id: str,
    db: AsyncSession = Depends(get_db)
):
    check_physio_or_admin(request)
    
    clinic_id = request.state.clinic_id
    patient = await patient_service.get_patient_by_id(db, clinic_id, id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not in caller's clinic"
        )
    return ResponseEnvelope(data=patient)
