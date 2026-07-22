from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.enums.patient import PatientStatus
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.patient import PatientNotFoundError, PatientService, PatientValidationError


@pytest.mark.asyncio
async def test_create_patient_success() -> None:
    """Test successful patient creation with whitespace trimming."""

    mock_repo = AsyncMock()
    clinic_id = uuid4()
    mock_patient = Patient(
        id=uuid4(),
        clinic_id=clinic_id,
        full_name="Alice Smith",
        phone="+1987654321",
        status=PatientStatus.ACTIVE,
    )
    mock_repo.create.return_value = mock_patient

    service = PatientService(mock_repo)
    payload = PatientCreate(full_name="   Alice Smith   ", phone="+1987654321")

    result = await service.create_patient(clinic_id, payload)
    assert result.full_name == "Alice Smith"
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_patient_validation_error() -> None:
    """Test validation error when creating patient with empty name."""

    mock_repo = AsyncMock()
    service = PatientService(mock_repo)
    payload = PatientCreate(full_name="    ")

    with pytest.raises(PatientValidationError, match="cannot be empty"):
        await service.create_patient(uuid4(), payload)


@pytest.mark.asyncio
async def test_get_patient_not_found() -> None:
    """Test PatientNotFoundError raised when patient ID does not exist."""

    mock_repo = AsyncMock()
    mock_repo.get_by_patient_id.return_value = None
    service = PatientService(mock_repo)

    patient_id = uuid4()
    clinic_id = uuid4()

    with pytest.raises(PatientNotFoundError, match=f"Patient '{patient_id}' not found"):
        await service.get_patient(clinic_id, patient_id)


@pytest.mark.asyncio
async def test_update_patient_success() -> None:
    """Test updating patient fields."""

    mock_repo = AsyncMock()
    clinic_id = uuid4()
    patient_id = uuid4()

    existing_patient = Patient(
        id=patient_id,
        clinic_id=clinic_id,
        full_name="Bob Jones",
        status=PatientStatus.ACTIVE,
    )
    mock_repo.get_by_patient_id.return_value = existing_patient
    mock_repo.update.return_value = existing_patient

    service = PatientService(mock_repo)
    payload = PatientUpdate(full_name="Bob Brown", status=PatientStatus.INACTIVE)

    updated = await service.update_patient(clinic_id, patient_id, payload)
    assert updated is not None
    mock_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_patient_success() -> None:
    """Test deleting patient record."""

    mock_repo = AsyncMock()
    clinic_id = uuid4()
    patient_id = uuid4()

    existing_patient = Patient(id=patient_id, clinic_id=clinic_id, full_name="Charlie")
    mock_repo.get_by_patient_id.return_value = existing_patient

    service = PatientService(mock_repo)
    await service.delete_patient(clinic_id, patient_id)
    mock_repo.delete.assert_awaited_once_with(existing_patient)


@pytest.mark.asyncio
async def test_search_patients_routing() -> None:
    """Test search_patients routes numeric query to phone search and alpha query to name search."""

    mock_repo = AsyncMock()
    service = PatientService(mock_repo)
    clinic_id = uuid4()

    mock_repo.search_by_phone.return_value = []
    await service.search_patients(clinic_id, query="12345")
    mock_repo.search_by_phone.assert_awaited_once()

    mock_repo.search_by_name.return_value = []
    await service.search_patients(clinic_id, query="John")
    mock_repo.search_by_name.assert_awaited_once()
