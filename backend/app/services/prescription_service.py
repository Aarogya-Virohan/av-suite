import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from typing import List, Tuple, Optional

from app.models.prescription import Prescription, PrescriptionItem
from app.models.exercise import Exercise
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate
from app.schemas.common import PaginationParams

logger = logging.getLogger(__name__)

async def create_prescription(
    db: AsyncSession,
    clinic_id: str,
    physio_id: str,
    data: PrescriptionCreate
) -> Prescription:
    try:
        # Create main prescription record
        prescription = Prescription(
            clinic_id=uuid.UUID(clinic_id),
            patient_id=data.patient_id,
            physio_id=uuid.UUID(physio_id),
            physio_notes=data.physio_notes,
            status=data.status
        )
        db.add(prescription)
        await db.flush()  # Flush to get prescription ID

        # Create items
        for item_data in data.items:
            item = PrescriptionItem(
                prescription_id=prescription.id,
                exercise_id=item_data.exercise_id,
                sets=item_data.sets,
                reps=item_data.reps,
                hold=item_data.hold,
                frequency=item_data.frequency,
                hold_angle=item_data.hold_angle,
                note=item_data.note
            )
            db.add(item)
            
        await db.commit()
        
        # Refresh and load relations
        return await get_prescription_by_id(db, clinic_id, str(prescription.id))
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating prescription: {e}")
        raise


async def get_prescription_by_id(
    db: AsyncSession,
    clinic_id: str,
    prescription_id: str
) -> Optional[Prescription]:
    try:
        query = (
            select(Prescription)
            .options(
                selectinload(Prescription.items).selectinload(PrescriptionItem.exercise)
            )
            .where(
                Prescription.id == uuid.UUID(prescription_id),
                Prescription.clinic_id == uuid.UUID(clinic_id)
            )
        )
        result = await db.execute(query)
        return result.scalars().first()
    except ValueError:
        return None


async def get_prescriptions(
    db: AsyncSession,
    clinic_id: str,
    pagination: PaginationParams,
    patient_id: Optional[str] = None
) -> Tuple[List[Prescription], int]:
    try:
        query = select(Prescription).where(Prescription.clinic_id == uuid.UUID(clinic_id))
        
        if patient_id:
            query = query.where(Prescription.patient_id == uuid.UUID(patient_id))
            
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0
        
        query = (
            query
            .options(
                selectinload(Prescription.items).selectinload(PrescriptionItem.exercise)
            )
            .offset((pagination.page - 1) * pagination.page_size)
            .limit(pagination.page_size)
            .order_by(Prescription.created_at.desc())
        )
        
        result = await db.execute(query)
        return list(result.scalars().all()), total
    except ValueError:
        return [], 0


async def update_prescription(
    db: AsyncSession,
    clinic_id: str,
    prescription_id: str,
    data: PrescriptionUpdate
) -> Optional[Prescription]:
    try:
        prescription = await get_prescription_by_id(db, clinic_id, prescription_id)
        if not prescription:
            return None
            
        if data.physio_notes is not None:
            prescription.physio_notes = data.physio_notes
        if data.status is not None:
            prescription.status = data.status
            
        await db.commit()
        await db.refresh(prescription)
        return prescription
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating prescription: {e}")
        raise
