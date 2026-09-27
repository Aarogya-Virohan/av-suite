from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.appointment import AppointmentStatus
from app.enums.billing import InvoiceStatus
from app.enums.shared import Specialty
from app.enums.user import UserRole
from app.models.appointment import Appointment
from app.models.billing import Invoice
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.treatment import SoapAssessment, TreatmentSession
from app.models.user import User
from app.repositories.analytics import AnalyticsRepository
from app.utils.analytics_periods import AnalyticsPeriods

UTC = timezone.utc
MONTH = AnalyticsPeriods.containing(datetime(2024, 3, 6, 12, tzinfo=UTC)).this_month
TODAY = AnalyticsPeriods.containing(datetime(2024, 3, 6, 12, tzinfo=UTC)).today
WEEK = AnalyticsPeriods.containing(datetime(2024, 3, 6, 12, tzinfo=UTC)).this_week


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

    repository = AnalyticsRepository(db_session)
    appointments_result = await repository.get_appointment_stats(clinic.id, TODAY, WEEK)
    patients_result = await repository.get_patient_stats(clinic.id, MONTH)
    revenue_result = await repository.get_revenue_stats(clinic.id, MONTH)

    assert appointments_result.today_appointments == 1
    assert appointments_result.this_week_appointments == 4
    assert (
        appointments_result.this_week_appointments
        != appointments_result.today_appointments
    )
    assert appointments_result.completed_appointments == 1
    assert patients_result.new_patients_this_month == 2
    assert revenue_result.revenue_this_month == Decimal("20.00")


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
        clinic.id, therapist.id, MONTH, TODAY
    )

    assert result.today_appointments == 1
    assert result.completed_appointments_this_month == 2
    assert result.cancelled_appointments_this_month == 1
    assert result.treatment_sessions_this_month == 1
    assert result.soap_notes_this_month == 1
    assert result.patients_seen_this_month == 1
