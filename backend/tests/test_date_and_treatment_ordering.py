from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.enums.shared import Specialty
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.treatment import SoapAssessment, TreatmentSession
from app.models.user import User
from app.repositories.appointment import AppointmentRepository
from app.repositories.treatment import SoapAssessmentRepository, TreatmentSessionRepository


async def _context(db_session):
    clinic = (await db_session.scalars(select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic"))).one()
    therapist = (await db_session.scalars(select(User).where(User.email == "therapist@avtest.com"))).one()
    patient = Patient(
        id=uuid4(), clinic_id=clinic.id, first_name="Date", last_name="Range",
        phone=f"9{uuid4().int % 10**9:09d}", gender="male",
        date_of_birth=date(1990, 1, 1),
    )
    db_session.add(patient)
    await db_session.flush()
    return clinic, therapist, patient


@pytest.mark.asyncio
async def test_appointment_date_filter_uses_ist_day_and_inclusive_date_range(db_session):
    clinic, therapist, patient = await _context(db_session)
    ids = [uuid4() for _ in range(4)]
    # 2026-10-15 in India spans [2026-10-14 18:30Z, 2026-10-15 18:30Z).
    appointments = [
        Appointment(id=ids[0], clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                    scheduled_at=datetime(2026, 10, 14, 18, 30, tzinfo=timezone.utc), duration_minutes=30),
        Appointment(id=ids[1], clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                    scheduled_at=datetime(2026, 10, 15, 18, 29, 59, tzinfo=timezone.utc), duration_minutes=30),
        Appointment(id=ids[2], clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                    scheduled_at=datetime(2026, 10, 15, 18, 30, tzinfo=timezone.utc), duration_minutes=30),
        Appointment(id=ids[3], clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                    scheduled_at=datetime(2026, 10, 14, 18, 29, 59, tzinfo=timezone.utc), duration_minutes=30),
    ]
    db_session.add_all(appointments)
    await db_session.flush()

    repo = AppointmentRepository(db_session)
    day_rows = await repo.list_appointments(clinic_id=clinic.id, scheduled_date=date(2026, 10, 15))
    assert {row.id for row in day_rows} == {ids[0], ids[1]}

    inclusive_rows = await repo.list_appointments(
        clinic_id=clinic.id, start_date=date(2026, 10, 15), end_date=date(2026, 10, 15)
    )
    assert {row.id for row in inclusive_rows} == {ids[0], ids[1]}


@pytest.mark.asyncio
async def test_appointment_order_is_scheduled_at_then_id(db_session):
    clinic, therapist, patient = await _context(db_session)
    timestamp = datetime(2026, 10, 15, 8, tzinfo=timezone.utc)
    lower_id, higher_id = sorted((uuid4(), uuid4()))
    later_time_id = uuid4()
    db_session.add_all([
        Appointment(id=higher_id, clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                    scheduled_at=timestamp, duration_minutes=30),
        Appointment(id=lower_id, clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                    scheduled_at=timestamp, duration_minutes=30),
        Appointment(id=later_time_id, clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                    scheduled_at=timestamp.replace(hour=9), duration_minutes=30),
    ])
    await db_session.flush()

    rows = await AppointmentRepository(db_session).list_appointments(clinic_id=clinic.id, patient_id=patient.id)
    assert [row.id for row in rows] == [lower_id, higher_id, later_time_id]


@pytest.mark.asyncio
async def test_treatment_sessions_order_by_treatment_date_then_created_at(db_session):
    clinic, therapist, patient = await _context(db_session)
    older_created, newer_created = datetime(2026, 10, 1, tzinfo=timezone.utc), datetime(2026, 10, 2, tzinfo=timezone.utc)
    same_day = datetime(2026, 10, 10, tzinfo=timezone.utc)
    ids = [uuid4(), uuid4(), uuid4()]
    db_session.add_all([
        TreatmentSession(id=ids[0], clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                         treatment_date=same_day, created_at=older_created, updated_at=older_created, treatment="one"),
        TreatmentSession(id=ids[1], clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                         treatment_date=same_day, created_at=newer_created, updated_at=newer_created, treatment="two"),
        TreatmentSession(id=ids[2], clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                         treatment_date=datetime(2026, 10, 11, tzinfo=timezone.utc), created_at=older_created,
                         updated_at=older_created, treatment="three"),
    ])
    await db_session.flush()

    rows = await TreatmentSessionRepository(db_session).list_sessions(clinic_id=clinic.id, patient_id=patient.id)
    assert [row.id for row in rows] == [ids[2], ids[1], ids[0]]


@pytest.mark.asyncio
async def test_assessments_order_by_created_at_desc(db_session):
    clinic, therapist, patient = await _context(db_session)
    created = [datetime(2026, 10, day, tzinfo=timezone.utc) for day in (1, 3, 2)]
    ids = [uuid4() for _ in created]
    db_session.add_all([
        SoapAssessment(id=item_id, clinic_id=clinic.id, patient_id=patient.id, therapist_id=therapist.id,
                       specialty=Specialty.PHYSIOTHERAPY, form_data={}, created_at=created_at, updated_at=created_at)
        for item_id, created_at in zip(ids, created)
    ])
    await db_session.flush()

    rows = await SoapAssessmentRepository(db_session).list_assessments(clinic_id=clinic.id, patient_id=patient.id)
    assert [row.id for row in rows] == [ids[1], ids[2], ids[0]]
