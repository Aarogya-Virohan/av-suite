from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.enums.appointment import AppointmentSource, AppointmentStatus
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.appointment import (
    AppointmentNotFoundError,
    AppointmentService,
    AppointmentValidationError,
)


@pytest.mark.asyncio
async def test_create_appointment_success() -> None:
    """Test creating an appointment with valid patient, therapist, and duration."""

    mock_appt_repo = AsyncMock()
    mock_patient_repo = AsyncMock()
    mock_user_repo = AsyncMock()

    clinic_id = uuid4()
    patient_id = uuid4()
    therapist_id = uuid4()

    mock_patient = Patient(id=patient_id, clinic_id=clinic_id, full_name="John Doe")
    mock_therapist = User(id=therapist_id, clinic_id=clinic_id, name="Dr. Smith")
    mock_appt = Appointment(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        therapist_id=therapist_id,
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        source=AppointmentSource.MANUAL,
    )

    mock_patient_repo.get_by_patient_id.return_value = mock_patient
    mock_user_repo.get_by_id.return_value = mock_therapist
    mock_appt_repo.create.return_value = mock_appt

    service = AppointmentService(mock_appt_repo, mock_patient_repo, mock_user_repo)
    payload = AppointmentCreate(
        patient_id=patient_id,
        therapist_id=therapist_id,
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
    )

    result = await service.create_appointment(clinic_id, payload)
    assert result.duration_minutes == 30
    mock_appt_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_appointment_invalid_duration() -> None:
    """Test duration_minutes <= 0 raises AppointmentValidationError."""

    service = AppointmentService(AsyncMock(), AsyncMock(), AsyncMock())
    payload = AppointmentCreate.model_construct(
        patient_id=uuid4(),
        therapist_id=uuid4(),
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=0,
    )


    with pytest.raises(AppointmentValidationError, match="duration_minutes must be greater than 0"):
        await service.create_appointment(uuid4(), payload)


@pytest.mark.asyncio
async def test_create_appointment_patient_not_found() -> None:
    """Test creating appointment with non-existent patient raises AppointmentValidationError."""

    mock_patient_repo = AsyncMock()
    mock_patient_repo.get_by_patient_id.return_value = None

    service = AppointmentService(AsyncMock(), mock_patient_repo, AsyncMock())
    payload = AppointmentCreate(
        patient_id=uuid4(),
        therapist_id=uuid4(),
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
    )

    with pytest.raises(AppointmentValidationError, match="Patient .* does not exist"):
        await service.create_appointment(uuid4(), payload)


@pytest.mark.asyncio
async def test_create_appointment_therapist_not_found() -> None:
    """Test creating appointment with non-existent therapist raises AppointmentValidationError."""

    clinic_id = uuid4()
    mock_patient_repo = AsyncMock()
    mock_user_repo = AsyncMock()

    mock_patient_repo.get_by_patient_id.return_value = Patient(id=uuid4(), clinic_id=clinic_id)
    mock_user_repo.get_by_id.return_value = None

    service = AppointmentService(AsyncMock(), mock_patient_repo, mock_user_repo)
    payload = AppointmentCreate(
        patient_id=uuid4(),
        therapist_id=uuid4(),
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
    )

    with pytest.raises(AppointmentValidationError, match="Therapist .* does not exist"):
        await service.create_appointment(clinic_id, payload)


@pytest.mark.asyncio
async def test_get_appointment_not_found() -> None:
    """Test get_appointment raises AppointmentNotFoundError when appointment missing."""

    mock_appt_repo = AsyncMock()
    mock_appt_repo.get_by_id.return_value = None

    service = AppointmentService(mock_appt_repo, AsyncMock(), AsyncMock())
    appt_id = uuid4()
    clinic_id = uuid4()

    with pytest.raises(AppointmentNotFoundError, match=f"Appointment '{appt_id}' not found"):
        await service.get_appointment(clinic_id, appt_id)


@pytest.mark.asyncio
async def test_list_appointments_filters() -> None:
    """Test listing appointments with filtering options."""

    mock_appt_repo = AsyncMock()
    mock_appt_repo.list_appointments.return_value = []

    service = AppointmentService(mock_appt_repo, AsyncMock(), AsyncMock())
    clinic_id = uuid4()
    p_id = uuid4()
    t_id = uuid4()
    t_date = date(2026, 7, 22)

    await service.list_appointments(
        clinic_id, scheduled_date=t_date, patient_id=p_id, therapist_id=t_id
    )
    mock_appt_repo.list_appointments.assert_awaited_once_with(
        clinic_id=clinic_id,
        scheduled_date=t_date,
        patient_id=p_id,
        therapist_id=t_id,
        status=None,
        offset=0,
        limit=100,
    )


@pytest.mark.asyncio
async def test_update_appointment_success() -> None:
    """Test updating appointment fields."""

    mock_appt_repo = AsyncMock()
    mock_patient_repo = AsyncMock()
    mock_user_repo = AsyncMock()

    clinic_id = uuid4()
    appt_id = uuid4()

    existing_appt = Appointment(id=appt_id, clinic_id=clinic_id, duration_minutes=30)
    mock_appt_repo.get_by_id.return_value = existing_appt
    mock_appt_repo.update.return_value = existing_appt

    service = AppointmentService(mock_appt_repo, mock_patient_repo, mock_user_repo)
    payload = AppointmentUpdate(duration_minutes=45)

    updated = await service.update_appointment(clinic_id, appt_id, payload)
    assert updated is not None
    mock_appt_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_soft_cancel_appointment_success() -> None:
    """Test soft-cancelling an appointment."""

    mock_appt_repo = AsyncMock()
    clinic_id = uuid4()
    appt_id = uuid4()

    existing_appt = Appointment(id=appt_id, clinic_id=clinic_id, status=AppointmentStatus.SCHEDULED)
    mock_appt_repo.get_by_id.return_value = existing_appt
    mock_appt_repo.soft_cancel.return_value = existing_appt

    service = AppointmentService(mock_appt_repo, AsyncMock(), AsyncMock())
    await service.soft_cancel(clinic_id, appt_id)
    mock_appt_repo.soft_cancel.assert_awaited_once_with(existing_appt)
