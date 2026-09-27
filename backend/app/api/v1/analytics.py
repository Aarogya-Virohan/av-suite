from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
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
from app.enums.analytics import AnalyticsPeriod, PatientRevenueSort
from app.schemas.analytics import (
    AnalyticsOverviewEnvelope,
    TherapistPerformanceEnvelope,
)
from app.services.analytics import AnalyticsService

router = APIRouter()


async def get_analytics_service(
    session: AsyncSession = Depends(get_async_session),
) -> AnalyticsService:
    """Inject AnalyticsService bound to async session."""

    return AnalyticsService(session=session)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewEnvelope,
)
async def get_analytics_overview(
    clinic: CurrentClinicDep,
    service: AnalyticsServiceDep,
    period: AnalyticsPeriod = Query(
        default=AnalyticsPeriod.MONTH,
        description=(
            "UTC calendar reporting period: today (current UTC day), week "
            "(current Monday-based calendar week), month (current UTC calendar "
            "month), or year (current UTC calendar year). The start is inclusive "
            "and the end is exclusive. Defaults to month."
        ),
    ),
    patient_revenue_sort: PatientRevenueSort = Query(
        default=PatientRevenueSort.COLLECTED_AMOUNT,
        description=(
            "Financial metric used to rank the patient_revenue list: "
            "collected_amount (default) or billed_amount."
        ),
    ),
    patient_revenue_limit: int = Query(
        default=5,
        ge=1,
        le=100,
        description="Maximum patient_revenue results to return (1-100; default 5).",
    ),
    _scope: CapabilityScope = Depends(
        require_capability("analytics.clinic_financials")
    ),
) -> AnalyticsOverviewEnvelope:
    """
    Retrieve clinic-wide analytics metrics.
    Requires analytics.clinic_financials capability.
    """

    return await service.get_overview(
        clinic.id,
        period,
        patient_revenue_sort=patient_revenue_sort,
        patient_revenue_limit=patient_revenue_limit,
    )


@router.get(
    "/analytics/my-performance",
    response_model=TherapistPerformanceEnvelope,
)
async def get_my_performance(
    clinic: CurrentClinicDep,
    current_user: CurrentUserDep,
    service: AnalyticsServiceDep,
    period: AnalyticsPeriod = Query(
        default=AnalyticsPeriod.MONTH,
        description=(
            "UTC calendar reporting period: today (current UTC day), week "
            "(current Monday-based calendar week), month (current UTC calendar "
            "month), or year (current UTC calendar year). The start is inclusive "
            "and the end is exclusive. Defaults to month."
        ),
    ),
    _scope: CapabilityScope = Depends(require_capability("analytics.my_performance")),
) -> TherapistPerformanceEnvelope:
    """
    Retrieve therapist-scoped performance metrics.
    Requires analytics.my_performance capability.
    """

    return await service.get_my_performance(clinic.id, current_user.id, period)
