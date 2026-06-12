from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import logging

from app.core.database import get_db
from app.schemas.posture import PostureSessionCreate, PostureSessionRead
from app.schemas.envelope import ResponseEnvelope
from app.services import posture_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/sessions",
    response_model=ResponseEnvelope[PostureSessionRead],
    status_code=201,
    tags=["Posture"]
)
async def create_session(
    request: Request,
    session_in: PostureSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new posture session and associated measurements.
    Strictly scoped to the clinician's clinic_id.
    """
    logger.info(f"Received create posture session request for patient {session_in.patient_id}")
    try:
        clinic_id = request.state.clinic_id
        session = await posture_service.create_posture_session(
            db, uuid.UUID(clinic_id), session_in
        )
        return ResponseEnvelope(data=session)
    except Exception as e:
        logger.error(f"Error creating posture session: {str(e)}")
        raise

@router.get(
    "/sessions",
    response_model=ResponseEnvelope[List[PostureSessionRead]],
    tags=["Posture"]
)
async def list_sessions(
    request: Request,
    patient_id: Optional[uuid.UUID] = Query(None, description="Filter by patient ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves all posture sessions for the clinic.
    """
    logger.info(f"Listing posture sessions. Filter by patient: {patient_id}")
    try:
        clinic_id = request.state.clinic_id
        sessions = await posture_service.get_posture_sessions(
            db, uuid.UUID(clinic_id), patient_id
        )
        return ResponseEnvelope(data=sessions)
    except Exception as e:
        logger.error(f"Error listing posture sessions: {str(e)}")
        raise

@router.get(
    "/sessions/{id}",
    response_model=ResponseEnvelope[PostureSessionRead],
    tags=["Posture"]
)
async def get_session(
    request: Request,
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a specific posture session by ID.
    """
    logger.info(f"Fetching posture session: {id}")
    try:
        clinic_id = request.state.clinic_id
        session = await posture_service.get_posture_session_by_id(
            db, uuid.UUID(clinic_id), id
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Posture session not found or not in user's clinic"
            )
        return ResponseEnvelope(data=session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting posture session {id}: {str(e)}")
        raise
