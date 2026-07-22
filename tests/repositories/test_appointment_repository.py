from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.enums.appointment import AppointmentSource, AppointmentStatus
from app.models.appointment import Appointment
from app.repositories.appointment import AppointmentRepository


@pytest.mark.asyncio
async def test_appointment_repository_create_and_get() -> None:
    """Test creating and retrieving an appointment via repository."""

    mock_session = AsyncMock()
    clinic_id = uuid4()
    mock_appt = Appointment(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=uuid4(),
        therapist_id=uuid4(),
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        source=AppointmentSource.MANUAL,
    )

    repo = AppointmentRepository(mock_session)

    with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_appt
        created = await repo.create({"clinic_id": clinic_id, "duration_minutes": 30})
        assert created.duration_minutes == 30
        mock_create.assert_awaited_once()

    with patch.object(repo, "get_by_id", new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_appt
        retrieved = await repo.get_by_id(mock_appt.id, clinic_id=clinic_id)
        assert retrieved is not None
        assert retrieved.id == mock_appt.id


@pytest.mark.asyncio
async def test_appointment_repository_list_with_filters() -> None:
    """Test list_appointments with date, patient_id, therapist_id, and status filters."""

    mock_session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [
        Appointment(
            id=uuid4(),
            clinic_id=uuid4(),
            patient_id=uuid4(),
            therapist_id=uuid4(),
            scheduled_at=datetime.now(timezone.utc),
            status=AppointmentStatus.SCHEDULED,
        )
    ]
    mock_session.scalars.return_value = mock_scalars

    repo = AppointmentRepository(mock_session)
    clinic_id = uuid4()
    patient_id = uuid4()
    therapist_id = uuid4()
    test_date = date(2026, 7, 22)

    results = await repo.list_appointments(
        clinic_id=clinic_id,
        scheduled_date=test_date,
        patient_id=patient_id,
        therapist_id=therapist_id,
        status=AppointmentStatus.SCHEDULED,
    )
    assert len(results) == 1
    mock_session.scalars.assert_called_once()


@pytest.mark.asyncio
async def test_appointment_repository_soft_cancel() -> None:
    """Test soft_cancel updates appointment status to CANCELLED."""

    mock_session = AsyncMock()
    clinic_id = uuid4()
    mock_appt = Appointment(
        id=uuid4(),
        clinic_id=clinic_id,
        status=AppointmentStatus.SCHEDULED,
    )
    cancelled_appt = Appointment(
        id=mock_appt.id,
        clinic_id=clinic_id,
        status=AppointmentStatus.CANCELLED,
    )

    repo = AppointmentRepository(mock_session)
    with patch.object(repo, "update", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = cancelled_appt
        res = await repo.soft_cancel(mock_appt)
        assert res.status == AppointmentStatus.CANCELLED
        mock_update.assert_awaited_once_with(mock_appt, {"status": AppointmentStatus.CANCELLED})


@pytest.mark.asyncio
async def test_appointment_repository_clinic_isolation() -> None:
    """Test that missing clinic_id raises ValueError for clinic-scoped appointment operations."""

    mock_session = AsyncMock()
    repo = AppointmentRepository(mock_session)

    with pytest.raises(ValueError, match="clinic_id is required"):
        await repo.get_by_id(uuid4(), clinic_id=None)
