from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.enums.analytics import AnalyticsPeriod
from app.schemas.envelope import ResponseEnvelope


class AnalyticsPeriodMetadata(BaseModel):
    """Selected UTC calendar range; ``start`` is inclusive and ``end`` exclusive."""

    period: AnalyticsPeriod
    start: datetime
    end: datetime


class PatientAnalytics(BaseModel):
    """Analytics metrics for clinic patients."""

    total_patients: int
    active_patients: int
    new_patients_this_month: int
    new_patients_in_period: int


class AppointmentAnalytics(BaseModel):
    """Analytics metrics for clinic appointments."""

    today_appointments: int
    this_week_appointments: int
    appointments_in_period: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int


class RevenueAnalytics(BaseModel):
    """Financial analytics with billed and actually collected amounts separated."""

    billed_amount_in_period: Decimal = Field(
        description=(
            "Sum of non-draft, non-cancelled invoice total_amount values whose "
            "issue_date is within the selected UTC period [start, end)."
        )
    )
    collected_amount_in_period: Decimal = Field(
        description=(
            "Sum of completed payment amounts whose payment_date is within the "
            "selected UTC period [start, end), linked to a non-deleted invoice."
        )
    )
    outstanding_amount: Decimal = Field(
        description=(
            "Current all-time outstanding invoice balance: total_amount minus "
            "paid_amount for non-deleted invoices in issued, unpaid, partial, or "
            "overdue status. This is a balance snapshot, not a period flow."
        )
    )
    revenue_this_month: Decimal = Field(
        deprecated=True,
        description=(
            "Compatibility alias for collected payment amounts whose payment_date "
            "falls in the current UTC calendar month. Prefer explicit financial fields."
        ),
    )
    revenue_in_period: Decimal = Field(
        deprecated=True,
        description=(
            "Compatibility alias for collected_amount_in_period. Prefer explicit "
            "financial fields."
        ),
    )

    paid_invoices_count: int
    unpaid_invoices_count: int
    partial_invoices_count: int
    total_outstanding_amount: Decimal = Field(
        description=(
            "Legacy alias for outstanding_amount; retains the all-time status-based "
            "invoice balance calculation."
        )
    )


class LeadAnalytics(BaseModel):
    """Analytics metrics for clinic prospective leads."""

    total_leads: int
    leads_by_stage: dict[str, int]
    conversion_rate: float


class BookingAnalytics(BaseModel):
    """Analytics metrics for public booking appointment requests."""

    pending_requests: int
    approved_requests: int
    rejected_requests: int


class AnalyticsOverviewResponse(BaseModel):
    """Aggregated dashboard overview response schema (admin/clinic-wide)."""

    patients: PatientAnalytics
    appointments: AppointmentAnalytics
    revenue: RevenueAnalytics
    leads: LeadAnalytics
    booking: BookingAnalytics


class AnalyticsOverviewEnvelope(ResponseEnvelope[AnalyticsOverviewResponse]):
    """Overview envelope with metadata describing the selected report period."""

    meta: AnalyticsPeriodMetadata


class TherapistPerformanceResponse(BaseModel):
    """
    Therapist-scoped performance metrics for /analytics/my-performance.

    Per RBAC Spec §4: Analytics for therapist = 'Own only'.
    Per Rev3 scope: split analytics into my-performance vs clinic-financials.
    Only contains data belonging to the requesting therapist.
    """

    # Appointment counts (scoped to this therapist)
    today_appointments: int
    appointments_in_period: int
    completed_appointments_this_month: int
    completed_appointments_in_period: int
    cancelled_appointments_this_month: int
    cancelled_appointments_in_period: int

    # Treatment sessions logged by this therapist this month
    treatment_sessions_this_month: int
    treatment_sessions_in_period: int

    # SOAP notes authored by this therapist
    soap_notes_this_month: int
    soap_notes_in_period: int

    # Patient count assigned to this therapist (via appointments this month)
    patients_seen_this_month: int
    patients_seen_in_period: int


class TherapistPerformanceEnvelope(ResponseEnvelope[TherapistPerformanceResponse]):
    """Therapist performance envelope with selected-period metadata."""

    meta: AnalyticsPeriodMetadata
