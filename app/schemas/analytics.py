from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class PatientAnalytics(BaseModel):
    """Analytics metrics for clinic patients."""

    total_patients: int
    active_patients: int
    new_patients_this_month: int


class AppointmentAnalytics(BaseModel):
    """Analytics metrics for clinic appointments."""

    today_appointments: int
    this_week_appointments: int
    completed_appointments: int
    cancelled_appointments: int
    no_show_appointments: int


class RevenueAnalytics(BaseModel):
    """Analytics metrics for clinic revenue and billing."""

    revenue_this_month: Decimal
    paid_invoices_count: int
    unpaid_invoices_count: int
    partial_invoices_count: int
    total_outstanding_amount: Decimal


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
    """Aggregated dashboard overview response schema."""

    patients: PatientAnalytics
    appointments: AppointmentAnalytics
    revenue: RevenueAnalytics
    leads: LeadAnalytics
    booking: BookingAnalytics
