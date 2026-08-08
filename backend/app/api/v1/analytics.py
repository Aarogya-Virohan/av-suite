from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from app.core.dependencies import require_admin, require_permission

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.models.clinic import Clinic
from app.schemas.analytics import AnalyticsOverviewResponse
from app.services.analytics import AnalyticsService
from app.schemas.envelope import ResponseEnvelope

from app.enums.user import UserRole

router = APIRouter(dependencies=[Depends(require_permission("analytics"))])


async def get_analytics_service(
    session: AsyncSession = Depends(get_async_session),
) -> AnalyticsService:
    """Inject AnalyticsService bound to async session."""

    return AnalyticsService(session=session)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


@router.get("/analytics/overview", response_model=ResponseEnvelope[AnalyticsOverviewResponse])
async def get_analytics_overview(
    clinic: CurrentClinicDep,
    service: AnalyticsServiceDep,
) -> ResponseEnvelope[AnalyticsOverviewResponse]:
    """Retrieve clinic-scoped analytics dashboard metrics."""

    result = await service.get_overview(clinic.id)
    return ResponseEnvelope(data=result)
