from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.models.usage_event import UsageEvent

logger = logging.getLogger(__name__)


async def record_usage(
    db: AsyncSession, clinic: Clinic, user_id: UUID | None, product_key: str, event_type: str
) -> None:
    """Best-effort insert isolated with a savepoint; never fail the business action."""
    try:
        organization_id = clinic.organization_id
        clinic_id = clinic.id
        if not organization_id or not clinic_id:
            logger.warning("Skipping usage event without clinic organization context")
            return
        async with db.begin_nested():
            db.add(UsageEvent(
                organization_id=organization_id,
                clinic_id=clinic_id,
                user_id=user_id,
                product_key=product_key,
                event_type=event_type,
            ))
            await db.flush()
    except Exception:
        logger.exception("Unable to record usage event product=%s event=%s", product_key, event_type)
