from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.enums.appointment import AppointmentStatus
from app.enums.analytics import AnalyticsPeriod, PatientRevenueSort
from app.enums.billing import InvoiceStatus, PaymentMethod, PaymentStatus
from app.enums.shared import Specialty
from app.enums.user import UserRole
from app.models.appointment import Appointment
from app.models.billing import Invoice, Payment
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.treatment import SoapAssessment, TreatmentSession
from app.models.user import User
from app.repositories.analytics import AnalyticsRepository
from app.services import analytics as analytics_service_module
from app.utils.analytics_periods import AnalyticsPeriods
from app.main import app

UTC = timezone.utc
FROZEN_NOW = datetime(2024, 3, 6, 12, tzinfo=UTC)
MONTH = AnalyticsPeriods.containing(datetime(2024, 3, 6, 12, tzinfo=UTC)).this_month
TODAY = AnalyticsPeriods.containing(datetime(2024, 3, 6, 12, tzinfo=UTC)).today
WEEK = AnalyticsPeriods.containing(datetime(2024, 3, 6, 12, tzinfo=UTC)).this_week


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return (
            FROZEN_NOW.astimezone(tz)
            if tz is not None
            else FROZEN_NOW.replace(tzinfo=None)
        )


def test_analytics_periods_are_utc_calendar_ranges() -> None:
    periods = AnalyticsPeriods.containing(
        datetime(2024, 1, 1, 0, 30, tzinfo=timezone(timedelta(hours=14)))
    )

    assert periods.today.start == datetime(2023, 12, 31, tzinfo=UTC)
    assert periods.today.end == datetime(2024, 1, 1, tzinfo=UTC)
    assert periods.this_week.start == datetime(2023, 12, 25, tzinfo=UTC)
    assert periods.this_week.end == datetime(2024, 1, 1, tzinfo=UTC)
    assert periods.this_month.start == datetime(2023, 12, 1, tzinfo=UTC)
    assert periods.this_month.end == datetime(2024, 1, 1, tzinfo=UTC)
    assert periods.this_year.start == datetime(2023, 1, 1, tzinfo=UTC)
    assert periods.this_year.end == datetime(2024, 1, 1, tzinfo=UTC)


async def _create_context(session: AsyncSession):
    clinic = Clinic(name=f"Analytics clinic {uuid4()}")
    other_clinic = Clinic(name=f"Other analytics clinic {uuid4()}")
    session.add_all([clinic, other_clinic])
    await session.flush()

    therapist = User(
        clinic_id=clinic.id,
        email=f"therapist-{uuid4()}@analytics.test",
        password_hash="not-used",
        role=UserRole.THERAPIST,
        first_name="Test",
        last_name="Therapist",
    )
    other_therapist = User(
        clinic_id=clinic.id,
        email=f"therapist-{uuid4()}@analytics.test",
        password_hash="not-used",
        role=UserRole.THERAPIST,
        first_name="Other",
        last_name="Therapist",
    )
    outside_therapist = User(
        clinic_id=other_clinic.id,
        email=f"therapist-{uuid4()}@analytics.test",
        password_hash="not-used",
        role=UserRole.THERAPIST,
        first_name="Outside",
        last_name="Therapist",
    )
    session.add_all([therapist, other_therapist, outside_therapist])
    await session.flush()

    patients = [
        Patient(clinic_id=clinic.id, first_name=f"Patient{i}", last_name="Test")
        for i in range(6)
    ]
    outside_patient = Patient(
        clinic_id=other_clinic.id, first_name="Outside", last_name="Test"
    )
    session.add_all([*patients, outside_patient])
    await session.flush()

    return (
        clinic,
        other_clinic,
        therapist,
        other_therapist,
        outside_therapist,
        patients,
        outside_patient,
    )


def _appointment(
    clinic_id,
    therapist_id,
    patient_id,
    scheduled_at: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
    deleted_at: datetime | None = None,
) -> Appointment:
    return Appointment(
        clinic_id=clinic_id,
        therapist_id=therapist_id,
        patient_id=patient_id,
        scheduled_at=scheduled_at,
        status=status,
        deleted_at=deleted_at,
    )


def _invoice(
    clinic_id,
    patient_id,
    issue_date: datetime,
    total_amount: Decimal,
    paid_amount: Decimal = Decimal("0.00"),
    status: InvoiceStatus = InvoiceStatus.ISSUED,
    deleted_at: datetime | None = None,
) -> Invoice:
    return Invoice(
        clinic_id=clinic_id,
        patient_id=patient_id,
        invoice_number=f"INV-{uuid4()}",
        issue_date=issue_date,
        subtotal=total_amount,
        total_amount=total_amount,
        paid_amount=paid_amount,
        status=status,
        deleted_at=deleted_at,
    )


def _payment(
    invoice: Invoice,
    amount: Decimal,
    payment_date: datetime,
    status: PaymentStatus = PaymentStatus.COMPLETED,
) -> Payment:
    return Payment(
        clinic_id=invoice.clinic_id,
        invoice_id=invoice.id,
        patient_id=invoice.patient_id,
        amount=amount,
        payment_method=PaymentMethod.CASH,
        payment_date=payment_date,
        status=status,
    )


@pytest.mark.asyncio
async def test_overview_uses_today_week_and_month_ranges_and_clinic_scope(
    db_session: AsyncSession,
) -> None:
    clinic, other_clinic, therapist, _, outside_therapist, patients, outside_patient = (
        await _create_context(db_session)
    )
    appointments = [
        _appointment(
            clinic.id,
            therapist.id,
            patients[0].id,
            datetime(2024, 2, 1, tzinfo=UTC),
            AppointmentStatus.COMPLETED,
        ),
        _appointment(
            clinic.id, therapist.id, patients[0].id, TODAY.start - timedelta(minutes=1)
        ),
        _appointment(clinic.id, therapist.id, patients[0].id, TODAY.start),
        _appointment(clinic.id, therapist.id, patients[0].id, TODAY.end),
        _appointment(clinic.id, therapist.id, patients[0].id, WEEK.start),
        _appointment(clinic.id, therapist.id, patients[0].id, WEEK.end),
        _appointment(
            clinic.id, therapist.id, patients[0].id, TODAY.start, deleted_at=TODAY.start
        ),
        _appointment(
            other_clinic.id, outside_therapist.id, outside_patient.id, TODAY.start
        ),
    ]

    patients[1].created_at = MONTH.start - timedelta(microseconds=1)
    patients[2].created_at = MONTH.start
    patients[3].created_at = MONTH.end - timedelta(microseconds=1)
    patients[4].created_at = MONTH.end
    patients[5].created_at = MONTH.start
    patients[5].deleted_at = MONTH.start
    outside_patient.created_at = MONTH.start
    invoices = [
        Invoice(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            invoice_number=f"INV-{uuid4()}",
            issue_date=MONTH.start - timedelta(microseconds=1),
            subtotal=Decimal("10.00"),
            total_amount=Decimal("10.00"),
            paid_amount=Decimal("10.00"),
            status=InvoiceStatus.PAID,
        ),
        Invoice(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            invoice_number=f"INV-{uuid4()}",
            issue_date=MONTH.start,
            subtotal=Decimal("20.00"),
            total_amount=Decimal("20.00"),
            paid_amount=Decimal("20.00"),
            status=InvoiceStatus.PAID,
        ),
        Invoice(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            invoice_number=f"INV-{uuid4()}",
            issue_date=MONTH.end,
            subtotal=Decimal("30.00"),
            total_amount=Decimal("30.00"),
            paid_amount=Decimal("30.00"),
            status=InvoiceStatus.PAID,
        ),
        Invoice(
            clinic_id=other_clinic.id,
            patient_id=outside_patient.id,
            invoice_number=f"INV-{uuid4()}",
            issue_date=MONTH.start,
            subtotal=Decimal("40.00"),
            total_amount=Decimal("40.00"),
            paid_amount=Decimal("40.00"),
            status=InvoiceStatus.PAID,
        ),
    ]
    db_session.add_all([*appointments, *invoices])
    await db_session.flush()
    db_session.add(_payment(invoices[1], Decimal("20.00"), MONTH.start))
    await db_session.flush()

    repository = AnalyticsRepository(db_session)
    appointments_result = await repository.get_appointment_stats(
        clinic.id, TODAY, WEEK, MONTH
    )
    patients_result = await repository.get_patient_stats(clinic.id, MONTH, MONTH)
    revenue_result = await repository.get_financial_stats(clinic.id, MONTH, MONTH)

    assert appointments_result.today_appointments == 1
    assert appointments_result.this_week_appointments == 4
    assert (
        appointments_result.this_week_appointments
        != appointments_result.today_appointments
    )
    assert appointments_result.completed_appointments == 1
    assert patients_result.new_patients_this_month == 2
    assert revenue_result.billed_amount_in_period == Decimal("20.00")
    assert revenue_result.collected_amount_in_period == Decimal("20.00")
    assert revenue_result.outstanding_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_financial_metrics_are_zero_without_financial_records(
    db_session: AsyncSession,
) -> None:
    clinic, *_ = await _create_context(db_session)

    result = await AnalyticsRepository(db_session).get_financial_stats(
        clinic.id, MONTH, MONTH
    )

    assert result.billed_amount_in_period == Decimal("0.00")
    assert result.collected_amount_in_period == Decimal("0.00")
    assert result.outstanding_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_financial_totals_use_invoices_payments_statuses_and_clinic_scope(
    db_session: AsyncSession,
) -> None:
    clinic, other_clinic, _, _, _, patients, outside_patient = await _create_context(
        db_session
    )
    paid = _invoice(
        clinic.id,
        patients[0].id,
        MONTH.start,
        Decimal("100.00"),
        Decimal("100.00"),
        InvoiceStatus.PAID,
    )
    partial = _invoice(
        clinic.id,
        patients[1].id,
        MONTH.start,
        Decimal("80.00"),
        Decimal("30.00"),
        InvoiceStatus.PARTIAL,
    )
    issued = _invoice(clinic.id, patients[2].id, MONTH.start, Decimal("20.00"))
    draft = _invoice(
        clinic.id,
        patients[3].id,
        MONTH.start,
        Decimal("300.00"),
        status=InvoiceStatus.DRAFT,
    )
    cancelled = _invoice(
        clinic.id,
        patients[4].id,
        MONTH.start,
        Decimal("400.00"),
        status=InvoiceStatus.CANCELLED,
    )
    deleted = _invoice(
        clinic.id,
        patients[5].id,
        MONTH.start,
        Decimal("500.00"),
        Decimal("500.00"),
        InvoiceStatus.PAID,
        deleted_at=MONTH.start,
    )
    outside = _invoice(
        other_clinic.id,
        outside_patient.id,
        MONTH.start,
        Decimal("900.00"),
        Decimal("900.00"),
        InvoiceStatus.PAID,
    )
    db_session.add_all([paid, partial, issued, draft, cancelled, deleted, outside])
    await db_session.flush()
    db_session.add_all(
        [
            _payment(paid, Decimal("100.00"), MONTH.start),
            _payment(partial, Decimal("10.00"), MONTH.start),
            _payment(partial, Decimal("20.00"), MONTH.start),
            _payment(partial, Decimal("70.00"), MONTH.start, PaymentStatus.PENDING),
            _payment(partial, Decimal("50.00"), MONTH.start, PaymentStatus.VOIDED),
            _payment(partial, Decimal("40.00"), MONTH.start, PaymentStatus.REFUNDED),
            _payment(draft, Decimal("7.00"), MONTH.start),
            _payment(cancelled, Decimal("11.00"), MONTH.start),
            _payment(deleted, Decimal("25.00"), MONTH.start),
            _payment(outside, Decimal("900.00"), MONTH.start),
        ]
    )
    await db_session.flush()

    result = await AnalyticsRepository(db_session).get_financial_stats(
        clinic.id, MONTH, MONTH
    )

    assert result.billed_amount_in_period == Decimal("200.00")
    assert result.collected_amount_in_period == Decimal("148.00")
    assert result.outstanding_amount == Decimal("70.00")
    assert result.total_outstanding_amount == Decimal("70.00")
    patient_revenue = await AnalyticsRepository(db_session).get_patient_revenue(
        clinic.id, MONTH, limit=100
    )
    patient_revenue_by_id = {
        patient.patient_id: patient for patient in patient_revenue
    }
    assert patient_revenue_by_id[patients[3].id].billed_amount == Decimal("0.00")
    assert patient_revenue_by_id[patients[3].id].collected_amount == Decimal("7.00")
    assert patient_revenue_by_id[patients[4].id].billed_amount == Decimal("0.00")
    assert patient_revenue_by_id[patients[4].id].collected_amount == Decimal("11.00")


@pytest.mark.asyncio
async def test_deprecated_revenue_fields_preserve_invoice_paid_amount_semantics(
    db_session: AsyncSession,
) -> None:
    clinic, _, _, _, _, patients, _ = await _create_context(db_session)
    draft = _invoice(
        clinic.id,
        patients[0].id,
        MONTH.start,
        Decimal("100.00"),
        Decimal("35.00"),
        InvoiceStatus.DRAFT,
    )
    cancelled = _invoice(
        clinic.id,
        patients[1].id,
        MONTH.start,
        Decimal("100.00"),
        Decimal("40.00"),
        InvoiceStatus.CANCELLED,
    )
    prior_invoice = _invoice(
        clinic.id,
        patients[2].id,
        MONTH.start - timedelta(days=1),
        Decimal("100.00"),
        Decimal("60.00"),
        InvoiceStatus.PAID,
    )
    deleted_invoice = _invoice(
        clinic.id,
        patients[3].id,
        MONTH.start,
        Decimal("100.00"),
        Decimal("90.00"),
        InvoiceStatus.PAID,
        deleted_at=MONTH.start,
    )
    db_session.add_all([draft, cancelled, prior_invoice, deleted_invoice])
    await db_session.flush()
    db_session.add(_payment(prior_invoice, Decimal("7.00"), MONTH.start))
    await db_session.flush()

    result = await AnalyticsRepository(db_session).get_financial_stats(
        clinic.id, MONTH, MONTH
    )

    assert result.revenue_this_month == Decimal("75.00")
    assert result.revenue_in_period == Decimal("75.00")
    assert result.collected_amount_in_period == Decimal("7.00")


@pytest.mark.asyncio
async def test_financial_metrics_use_half_open_invoice_and_payment_date_ranges(
    db_session: AsyncSession,
) -> None:
    clinic, _, _, _, _, patients, _ = await _create_context(db_session)
    before_start = _invoice(
        clinic.id,
        patients[0].id,
        MONTH.start - timedelta(microseconds=1),
        Decimal("1.00"),
    )
    at_start = _invoice(clinic.id, patients[1].id, MONTH.start, Decimal("10.00"))
    before_end = _invoice(
        clinic.id,
        patients[2].id,
        MONTH.end - timedelta(microseconds=1),
        Decimal("20.00"),
    )
    at_end = _invoice(clinic.id, patients[3].id, MONTH.end, Decimal("30.00"))
    after_end = _invoice(
        clinic.id,
        patients[4].id,
        MONTH.end + timedelta(microseconds=1),
        Decimal("40.00"),
    )
    db_session.add_all([before_start, at_start, before_end, at_end, after_end])
    await db_session.flush()
    db_session.add_all(
        [
            _payment(
                at_start, Decimal("1.00"), MONTH.start - timedelta(microseconds=1)
            ),
            _payment(at_start, Decimal("2.00"), MONTH.start),
            _payment(at_start, Decimal("3.00"), MONTH.end - timedelta(microseconds=1)),
            _payment(at_start, Decimal("4.00"), MONTH.end),
            _payment(
                at_start,
                Decimal("5.00"),
                MONTH.end + timedelta(microseconds=1),
            ),
        ]
    )
    await db_session.flush()

    result = await AnalyticsRepository(db_session).get_financial_stats(
        clinic.id, MONTH, MONTH
    )

    assert result.billed_amount_in_period == Decimal("30.00")
    assert result.collected_amount_in_period == Decimal("5.00")


@pytest.mark.asyncio
async def test_patient_revenue_is_empty_without_financial_activity(
    db_session: AsyncSession,
) -> None:
    clinic, *_ = await _create_context(db_session)

    result = await AnalyticsRepository(db_session).get_patient_revenue(clinic.id, MONTH)

    assert result == []


@pytest.mark.asyncio
async def test_patient_revenue_is_empty_when_clinic_has_no_patients(
    db_session: AsyncSession,
) -> None:
    clinic = Clinic(name=f"Empty analytics clinic {uuid4()}")
    db_session.add(clinic)
    await db_session.flush()

    result = await AnalyticsRepository(db_session).get_patient_revenue(clinic.id, MONTH)

    assert result == []


@pytest.mark.asyncio
async def test_patient_revenue_aggregates_ranks_and_excludes_deleted_or_other_clinic(
    db_session: AsyncSession,
) -> None:
    clinic, other_clinic, _, _, _, patients, outside_patient = await _create_context(
        db_session
    )
    paid_invoice = _invoice(
        clinic.id,
        patients[0].id,
        MONTH.start,
        Decimal("100.00"),
        Decimal("20.00"),
        InvoiceStatus.PARTIAL,
    )
    second_invoice = _invoice(
        clinic.id,
        patients[0].id,
        MONTH.start,
        Decimal("50.00"),
        Decimal("5.00"),
        InvoiceStatus.PARTIAL,
    )
    billed_only_invoice = _invoice(
        clinic.id, patients[1].id, MONTH.start, Decimal("80.00")
    )
    collected_only_invoice = _invoice(
        clinic.id,
        patients[2].id,
        MONTH.start - timedelta(days=1),
        Decimal("40.00"),
        Decimal("15.00"),
        InvoiceStatus.PARTIAL,
    )
    deleted_invoice = _invoice(
        clinic.id,
        patients[3].id,
        MONTH.start,
        Decimal("900.00"),
        Decimal("900.00"),
        InvoiceStatus.PAID,
        deleted_at=MONTH.start,
    )
    deleted_patient_invoice = _invoice(
        clinic.id,
        patients[4].id,
        MONTH.start,
        Decimal("700.00"),
        Decimal("700.00"),
        InvoiceStatus.PAID,
    )
    other_clinic_invoice = _invoice(
        other_clinic.id,
        outside_patient.id,
        MONTH.start,
        Decimal("800.00"),
        Decimal("800.00"),
        InvoiceStatus.PAID,
    )
    patients[4].deleted_at = MONTH.start
    db_session.add_all(
        [
            paid_invoice,
            second_invoice,
            billed_only_invoice,
            collected_only_invoice,
            deleted_invoice,
            deleted_patient_invoice,
            other_clinic_invoice,
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            _payment(paid_invoice, Decimal("10.00"), MONTH.start),
            _payment(paid_invoice, Decimal("10.00"), MONTH.start),
            _payment(second_invoice, Decimal("5.00"), MONTH.start),
            _payment(collected_only_invoice, Decimal("15.00"), MONTH.start),
            _payment(deleted_invoice, Decimal("900.00"), MONTH.start),
            _payment(deleted_patient_invoice, Decimal("700.00"), MONTH.start),
            _payment(other_clinic_invoice, Decimal("800.00"), MONTH.start),
        ]
    )
    await db_session.flush()

    repository = AnalyticsRepository(db_session)
    collected_ranked = await repository.get_patient_revenue(clinic.id, MONTH)
    billed_ranked = await repository.get_patient_revenue(
        clinic.id, MONTH, sort_by=PatientRevenueSort.BILLED_AMOUNT
    )

    assert [patient.patient_id for patient in collected_ranked] == [
        patients[0].id,
        patients[2].id,
        patients[1].id,
    ]
    assert [patient.patient_name for patient in collected_ranked] == [
        "Patient0 Test",
        "Patient2 Test",
        "Patient1 Test",
    ]
    assert [
        (patient.billed_amount, patient.collected_amount)
        for patient in collected_ranked
    ] == [
        (Decimal("150.00"), Decimal("25.00")),
        (Decimal("0.00"), Decimal("15.00")),
        (Decimal("80.00"), Decimal("0.00")),
    ]
    assert [patient.patient_id for patient in billed_ranked] == [
        patients[0].id,
        patients[1].id,
        patients[2].id,
    ]
    limited = await repository.get_patient_revenue(clinic.id, MONTH, limit=1)
    assert len(limited) == 1
    assert limited[0].patient_id == patients[0].id


@pytest.mark.asyncio
async def test_patient_revenue_uses_independent_dates_and_half_open_boundaries(
    db_session: AsyncSession,
) -> None:
    clinic, _, _, _, _, patients, _ = await _create_context(db_session)
    billed_at_start = _invoice(clinic.id, patients[0].id, MONTH.start, Decimal("10.00"))
    billed_before_start = _invoice(
        clinic.id,
        patients[1].id,
        MONTH.start - timedelta(microseconds=1),
        Decimal("20.00"),
        Decimal("5.00"),
        InvoiceStatus.PARTIAL,
    )
    billed_before_end = _invoice(
        clinic.id,
        patients[2].id,
        MONTH.end - timedelta(microseconds=1),
        Decimal("30.00"),
    )
    billed_at_end = _invoice(clinic.id, patients[3].id, MONTH.end, Decimal("40.00"))
    invoice_for_payments = _invoice(
        clinic.id,
        patients[4].id,
        MONTH.start - timedelta(days=2),
        Decimal("50.00"),
        Decimal("20.00"),
        InvoiceStatus.PARTIAL,
    )
    db_session.add_all(
        [
            billed_at_start,
            billed_before_start,
            billed_before_end,
            billed_at_end,
            invoice_for_payments,
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            _payment(
                billed_at_start,
                Decimal("1.00"),
                MONTH.start - timedelta(microseconds=1),
            ),
            _payment(billed_before_start, Decimal("5.00"), MONTH.start),
            _payment(
                billed_before_end,
                Decimal("3.00"),
                MONTH.end - timedelta(microseconds=1),
            ),
            _payment(billed_at_end, Decimal("4.00"), MONTH.end),
            _payment(invoice_for_payments, Decimal("7.00"), MONTH.start),
            _payment(
                invoice_for_payments,
                Decimal("8.00"),
                MONTH.end + timedelta(microseconds=1),
            ),
        ]
    )
    await db_session.flush()

    result = await AnalyticsRepository(db_session).get_patient_revenue(clinic.id, MONTH)
    by_patient_id = {patient.patient_id: patient for patient in result}

    assert by_patient_id[patients[0].id].billed_amount == Decimal("10.00")
    assert by_patient_id[patients[0].id].collected_amount == Decimal("0.00")
    assert by_patient_id[patients[1].id].billed_amount == Decimal("0.00")
    assert by_patient_id[patients[1].id].collected_amount == Decimal("5.00")
    assert by_patient_id[patients[2].id].billed_amount == Decimal("30.00")
    assert patients[3].id not in by_patient_id
    assert by_patient_id[patients[4].id].billed_amount == Decimal("0.00")
    assert by_patient_id[patients[4].id].collected_amount == Decimal("7.00")


@pytest.mark.asyncio
async def test_patient_revenue_default_limit_and_ties_are_deterministic(
    db_session: AsyncSession,
) -> None:
    clinic, _, _, _, _, patients, _ = await _create_context(db_session)
    names_and_totals = [
        ("Zoe", "Patient", Decimal("100.00")),
        ("Amy", "Patient", Decimal("100.00")),
        ("Amy", "Patient", Decimal("100.00")),
        ("Aaron", "Patient", Decimal("50.00")),
        ("Benny", "Patient", Decimal("50.00")),
        ("Other", "Patient", Decimal("40.00")),
    ]
    invoices = []
    for patient, (first_name, last_name, total) in zip(patients, names_and_totals):
        patient.first_name = first_name
        patient.last_name = last_name
        invoices.append(
            _invoice(
                clinic.id,
                patient.id,
                MONTH.start,
                total,
                Decimal("10.00"),
                InvoiceStatus.PARTIAL,
            )
        )
    db_session.add_all(invoices)
    await db_session.flush()
    db_session.add_all(
        [_payment(invoice, Decimal("10.00"), MONTH.start) for invoice in invoices]
    )
    await db_session.flush()

    result = await AnalyticsRepository(db_session).get_patient_revenue(
        clinic.id, MONTH
    )

    expected_top_five = [
        *sorted([patients[1].id, patients[2].id]),
        patients[0].id,
        patients[3].id,
        patients[4].id,
    ]
    assert len(result) == 5
    assert [patient.patient_id for patient in result] == expected_top_five


@pytest.mark.asyncio
async def test_personal_month_metrics_are_bounded_and_scoped(
    db_session: AsyncSession,
) -> None:
    (
        clinic,
        other_clinic,
        therapist,
        other_therapist,
        outside_therapist,
        patients,
        outside_patient,
    ) = await _create_context(db_session)
    deleted_patient = patients[5]
    deleted_patient.deleted_at = MONTH.start

    appointments = [
        _appointment(
            clinic.id,
            therapist.id,
            patients[0].id,
            MONTH.start,
            AppointmentStatus.COMPLETED,
        ),
        _appointment(
            clinic.id,
            therapist.id,
            patients[1].id,
            MONTH.start - timedelta(microseconds=1),
            AppointmentStatus.COMPLETED,
        ),
        _appointment(
            clinic.id,
            therapist.id,
            patients[2].id,
            MONTH.end,
            AppointmentStatus.COMPLETED,
        ),
        _appointment(
            clinic.id,
            other_therapist.id,
            patients[3].id,
            MONTH.start,
            AppointmentStatus.COMPLETED,
        ),
        _appointment(
            clinic.id,
            therapist.id,
            deleted_patient.id,
            MONTH.start,
            AppointmentStatus.COMPLETED,
        ),
        _appointment(
            clinic.id,
            therapist.id,
            patients[4].id,
            MONTH.start,
            AppointmentStatus.COMPLETED,
            deleted_at=MONTH.start,
        ),
        _appointment(
            clinic.id,
            therapist.id,
            patients[0].id,
            MONTH.start,
            AppointmentStatus.CANCELLED,
        ),
        _appointment(
            clinic.id,
            therapist.id,
            patients[1].id,
            MONTH.end,
            AppointmentStatus.CANCELLED,
        ),
        _appointment(
            other_clinic.id,
            outside_therapist.id,
            outside_patient.id,
            MONTH.start,
            AppointmentStatus.COMPLETED,
        ),
        _appointment(clinic.id, therapist.id, patients[0].id, TODAY.start),
        _appointment(clinic.id, other_therapist.id, patients[1].id, TODAY.start),
    ]
    sessions = [
        TreatmentSession(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=therapist.id,
            treatment_date=MONTH.start,
            treatment="In-range session",
        ),
        TreatmentSession(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=therapist.id,
            treatment_date=MONTH.end,
            treatment="End-boundary session",
        ),
        TreatmentSession(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=therapist.id,
            treatment_date=MONTH.start - timedelta(microseconds=1),
            treatment="Before-month session",
        ),
        TreatmentSession(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=other_therapist.id,
            treatment_date=MONTH.start,
            treatment="Other therapist session",
        ),
    ]
    soap_notes = [
        SoapAssessment(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=therapist.id,
            specialty=Specialty.PHYSIOTHERAPY,
            created_at=MONTH.start,
            form_data={},
        ),
        SoapAssessment(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=therapist.id,
            specialty=Specialty.PHYSIOTHERAPY,
            created_at=MONTH.end,
            form_data={},
        ),
        SoapAssessment(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=therapist.id,
            specialty=Specialty.PHYSIOTHERAPY,
            created_at=MONTH.start - timedelta(microseconds=1),
            form_data={},
        ),
        SoapAssessment(
            clinic_id=clinic.id,
            patient_id=patients[0].id,
            therapist_id=other_therapist.id,
            specialty=Specialty.PHYSIOTHERAPY,
            created_at=MONTH.start,
            form_data={},
        ),
    ]
    db_session.add_all([*appointments, *sessions, *soap_notes])
    await db_session.flush()

    result = await AnalyticsRepository(db_session).get_therapist_performance(
        clinic.id, therapist.id, MONTH, TODAY, MONTH
    )

    assert result.today_appointments == 1
    assert result.completed_appointments_this_month == 2
    assert result.cancelled_appointments_this_month == 1
    assert result.treatment_sessions_this_month == 1
    assert result.soap_notes_this_month == 1
    assert result.patients_seen_this_month == 1


@pytest.mark.asyncio
async def test_analytics_api_period_contract_and_scoping(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(analytics_service_module, "datetime", FrozenDateTime)

    clinic = await db_session.scalar(
        select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
    )
    admin = await db_session.scalar(
        select(User).where(User.email == "admin@avtest.com")
    )
    other_therapist = await db_session.scalar(
        select(User).where(User.email == "therapist@avtest.com")
    )
    assert clinic is not None and admin is not None and other_therapist is not None

    other_clinic = Clinic(name=f"Analytics API clinic {uuid4()}")
    db_session.add(other_clinic)
    await db_session.flush()
    outside_user = User(
        clinic_id=other_clinic.id,
        email=f"outside-{uuid4()}@analytics.test",
        password_hash="not-used",
        role=UserRole.THERAPIST,
        first_name="Outside",
        last_name="Therapist",
    )
    db_session.add(outside_user)
    await db_session.flush()

    event_dates = [
        datetime(2024, 1, 1, 0, tzinfo=UTC),
        datetime(2024, 3, 1, 0, tzinfo=UTC),
        datetime(2024, 3, 4, 0, tzinfo=UTC),
        datetime(2024, 3, 6, 0, tzinfo=UTC),
        datetime(2024, 3, 7, 0, tzinfo=UTC),
        datetime(2024, 3, 11, 0, tzinfo=UTC),
        datetime(2024, 4, 1, 0, tzinfo=UTC),
        datetime(2025, 1, 1, 0, tzinfo=UTC),
        datetime(2023, 12, 31, 12, tzinfo=UTC),
    ]
    patients = [
        Patient(
            clinic_id=clinic.id,
            first_name=f"API{i}",
            last_name="Patient",
            created_at=event_date,
        )
        for i, event_date in enumerate(event_dates)
    ]
    outside_patient = Patient(
        clinic_id=other_clinic.id,
        first_name="Outside",
        last_name="Patient",
        created_at=event_dates[3],
    )
    db_session.add_all([*patients, outside_patient])
    await db_session.flush()

    appointments = [
        _appointment(
            clinic.id,
            admin.id,
            patient.id,
            event_date,
            (
                AppointmentStatus.CANCELLED
                if index == 2
                else (
                    AppointmentStatus.COMPLETED
                    if index == 3
                    else AppointmentStatus.SCHEDULED
                )
            ),
        )
        for index, (patient, event_date) in enumerate(zip(patients, event_dates))
    ]
    appointments.extend(
        [
            _appointment(
                clinic.id,
                other_therapist.id,
                patients[3].id,
                event_dates[3],
                AppointmentStatus.COMPLETED,
            ),
            _appointment(
                other_clinic.id,
                outside_user.id,
                outside_patient.id,
                event_dates[3],
                AppointmentStatus.COMPLETED,
            ),
        ]
    )
    invoices = [
        Invoice(
            clinic_id=clinic.id,
            patient_id=patient.id,
            invoice_number=f"API-{uuid4()}",
            issue_date=event_date,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            paid_amount=Decimal("100.00"),
            status=InvoiceStatus.PAID,
        )
        for patient, event_date in zip(patients, event_dates)
    ]
    outside_invoice = Invoice(
        clinic_id=other_clinic.id,
        patient_id=outside_patient.id,
        invoice_number=f"API-{uuid4()}",
        issue_date=event_dates[3],
        subtotal=Decimal("900.00"),
        total_amount=Decimal("900.00"),
        paid_amount=Decimal("900.00"),
        status=InvoiceStatus.PAID,
    )
    treatments = [
        TreatmentSession(
            clinic_id=clinic.id,
            patient_id=patients[3].id,
            therapist_id=admin.id,
            treatment_date=event_dates[3],
            treatment="Selected day",
        ),
        TreatmentSession(
            clinic_id=clinic.id,
            patient_id=patients[4].id,
            therapist_id=admin.id,
            treatment_date=event_dates[4],
            treatment="At day end",
        ),
    ]
    soap_notes = [
        SoapAssessment(
            clinic_id=clinic.id,
            patient_id=patients[index].id,
            therapist_id=admin.id,
            specialty=Specialty.PHYSIOTHERAPY,
            created_at=event_dates[index],
            form_data={},
        )
        for index in (3, 4)
    ]
    db_session.add_all(
        [*appointments, *invoices, outside_invoice, *treatments, *soap_notes]
    )
    await db_session.flush()
    db_session.add_all(
        [
            *[
                _payment(invoice, Decimal("100.00"), event_date)
                for invoice, event_date in zip(invoices, event_dates)
            ],
            _payment(outside_invoice, Decimal("900.00"), event_dates[3]),
        ]
    )
    await db_session.flush()

    expected = {
        AnalyticsPeriod.TODAY: (2, 1, Decimal("100.00"), [3]),
        AnalyticsPeriod.WEEK: (4, 3, Decimal("300.00"), [2, 3, 4]),
        AnalyticsPeriod.MONTH: (6, 5, Decimal("500.00"), [1, 2, 3, 4, 5]),
        AnalyticsPeriod.YEAR: (8, 7, Decimal("700.00"), [0, 1, 2, 3, 4, 5, 6]),
    }
    for period, (
        appointment_count,
        patient_count,
        revenue,
        patient_revenue_indexes,
    ) in expected.items():
        response = await client.get(
            f"{settings.API_V1_PREFIX}/analytics/overview?period={period.value}&patient_revenue_limit=100",
            headers=auth_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["meta"]["period"] == period.value
        selected_range = AnalyticsPeriods.containing(FROZEN_NOW).for_period(period)
        assert (
            datetime.fromisoformat(payload["meta"]["start"].replace("Z", "+00:00"))
            == selected_range.start
        )
        assert (
            datetime.fromisoformat(payload["meta"]["end"].replace("Z", "+00:00"))
            == selected_range.end
        )
        assert (
            payload["data"]["appointments"]["appointments_in_period"]
            == appointment_count
        )
        assert payload["data"]["patients"]["new_patients_in_period"] == patient_count
        financial_data = payload["data"]["revenue"]
        assert Decimal(str(financial_data["billed_amount_in_period"])) == revenue
        assert Decimal(str(financial_data["collected_amount_in_period"])) == revenue
        assert Decimal(str(financial_data["revenue_in_period"])) == revenue
        patient_revenue = payload["data"]["patient_revenue"]
        assert payload["data"]["patient_revenue_sort"] == "collected_amount"
        assert {item["patient_id"] for item in patient_revenue} == {
            str(patients[index].id) for index in patient_revenue_indexes
        }
        assert all(
            Decimal(str(item["billed_amount"])) == Decimal("100.00")
            and Decimal(str(item["collected_amount"])) == Decimal("100.00")
            for item in patient_revenue
        )

    default_response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview", headers=auth_headers
    )
    default_payload = default_response.json()
    assert default_payload["meta"]["period"] == AnalyticsPeriod.MONTH.value
    assert default_payload["data"]["patients"]["new_patients_this_month"] == 5
    assert default_payload["data"]["patients"]["new_patients_in_period"] == 5
    assert default_payload["data"]["revenue"]["revenue_this_month"] == "500.00"
    assert default_payload["data"]["revenue"]["revenue_in_period"] == "500.00"
    assert default_payload["data"]["revenue"]["billed_amount_in_period"] == "500.00"
    assert default_payload["data"]["revenue"]["collected_amount_in_period"] == "500.00"

    default_limit_response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview?period=year",
        headers=auth_headers,
    )
    default_limit_data = default_limit_response.json()["data"]
    assert default_limit_response.status_code == 200
    assert default_limit_data["patient_revenue_sort"] == "collected_amount"
    assert len(default_limit_data["patient_revenue"]) == 5

    ranked_patients_response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview?period=month&patient_revenue_sort=billed_amount&patient_revenue_limit=1",
        headers=auth_headers,
    )
    assert ranked_patients_response.status_code == 200
    ranked_patients_payload = ranked_patients_response.json()["data"]
    assert ranked_patients_payload["patient_revenue_sort"] == "billed_amount"
    assert len(ranked_patients_payload["patient_revenue"]) == 1
    assert set(ranked_patients_payload["patient_revenue"][0]) == {
        "patient_id",
        "patient_name",
        "billed_amount",
        "collected_amount",
    }

    excessive_limit_response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview?patient_revenue_limit=101",
        headers=auth_headers,
    )
    assert excessive_limit_response.status_code == 422
    zero_limit_response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview?patient_revenue_limit=0",
        headers=auth_headers,
    )
    assert zero_limit_response.status_code == 422

    today_performance = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/my-performance?period=today",
        headers=auth_headers,
    )
    month_performance = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/my-performance?period=month",
        headers=auth_headers,
    )
    week_performance = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/my-performance?period=week",
        headers=auth_headers,
    )
    year_performance = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/my-performance?period=year",
        headers=auth_headers,
    )
    assert all(
        response.status_code == 200
        for response in (
            today_performance,
            week_performance,
            month_performance,
            year_performance,
        )
    )
    today_data = today_performance.json()["data"]
    month_data = month_performance.json()["data"]
    week_data = week_performance.json()["data"]
    year_data = year_performance.json()["data"]
    assert today_performance.json()["meta"]["period"] == "today"
    assert today_data["appointments_in_period"] == 1
    assert today_data["completed_appointments_in_period"] == 1
    assert today_data["treatment_sessions_in_period"] == 1
    assert today_data["soap_notes_in_period"] == 1
    assert today_data["patients_seen_in_period"] == 1
    assert week_performance.json()["meta"]["period"] == "week"
    assert week_data["appointments_in_period"] == 3
    assert week_data["completed_appointments_in_period"] == 1
    assert week_data["cancelled_appointments_in_period"] == 1
    assert week_data["treatment_sessions_in_period"] == 2
    assert week_data["soap_notes_in_period"] == 2
    assert week_data["patients_seen_in_period"] == 1
    assert month_performance.json()["meta"]["period"] == "month"
    assert month_data["appointments_in_period"] == 5
    assert month_data["completed_appointments_in_period"] == 1
    assert month_data["cancelled_appointments_in_period"] == 1
    assert month_data["treatment_sessions_in_period"] == 2
    assert month_data["soap_notes_in_period"] == 2
    assert month_data["patients_seen_in_period"] == 1
    assert year_performance.json()["meta"]["period"] == "year"
    assert year_data["appointments_in_period"] == 7
    assert year_data["completed_appointments_in_period"] == 1
    assert year_data["cancelled_appointments_in_period"] == 1
    assert year_data["treatment_sessions_in_period"] == 2
    assert year_data["soap_notes_in_period"] == 2
    assert year_data["patients_seen_in_period"] == 1
    invalid_performance_response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/my-performance?period=decade",
        headers=auth_headers,
    )
    assert invalid_performance_response.status_code == 422

    invalid_response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview?period=decade",
        headers=auth_headers,
    )
    assert invalid_response.status_code == 422

    openapi = app.openapi()
    overview_parameters = openapi["paths"]["/api/v1/analytics/overview"]["get"][
        "parameters"
    ]
    period_parameter = next(
        item for item in overview_parameters if item["name"] == "period"
    )
    period_schema_ref = period_parameter["schema"]["$ref"].rsplit("/", 1)[-1]
    assert openapi["components"]["schemas"][period_schema_ref]["enum"] == [
        "today",
        "week",
        "month",
        "year",
    ]
    assert period_parameter["schema"]["default"] == "month"
