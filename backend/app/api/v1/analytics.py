from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from app.core.dependencies import require_permission, require_roles, get_current_user
from app.enums.user import UserRole

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.analytics import AnalyticsOverviewResponse, TherapistPerformanceResponse
from app.services.analytics import AnalyticsService
from app.schemas.envelope import ResponseEnvelope

router = APIRouter(dependencies=[Depends(require_permission("analytics"))])


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
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> ResponseEnvelope[AnalyticsOverviewResponse]:
    """
    Retrieve clinic-wide analytics metrics (admin only).

    Per RBAC Spec §4: Analytics = 'Yes' for Admin only at the clinic-financial level.
    This includes revenue, lead stats, and booking metrics — financial data.
    Therapists use /analytics/my-performance for own-scoped stats instead.
    """

    result = await service.get_overview(clinic.id)
    return ResponseEnvelope(data=result)


@router.get("/analytics/my-performance", response_model=ResponseEnvelope[TherapistPerformanceResponse])
async def get_my_performance(
    clinic: CurrentClinicDep,
    current_user: CurrentUserDep,
    service: AnalyticsServiceDep,
) -> ResponseEnvelope[TherapistPerformanceResponse]:
    """
    Retrieve therapist-scoped performance metrics (therapist + admin access).

    Per RBAC Spec §4: Analytics for therapist = 'Own only'.
    Per Rev3 scope: exposed as a dedicated /my-performance endpoint.

    The therapist_id is derived from the authenticated JWT — the caller cannot
    request another therapist's data via this endpoint.
    Admins may also call this endpoint to preview the therapist view.
    """

    result = await service.get_my_performance(clinic.id, current_user.id)
    return ResponseEnvelope(data=result)
