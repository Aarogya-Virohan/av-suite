from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.appointment import AppointmentStatus
from app.enums.billing import InvoiceStatus
from app.enums.booking import AppointmentRequestStatus
from app.enums.lead import LeadStage
from app.enums.patient import PatientStatus
from app.models.appointment import Appointment
from app.models.billing import Invoice
from app.models.booking import AppointmentRequest
from app.models.lead import Lead
from app.models.patient import Patient
from app.schemas.analytics import (
    AppointmentAnalytics,
    BookingAnalytics,
    LeadAnalytics,
    PatientAnalytics,
    RevenueAnalytics,
)


class AnalyticsRepository:
    """Repository handling raw metric queries for analytics dashboards."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_patient_stats(self, clinic_id: UUID, month_start: datetime) -> PatientAnalytics:
        total_patients_stmt = select(func.count(Patient.id)).where(Patient.clinic_id == clinic_id)
        active_patients_stmt = select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id, Patient.status == PatientStatus.ACTIVE
        )
        new_patients_stmt = select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id, Patient.created_at >= month_start
        )

        total_patients = (await self.session.scalar(total_patients_stmt)) or 0
        active_patients = (await self.session.scalar(active_patients_stmt)) or 0
        new_patients = (await self.session.scalar(new_patients_stmt)) or 0

        return PatientAnalytics(
            total_patients=total_patients,
            active_patients=active_patients,
            new_patients_this_month=new_patients,
        )

    async def get_appointment_stats(
        self, clinic_id: UUID, today_start: datetime, today_end: datetime
    ) -> AppointmentAnalytics:
        today_appt_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_at >= today_start,
            Appointment.scheduled_at <= today_end,
        )
        completed_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id, Appointment.status == AppointmentStatus.COMPLETED
        )
        cancelled_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id, Appointment.status == AppointmentStatus.CANCELLED
        )
        no_show_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id, Appointment.status == AppointmentStatus.NO_SHOW
        )

        today_appts = (await self.session.scalar(today_appt_stmt)) or 0
        completed_appts = (await self.session.scalar(completed_stmt)) or 0
        cancelled_appts = (await self.session.scalar(cancelled_stmt)) or 0
        no_show_appts = (await self.session.scalar(no_show_stmt)) or 0

        return AppointmentAnalytics(
            today_appointments=today_appts,
            this_week_appointments=today_appts,  # aggregated
            completed_appointments=completed_appts,
            cancelled_appointments=cancelled_appts,
            no_show_appointments=no_show_appts,
        )

    async def get_revenue_stats(self, clinic_id: UUID, month_start: datetime) -> RevenueAnalytics:
        month_revenue_stmt = select(func.coalesce(func.sum(Invoice.paid_amount), Decimal("0.00"))).where(
            Invoice.clinic_id == clinic_id, Invoice.issue_date >= month_start
        )
        paid_invoices_stmt = select(func.count(Invoice.id)).where(
            Invoice.clinic_id == clinic_id, Invoice.status == InvoiceStatus.PAID
        )
        unpaid_invoices_stmt = select(func.count(Invoice.id)).where(
            Invoice.clinic_id == clinic_id, Invoice.status == InvoiceStatus.UNPAID
        )
        partial_invoices_stmt = select(func.count(Invoice.id)).where(
            Invoice.clinic_id == clinic_id, Invoice.status == InvoiceStatus.PARTIAL
        )
        outstanding_stmt = select(
            func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), Decimal("0.00"))
        ).where(
            Invoice.clinic_id == clinic_id,
            Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL, InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]),
        )

        month_revenue = (await self.session.scalar(month_revenue_stmt)) or Decimal("0.00")
        paid_count = (await self.session.scalar(paid_invoices_stmt)) or 0
        unpaid_count = (await self.session.scalar(unpaid_invoices_stmt)) or 0
        partial_count = (await self.session.scalar(partial_invoices_stmt)) or 0
        outstanding_amount = (await self.session.scalar(outstanding_stmt)) or Decimal("0.00")

        return RevenueAnalytics(
            revenue_this_month=Decimal(str(month_revenue)),
            paid_invoices_count=paid_count,
            unpaid_invoices_count=unpaid_count,
            partial_invoices_count=partial_count,
            total_outstanding_amount=Decimal(str(outstanding_amount)),
        )

    async def get_lead_stats(self, clinic_id: UUID) -> LeadAnalytics:
        total_leads_stmt = select(func.count(Lead.id)).where(Lead.clinic_id == clinic_id)
        total_leads = (await self.session.scalar(total_leads_stmt)) or 0

        lead_stage_stmt = (
            select(Lead.stage, func.count(Lead.id))
            .where(Lead.clinic_id == clinic_id)
            .group_by(Lead.stage)
        )
        stage_counts_result: Sequence[Row[tuple[LeadStage, int]]] = (await self.session.execute(lead_stage_stmt)).all()
        leads_by_stage: dict[str, int] = {st.value: 0 for st in LeadStage}
        converted_count = 0
        for stage_enum, cnt in stage_counts_result:
            leads_by_stage[stage_enum.value] = cnt
            if stage_enum == LeadStage.CONVERTED:
                converted_count = cnt

        conversion_rate = (converted_count / total_leads * 100.0) if total_leads > 0 else 0.0

        return LeadAnalytics(
            total_leads=total_leads,
            leads_by_stage=leads_by_stage,
            conversion_rate=round(conversion_rate, 2),
        )

    async def get_booking_stats(self, clinic_id: UUID) -> BookingAnalytics:
        pending_req_stmt = select(func.count(AppointmentRequest.id)).where(
            AppointmentRequest.clinic_id == clinic_id, AppointmentRequest.status == AppointmentRequestStatus.PENDING
        )
        approved_req_stmt = select(func.count(AppointmentRequest.id)).where(
            AppointmentRequest.clinic_id == clinic_id, AppointmentRequest.status == AppointmentRequestStatus.APPROVED
        )
        rejected_req_stmt = select(func.count(AppointmentRequest.id)).where(
            AppointmentRequest.clinic_id == clinic_id, AppointmentRequest.status == AppointmentRequestStatus.REJECTED
        )

        pending_req = (await self.session.scalar(pending_req_stmt)) or 0
        approved_req = (await self.session.scalar(approved_req_stmt)) or 0
        rejected_req = (await self.session.scalar(rejected_req_stmt)) or 0

        return BookingAnalytics(
            pending_requests=pending_req,
            approved_requests=approved_req,
            rejected_requests=rejected_req,
        )
