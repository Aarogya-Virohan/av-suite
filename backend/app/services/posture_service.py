import logging
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.posture_session import PostureSession, PostureMeasurement
from app.schemas.posture import PostureSessionCreate

logger = logging.getLogger(__name__)

async def create_posture_session(
    db: AsyncSession, clinic_id: uuid.UUID, session_in: PostureSessionCreate
) -> PostureSession:
    """
    Creates a new posture session and associated measurements for a clinic.
    """
    try:
        logger.info(f"Creating posture session for patient: {session_in.patient_id} in clinic: {clinic_id}")
        
        db_session = PostureSession(
            clinic_id=clinic_id,
            patient_id=session_in.patient_id,
            overall_confidence=session_in.overall_confidence,
            annotated_front_image=session_in.annotated_front_image,
            annotated_back_image=session_in.annotated_back_image,
            annotated_side_image=session_in.annotated_side_image,
        )
        db.add(db_session)
        await db.flush()  # Generate ID for the session
        
        db_measurements = []
        for m in session_in.measurements:
            db_measurements.append(
                PostureMeasurement(
                    session_id=db_session.id,
                    metric_name=m.metric_name,
                    value=m.value,
                    unit=m.unit,
                    notes=m.notes,
                    severity=m.severity,
                    visibility=m.visibility,
                )
            )
        
        if db_measurements:
            db.add_all(db_measurements)
        
        await db.commit()
        await db.refresh(db_session)
        
        # Load measurements for reading
        result = await db.execute(
            select(PostureSession)
            .where(PostureSession.id == db_session.id)
            .options(selectinload(PostureSession.measurements))
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error creating posture session: {str(e)}")
        await db.rollback()
        raise

async def get_posture_sessions(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: Optional[uuid.UUID] = None
) -> List[PostureSession]:
    """
    Retrieves all posture sessions for a clinic, optionally filtered by patient.
    """
    try:
        logger.info(f"Fetching posture sessions for clinic: {clinic_id}")
        query = select(PostureSession).where(PostureSession.clinic_id == clinic_id)
        if patient_id:
            query = query.where(PostureSession.patient_id == patient_id)
        
        query = query.options(selectinload(PostureSession.measurements)).order_by(PostureSession.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error listing posture sessions: {str(e)}")
        raise

async def get_posture_session_by_id(
    db: AsyncSession, clinic_id: uuid.UUID, session_id: uuid.UUID
) -> Optional[PostureSession]:
    """
    Retrieves a specific posture session by ID with clinic isolated scoping.
    """
    try:
        logger.info(f"Fetching posture session: {session_id} in clinic: {clinic_id}")
        query = (
            select(PostureSession)
            .where(PostureSession.id == session_id, PostureSession.clinic_id == clinic_id)
            .options(selectinload(PostureSession.measurements))
        )
        result = await db.execute(query)
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching posture session {session_id}: {str(e)}")
        raise
