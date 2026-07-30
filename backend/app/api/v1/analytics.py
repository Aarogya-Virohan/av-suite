from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from app.core.dependencies import require_admin

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.models.clinic import Clinic
from app.schemas.analytics import AnalyticsOverviewResponse
from app.services.analytics import AnalyticsService

router = APIRouter(dependencies=[Depends(require_admin)])


async def get_analytics_service(
    session: AsyncSession = Depends(get_async_session),
) -> AnalyticsService:
    """Inject AnalyticsService bound to async session."""

    return AnalyticsService(session=session)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    clinic: CurrentClinicDep,
    service: AnalyticsServiceDep,
) -> AnalyticsOverviewResponse:
    """Retrieve clinic-scoped analytics dashboard metrics."""

    return await service.get_overview(clinic.id)
