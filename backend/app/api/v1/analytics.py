from __future__ import annotations

from typing import Annotated

from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException, status
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
            "India calendar reporting period: today, week (Monday based), month, or year. "
            "Optional inclusive start_date and end_date select a custom range. The start is inclusive "
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
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _scope: CapabilityScope = Depends(
        require_capability("analytics.clinic_financials")
    ),
) -> AnalyticsOverviewEnvelope:
    """
    Retrieve clinic-wide analytics metrics.
    Requires analytics.clinic_financials capability.
    """

    _validate_custom_range(start_date, end_date, period)
    return await service.get_overview(
        clinic.id,
        period,
        patient_revenue_sort=patient_revenue_sort,
        patient_revenue_limit=patient_revenue_limit,
        start_date=start_date, end_date=end_date,
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
            "India calendar reporting period: today, week (Monday based), month, or year. "
            "Optional inclusive start_date and end_date select a custom range. The start is inclusive "
            "and the end is exclusive. Defaults to month."
        ),
    ),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _scope: CapabilityScope = Depends(require_capability("analytics.my_performance")),
) -> TherapistPerformanceEnvelope:
    """
    Retrieve therapist-scoped performance metrics.
    Requires analytics.my_performance capability.
    """

    _validate_custom_range(start_date, end_date, period)
    return await service.get_my_performance(clinic.id, current_user.id, period, start_date=start_date, end_date=end_date)


def _validate_custom_range(start_date: date | None, end_date: date | None, period: AnalyticsPeriod) -> None:
    if (start_date is None) != (end_date is None):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date and end_date must be supplied together")
    if start_date is None:
        if period == AnalyticsPeriod.CUSTOM:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="custom period requires start_date and end_date")
        return
    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date must not be after end_date")
    if end_date == date.max or start_date.year > date.max.year - 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date range is outside the supported calendar")
    # 24 calendar months, clamped for month ends.
    from calendar import monthrange
    year = start_date.year + (start_date.month - 1 + 24) // 12
    month = (start_date.month - 1 + 24) % 12 + 1
    limit = date(year, month, min(start_date.day, monthrange(year, month)[1]))
    if end_date > limit:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date range must not exceed 24 months")
