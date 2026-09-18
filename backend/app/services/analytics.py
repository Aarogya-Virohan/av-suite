from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.schemas.analytics import AnalyticsOverviewResponse, TherapistPerformanceResponse
from app.repositories.analytics import AnalyticsRepository
from sqlalchemy.ext.asyncio import AsyncSession


class AnalyticsService:
    """Service providing clinic-scoped aggregate metrics for the CRM dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service bound to database session."""

        self.session = session

    async def get_overview(self, clinic_id: UUID) -> AnalyticsOverviewResponse:
        """Compute all clinic-scoped analytics metrics using efficient SQL aggregations."""

        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        repo = AnalyticsRepository(self.session)

        # 1. Patient metrics
        patient_analytics = await repo.get_patient_stats(clinic_id, month_start)

        # 2. Appointment metrics
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        today_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
        appointment_analytics = await repo.get_appointment_stats(clinic_id, today_start, today_end)

        # 3. Revenue metrics
        revenue_analytics = await repo.get_revenue_stats(clinic_id, month_start)

        # 4. Lead metrics
        lead_analytics = await repo.get_lead_stats(clinic_id)

        # 5. Public Booking metrics
        booking_analytics = await repo.get_booking_stats(clinic_id)

        return AnalyticsOverviewResponse(
            patients=patient_analytics,
            appointments=appointment_analytics,
            revenue=revenue_analytics,
            leads=lead_analytics,
            booking=booking_analytics,
        )

    async def get_my_performance(self, clinic_id: UUID, therapist_id: UUID) -> TherapistPerformanceResponse:
        """
        Compute therapist-scoped 'own only' performance metrics.

        Per RBAC Spec §4: Analytics for therapist = 'Own only'.
        Per Rev3 scope: exposed via GET /analytics/my-performance.
        Only returns data belonging to the requesting therapist.
        """

        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        today_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)

        repo = AnalyticsRepository(self.session)

        return await repo.get_therapist_performance(
            clinic_id=clinic_id,
            therapist_id=therapist_id,
            month_start=month_start,
            today_start=today_start,
            today_end=today_end,
        )
