from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Row, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.appointment import AppointmentStatus
from app.enums.analytics import PatientRevenueSort
from app.enums.billing import InvoiceStatus, PaymentStatus
from app.enums.booking import AppointmentRequestStatus
from app.enums.lead import LeadStage
from app.enums.patient import PatientStatus
from app.models.appointment import Appointment
from app.models.billing import Invoice, Payment
from app.models.booking import AppointmentRequest
from app.models.lead import Lead
from app.models.patient import Patient
from app.models.treatment import TreatmentSession, SoapAssessment
from app.schemas.analytics import (
    AppointmentAnalytics,
    BookingAnalytics,
    LeadAnalytics,
    PatientAnalytics,
    PatientRevenueAnalytics,
    RevenueAnalytics,
    TherapistPerformanceResponse,
)
from app.utils.analytics_periods import DateRange


class AnalyticsRepository:
    """Repository handling raw metric queries for analytics dashboards."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_patient_stats(
        self, clinic_id: UUID, month: DateRange, period: DateRange
    ) -> PatientAnalytics:
        total_patients_stmt = select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None)
        )
        active_patients_stmt = select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id,
            Patient.status == PatientStatus.ACTIVE,
            Patient.deleted_at.is_(None),
        )
        new_patients_stmt = select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id,
            Patient.created_at >= month.start,
            Patient.created_at < month.end,
            Patient.deleted_at.is_(None),
        )
        new_patients_period_stmt = select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id,
            Patient.created_at >= period.start,
            Patient.created_at < period.end,
            Patient.deleted_at.is_(None),
        )

        total_patients = (await self.session.scalar(total_patients_stmt)) or 0
        active_patients = (await self.session.scalar(active_patients_stmt)) or 0
        new_patients = (await self.session.scalar(new_patients_stmt)) or 0
        new_patients_in_period = (
            await self.session.scalar(new_patients_period_stmt)
        ) or 0

        return PatientAnalytics(
            total_patients=total_patients,
            active_patients=active_patients,
            new_patients_this_month=new_patients,
            new_patients_in_period=new_patients_in_period,
        )

    async def get_appointment_stats(
        self,
        clinic_id: UUID,
        today: DateRange,
        this_week: DateRange,
        period: DateRange,
    ) -> AppointmentAnalytics:
        today_appt_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_at >= today.start,
            Appointment.scheduled_at < today.end,
            Appointment.deleted_at.is_(None),
        )
        week_appt_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_at >= this_week.start,
            Appointment.scheduled_at < this_week.end,
            Appointment.deleted_at.is_(None),
        )
        period_appt_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_at >= period.start,
            Appointment.scheduled_at < period.end,
            Appointment.deleted_at.is_(None),
        )
        completed_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.deleted_at.is_(None),
        )
        cancelled_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.status == AppointmentStatus.CANCELLED,
            Appointment.deleted_at.is_(None),
        )
        no_show_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.status == AppointmentStatus.NO_SHOW,
            Appointment.deleted_at.is_(None),
        )

        today_appts = (await self.session.scalar(today_appt_stmt)) or 0
        week_appts = (await self.session.scalar(week_appt_stmt)) or 0
        period_appts = (await self.session.scalar(period_appt_stmt)) or 0
        completed_appts = (await self.session.scalar(completed_stmt)) or 0
        cancelled_appts = (await self.session.scalar(cancelled_stmt)) or 0
        no_show_appts = (await self.session.scalar(no_show_stmt)) or 0

        return AppointmentAnalytics(
            today_appointments=today_appts,
            this_week_appointments=week_appts,
            appointments_in_period=period_appts,
            completed_appointments=completed_appts,
            cancelled_appointments=cancelled_appts,
            no_show_appointments=no_show_appts,
        )

    async def get_financial_stats(
        self, clinic_id: UUID, month: DateRange, period: DateRange
    ) -> RevenueAnalytics:
        billed_statuses = [
            InvoiceStatus.UNPAID,
            InvoiceStatus.PAID,
            InvoiceStatus.PARTIAL,
            InvoiceStatus.ISSUED,
            InvoiceStatus.OVERDUE,
        ]
        outstanding_statuses = [
            InvoiceStatus.UNPAID,
            InvoiceStatus.PARTIAL,
            InvoiceStatus.ISSUED,
            InvoiceStatus.OVERDUE,
        ]
        period_billed_stmt = select(
            func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00"))
        ).where(
            Invoice.clinic_id == clinic_id,
            Invoice.issue_date >= period.start,
            Invoice.issue_date < period.end,
            Invoice.status.in_(billed_statuses),
            Invoice.deleted_at.is_(None),
        )
        month_collected_stmt = (
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .where(
                Payment.clinic_id == clinic_id,
                Payment.payment_date >= month.start,
                Payment.payment_date < month.end,
                Payment.status == PaymentStatus.COMPLETED,
                Invoice.clinic_id == clinic_id,
                Invoice.deleted_at.is_(None),
            )
        )
        period_collected_stmt = (
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .where(
                Payment.clinic_id == clinic_id,
                Payment.payment_date >= period.start,
                Payment.payment_date < period.end,
                Payment.status == PaymentStatus.COMPLETED,
                Invoice.clinic_id == clinic_id,
                Invoice.deleted_at.is_(None),
            )
        )
        paid_invoices_stmt = select(func.count(Invoice.id)).where(
            Invoice.clinic_id == clinic_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.deleted_at.is_(None),
        )
        unpaid_invoices_stmt = select(func.count(Invoice.id)).where(
            Invoice.clinic_id == clinic_id,
            Invoice.status == InvoiceStatus.UNPAID,
            Invoice.deleted_at.is_(None),
        )
        partial_invoices_stmt = select(func.count(Invoice.id)).where(
            Invoice.clinic_id == clinic_id,
            Invoice.status == InvoiceStatus.PARTIAL,
            Invoice.deleted_at.is_(None),
        )
        outstanding_stmt = select(
            func.coalesce(
                func.sum(Invoice.total_amount - Invoice.paid_amount), Decimal("0.00")
            )
        ).where(
            Invoice.clinic_id == clinic_id,
            Invoice.status.in_(outstanding_statuses),
            Invoice.deleted_at.is_(None),
        )

        period_billed = (await self.session.scalar(period_billed_stmt)) or Decimal(
            "0.00"
        )
        month_collected = (await self.session.scalar(month_collected_stmt)) or Decimal(
            "0.00"
        )
        period_collected = (
            await self.session.scalar(period_collected_stmt)
        ) or Decimal("0.00")
        paid_count = (await self.session.scalar(paid_invoices_stmt)) or 0
        unpaid_count = (await self.session.scalar(unpaid_invoices_stmt)) or 0
        partial_count = (await self.session.scalar(partial_invoices_stmt)) or 0
        outstanding_amount = (await self.session.scalar(outstanding_stmt)) or Decimal(
            "0.00"
        )

        return RevenueAnalytics(
            billed_amount_in_period=Decimal(str(period_billed)),
            collected_amount_in_period=Decimal(str(period_collected)),
            outstanding_amount=Decimal(str(outstanding_amount)),
            revenue_this_month=Decimal(str(month_collected)),
            revenue_in_period=Decimal(str(period_collected)),
            paid_invoices_count=paid_count,
            unpaid_invoices_count=unpaid_count,
            partial_invoices_count=partial_count,
            total_outstanding_amount=Decimal(str(outstanding_amount)),
        )

    async def get_patient_revenue(
        self,
        clinic_id: UUID,
        period: DateRange,
        *,
        sort_by: PatientRevenueSort = PatientRevenueSort.COLLECTED_AMOUNT,
        limit: int = 5,
    ) -> list[PatientRevenueAnalytics]:
        """Return selected-period patient financial totals in ranked order."""

        billed_by_patient = (
            select(
                Invoice.patient_id.label("patient_id"),
                func.sum(Invoice.total_amount).label("billed_amount"),
            )
            .where(
                Invoice.clinic_id == clinic_id,
                Invoice.issue_date >= period.start,
                Invoice.issue_date < period.end,
                Invoice.status.in_(
                    [
                        InvoiceStatus.UNPAID,
                        InvoiceStatus.PAID,
                        InvoiceStatus.PARTIAL,
                        InvoiceStatus.ISSUED,
                        InvoiceStatus.OVERDUE,
                    ]
                ),
                Invoice.deleted_at.is_(None),
            )
            .group_by(Invoice.patient_id)
            .subquery()
        )
        collected_by_patient = (
            select(
                Invoice.patient_id.label("patient_id"),
                func.sum(Payment.amount).label("collected_amount"),
            )
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .where(
                Payment.clinic_id == clinic_id,
                Payment.payment_date >= period.start,
                Payment.payment_date < period.end,
                Payment.status == PaymentStatus.COMPLETED,
                Invoice.clinic_id == clinic_id,
                Invoice.deleted_at.is_(None),
            )
            .group_by(Invoice.patient_id)
            .subquery()
        )
        billed_amount = func.coalesce(
            billed_by_patient.c.billed_amount, Decimal("0.00")
        )
        collected_amount = func.coalesce(
            collected_by_patient.c.collected_amount, Decimal("0.00")
        )
        ranking_amount = (
            collected_amount
            if sort_by == PatientRevenueSort.COLLECTED_AMOUNT
            else billed_amount
        )
        secondary_amount = (
            billed_amount
            if sort_by == PatientRevenueSort.COLLECTED_AMOUNT
            else collected_amount
        )
        statement = (
            select(
                Patient.id,
                Patient.first_name,
                Patient.last_name,
                billed_amount.label("billed_amount"),
                collected_amount.label("collected_amount"),
            )
            .outerjoin(billed_by_patient, billed_by_patient.c.patient_id == Patient.id)
            .outerjoin(
                collected_by_patient,
                collected_by_patient.c.patient_id == Patient.id,
            )
            .where(
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
                or_(billed_amount > 0, collected_amount > 0),
            )
            .order_by(
                desc(ranking_amount),
                desc(secondary_amount),
                Patient.first_name,
                Patient.last_name,
                Patient.id,
            )
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            PatientRevenueAnalytics(
                patient_id=row.id,
                patient_name=f"{row.first_name} {row.last_name}".strip(),
                billed_amount=Decimal(str(row.billed_amount)),
                collected_amount=Decimal(str(row.collected_amount)),
            )
            for row in rows
        ]

    async def get_lead_stats(self, clinic_id: UUID) -> LeadAnalytics:
        total_leads_stmt = select(func.count(Lead.id)).where(
            Lead.clinic_id == clinic_id, Lead.deleted_at.is_(None)
        )
        total_leads = (await self.session.scalar(total_leads_stmt)) or 0

        lead_stage_stmt = (
            select(Lead.stage, func.count(Lead.id))
            .where(Lead.clinic_id == clinic_id, Lead.deleted_at.is_(None))
            .group_by(Lead.stage)
        )
        stage_counts_result: Sequence[Row[tuple[LeadStage, int]]] = (
            await self.session.execute(lead_stage_stmt)
        ).all()
        leads_by_stage: dict[str, int] = {st.value: 0 for st in LeadStage}
        converted_count = 0
        for stage_enum, cnt in stage_counts_result:
            leads_by_stage[stage_enum.value] = cnt
            if stage_enum == LeadStage.CONVERTED:
                converted_count = cnt

        conversion_rate = (
            (converted_count / total_leads * 100.0) if total_leads > 0 else 0.0
        )

        return LeadAnalytics(
            total_leads=total_leads,
            leads_by_stage=leads_by_stage,
            conversion_rate=round(conversion_rate, 2),
        )

    async def get_booking_stats(self, clinic_id: UUID) -> BookingAnalytics:
        pending_req_stmt = select(func.count(AppointmentRequest.id)).where(
            AppointmentRequest.clinic_id == clinic_id,
            AppointmentRequest.status == AppointmentRequestStatus.PENDING,
        )
        approved_req_stmt = select(func.count(AppointmentRequest.id)).where(
            AppointmentRequest.clinic_id == clinic_id,
            AppointmentRequest.status == AppointmentRequestStatus.APPROVED,
        )
        rejected_req_stmt = select(func.count(AppointmentRequest.id)).where(
            AppointmentRequest.clinic_id == clinic_id,
            AppointmentRequest.status == AppointmentRequestStatus.REJECTED,
        )

        pending_req = (await self.session.scalar(pending_req_stmt)) or 0
        approved_req = (await self.session.scalar(approved_req_stmt)) or 0
        rejected_req = (await self.session.scalar(rejected_req_stmt)) or 0

        return BookingAnalytics(
            pending_requests=pending_req,
            approved_requests=approved_req,
            rejected_requests=rejected_req,
        )

    async def get_therapist_performance(
        self,
        clinic_id: UUID,
        therapist_id: UUID,
        month: DateRange,
        today: DateRange,
        period: DateRange,
    ) -> TherapistPerformanceResponse:
        """
        Compute therapist-scoped performance metrics.

        All queries are filtered by both clinic_id and therapist_id.
        Per RBAC Spec §4: Analytics for therapist = 'Own only'.
        """

        # Today's appointments for this therapist
        today_appts_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.therapist_id == therapist_id,
            Appointment.scheduled_at >= today.start,
            Appointment.scheduled_at < today.end,
            Appointment.deleted_at.is_(None),
        )
        period_appts_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.therapist_id == therapist_id,
            Appointment.scheduled_at >= period.start,
            Appointment.scheduled_at < period.end,
            Appointment.deleted_at.is_(None),
        )

        # Completed this month for this therapist
        completed_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.therapist_id == therapist_id,
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.scheduled_at >= month.start,
            Appointment.scheduled_at < month.end,
            Appointment.deleted_at.is_(None),
        )
        completed_period_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.therapist_id == therapist_id,
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.scheduled_at >= period.start,
            Appointment.scheduled_at < period.end,
            Appointment.deleted_at.is_(None),
        )

        # Cancelled this month for this therapist
        cancelled_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.therapist_id == therapist_id,
            Appointment.status == AppointmentStatus.CANCELLED,
            Appointment.scheduled_at >= month.start,
            Appointment.scheduled_at < month.end,
            Appointment.deleted_at.is_(None),
        )
        cancelled_period_stmt = select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            Appointment.therapist_id == therapist_id,
            Appointment.status == AppointmentStatus.CANCELLED,
            Appointment.scheduled_at >= period.start,
            Appointment.scheduled_at < period.end,
            Appointment.deleted_at.is_(None),
        )

        # Treatment sessions logged this month by this therapist
        sessions_stmt = select(func.count(TreatmentSession.id)).where(
            TreatmentSession.clinic_id == clinic_id,
            TreatmentSession.therapist_id == therapist_id,
            TreatmentSession.treatment_date >= month.start,
            TreatmentSession.treatment_date < month.end,
        )
        sessions_period_stmt = select(func.count(TreatmentSession.id)).where(
            TreatmentSession.clinic_id == clinic_id,
            TreatmentSession.therapist_id == therapist_id,
            TreatmentSession.treatment_date >= period.start,
            TreatmentSession.treatment_date < period.end,
        )

        # SOAP notes authored by this therapist this month
        soap_stmt = select(func.count(SoapAssessment.id)).where(
            SoapAssessment.clinic_id == clinic_id,
            SoapAssessment.therapist_id == therapist_id,
            SoapAssessment.created_at >= month.start,
            SoapAssessment.created_at < month.end,
        )
        soap_period_stmt = select(func.count(SoapAssessment.id)).where(
            SoapAssessment.clinic_id == clinic_id,
            SoapAssessment.therapist_id == therapist_id,
            SoapAssessment.created_at >= period.start,
            SoapAssessment.created_at < period.end,
        )

        # Distinct patients seen by this therapist this month
        patients_seen_stmt = (
            select(func.count(func.distinct(Appointment.patient_id)))
            .join(Patient, Patient.id == Appointment.patient_id)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.therapist_id == therapist_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.scheduled_at >= month.start,
                Appointment.scheduled_at < month.end,
                Appointment.deleted_at.is_(None),
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
            )
        )
        patients_seen_period_stmt = (
            select(func.count(func.distinct(Appointment.patient_id)))
            .join(Patient, Patient.id == Appointment.patient_id)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.therapist_id == therapist_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.scheduled_at >= period.start,
                Appointment.scheduled_at < period.end,
                Appointment.deleted_at.is_(None),
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
            )
        )

        today_appts = (await self.session.scalar(today_appts_stmt)) or 0
        period_appts = (await self.session.scalar(period_appts_stmt)) or 0
        completed = (await self.session.scalar(completed_stmt)) or 0
        completed_period = (await self.session.scalar(completed_period_stmt)) or 0
        cancelled = (await self.session.scalar(cancelled_stmt)) or 0
        cancelled_period = (await self.session.scalar(cancelled_period_stmt)) or 0
        sessions = (await self.session.scalar(sessions_stmt)) or 0
        sessions_period = (await self.session.scalar(sessions_period_stmt)) or 0
        soap_notes = (await self.session.scalar(soap_stmt)) or 0
        soap_notes_period = (await self.session.scalar(soap_period_stmt)) or 0
        patients_seen = (await self.session.scalar(patients_seen_stmt)) or 0
        patients_seen_period = (
            await self.session.scalar(patients_seen_period_stmt)
        ) or 0

        return TherapistPerformanceResponse(
            today_appointments=today_appts,
            appointments_in_period=period_appts,
            completed_appointments_this_month=completed,
            completed_appointments_in_period=completed_period,
            cancelled_appointments_this_month=cancelled,
            cancelled_appointments_in_period=cancelled_period,
            treatment_sessions_this_month=sessions,
            treatment_sessions_in_period=sessions_period,
            soap_notes_this_month=soap_notes,
            soap_notes_in_period=soap_notes_period,
            patients_seen_this_month=patients_seen,
            patients_seen_in_period=patients_seen_period,
        )
