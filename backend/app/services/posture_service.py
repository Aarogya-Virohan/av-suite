import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.posture_session import PostureSession, PostureMeasurement
from app.schemas.posture import PostureSessionCreate

logger = logging.getLogger(__name__)

async def create_posture_session(
    db: AsyncSession,
    clinic_id: str,
    data: PostureSessionCreate
) -> PostureSession:
    try:
        session = PostureSession(
            clinic_id=uuid.UUID(clinic_id),
            patient_id=data.patient_id,
            overall_confidence=data.overall_confidence,
            annotated_front_image=data.annotated_front_image,
            annotated_back_image=data.annotated_back_image,
            annotated_left_image=data.annotated_left_image,
            annotated_right_image=data.annotated_right_image
        )
        db.add(session)
        await db.flush()

        for m in data.measurements:
            measurement = PostureMeasurement(
                session_id=session.id,
                metric_name=m.metric_name,
                value=m.value,
                unit=m.unit,
                severity=m.severity,
                visibility=m.visibility,
                notes=m.notes
            )
            db.add(measurement)

        await db.commit()
        await db.refresh(session)
        return session
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating posture session: {e}")
        raise
