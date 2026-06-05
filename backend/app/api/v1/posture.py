from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.schemas.posture import PostureSessionCreate, PostureSessionRead
from app.schemas.envelope import ResponseEnvelope
from app.services import posture_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/sessions",
    response_model=ResponseEnvelope[dict],
    status_code=status.HTTP_201_CREATED,
    tags=["Posture"]
)
async def create_posture_session(
    request: Request,
    data: PostureSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        clinic_id = request.state.clinic_id
        session = await posture_service.create_posture_session(db, clinic_id, data)
        return ResponseEnvelope(data={"session_id": str(session.id)})
    except Exception as e:
        logger.error(f"Error creating posture session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating posture session"
        )
