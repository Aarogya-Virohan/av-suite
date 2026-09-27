from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.enums.analytics import AnalyticsPeriod
from app.schemas.analytics import (
    AnalyticsOverviewEnvelope,
    AnalyticsOverviewResponse,
    AnalyticsPeriodMetadata,
    TherapistPerformanceEnvelope,
    TherapistPerformanceResponse,
)
from app.repositories.analytics import AnalyticsRepository
from app.utils.analytics_periods import AnalyticsPeriods
from sqlalchemy.ext.asyncio import AsyncSession


class AnalyticsService:
    """Service providing clinic-scoped aggregate metrics for the CRM dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service bound to database session."""

        self.session = session

    async def get_overview(
        self, clinic_id: UUID, period: AnalyticsPeriod = AnalyticsPeriod.MONTH
    ) -> AnalyticsOverviewEnvelope:
        """Compute all clinic-scoped analytics metrics using efficient SQL aggregations."""

        periods = AnalyticsPeriods.containing(datetime.now(timezone.utc))
        selected_range = periods.for_period(period)

        repo = AnalyticsRepository(self.session)

        # 1. Patient metrics
        patient_analytics = await repo.get_patient_stats(
            clinic_id, periods.this_month, selected_range
        )

        # 2. Appointment metrics
        appointment_analytics = await repo.get_appointment_stats(
            clinic_id, periods.today, periods.this_week, selected_range
        )

        # 3. Revenue metrics
        revenue_analytics = await repo.get_financial_stats(
            clinic_id, periods.this_month, selected_range
        )

        # 4. Lead metrics
        lead_analytics = await repo.get_lead_stats(clinic_id)

        # 5. Public Booking metrics
        booking_analytics = await repo.get_booking_stats(clinic_id)

        return AnalyticsOverviewEnvelope(
            data=AnalyticsOverviewResponse(
                patients=patient_analytics,
                appointments=appointment_analytics,
                revenue=revenue_analytics,
                leads=lead_analytics,
                booking=booking_analytics,
            ),
            meta=AnalyticsPeriodMetadata(
                period=period,
                start=selected_range.start,
                end=selected_range.end,
            ),
        )

    async def get_my_performance(
        self,
        clinic_id: UUID,
        therapist_id: UUID,
        period: AnalyticsPeriod = AnalyticsPeriod.MONTH,
    ) -> TherapistPerformanceEnvelope:
        """
        Compute therapist-scoped 'own only' performance metrics.

        Per RBAC Spec §4: Analytics for therapist = 'Own only'.
        Per Rev3 scope: exposed via GET /analytics/my-performance.
        Only returns data belonging to the requesting therapist.
        """

        periods = AnalyticsPeriods.containing(datetime.now(timezone.utc))
        selected_range = periods.for_period(period)

        repo = AnalyticsRepository(self.session)

        performance = await repo.get_therapist_performance(
            clinic_id=clinic_id,
            therapist_id=therapist_id,
            month=periods.this_month,
            today=periods.today,
            period=selected_range,
        )
        return TherapistPerformanceEnvelope(
            data=performance,
            meta=AnalyticsPeriodMetadata(
                period=period,
                start=selected_range.start,
                end=selected_range.end,
            ),
        )
