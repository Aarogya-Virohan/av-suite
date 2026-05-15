from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.patient import Patient
from app.schemas.patient import PatientCreate
from app.schemas.common import PaginationParams
from typing import Optional, List, Tuple
import uuid

async def get_patients(
    db: AsyncSession,
    clinic_id: str,
    pagination: PaginationParams
) -> Tuple[List[Patient], int]:
    
    query = select(Patient).where(Patient.clinic_id == uuid.UUID(clinic_id))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size)
    
    result = await db.execute(query)
    patients = result.scalars().all()

    return list(patients), total

async def create_patient(
    db: AsyncSession,
    clinic_id: str,
    patient_in: PatientCreate
) -> Patient:
    
    patient = Patient(
        clinic_id=uuid.UUID(clinic_id),
        **patient_in.model_dump()
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient

async def get_patient_by_id(
    db: AsyncSession,
    clinic_id: str,
    patient_id: str
) -> Optional[Patient]:
    
    query = select(Patient).where(
        Patient.id == uuid.UUID(patient_id),
        Patient.clinic_id == uuid.UUID(clinic_id)
    )
    result = await db.execute(query)
    return result.scalars().first()
