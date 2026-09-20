from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_async_session,
    get_current_clinic,
    get_current_user,
    require_capability,
)
from app.enums.permission import CapabilityScope
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.analytics import AnalyticsOverviewResponse, TherapistPerformanceResponse
from app.services.analytics import AnalyticsService
from app.schemas.envelope import ResponseEnvelope

router = APIRouter()


async def get_analytics_service(
    session: AsyncSession = Depends(get_async_session),
) -> AnalyticsService:
    """Inject AnalyticsService bound to async session."""

    return AnalyticsService(session=session)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("/analytics/overview", response_model=ResponseEnvelope[AnalyticsOverviewResponse])
async def get_analytics_overview(
    clinic: CurrentClinicDep,
    service: AnalyticsServiceDep,
    _scope: CapabilityScope = Depends(require_capability("analytics.clinic_financials")),
) -> ResponseEnvelope[AnalyticsOverviewResponse]:
    """
    Retrieve clinic-wide analytics metrics.
    Requires analytics.clinic_financials capability.
    """

    result = await service.get_overview(clinic.id)
    return ResponseEnvelope(data=result)


@router.get("/analytics/my-performance", response_model=ResponseEnvelope[TherapistPerformanceResponse])
async def get_my_performance(
    clinic: CurrentClinicDep,
    current_user: CurrentUserDep,
    service: AnalyticsServiceDep,
    _scope: CapabilityScope = Depends(require_capability("analytics.my_performance")),
) -> ResponseEnvelope[TherapistPerformanceResponse]:
    """
    Retrieve therapist-scoped performance metrics.
    Requires analytics.my_performance capability.
    """

    result = await service.get_my_performance(clinic.id, current_user.id)
    return ResponseEnvelope(data=result)
