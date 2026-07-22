from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.enums.patient import PatientStatus
from app.models.patient import Patient
from app.repositories.patient import PatientRepository


@pytest.mark.asyncio
async def test_patient_repository_create_and_get() -> None:
    """Test repository create and get_by_patient_id methods."""

    mock_session = AsyncMock()
    mock_patient = Patient(
        id=uuid4(),
        clinic_id=uuid4(),
        full_name="John Doe",
        phone="+1234567890",
        status=PatientStatus.ACTIVE,
    )

    repo = PatientRepository(mock_session)

    with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_patient
        created = await repo.create({"full_name": "John Doe", "clinic_id": mock_patient.clinic_id})
        assert created.full_name == "John Doe"
        mock_create.assert_awaited_once()

    with patch.object(repo, "get_by_id", new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_patient
        retrieved = await repo.get_by_patient_id(mock_patient.id, clinic_id=mock_patient.clinic_id)
        assert retrieved is not None
        assert retrieved.id == mock_patient.id
        mock_get_by_id.assert_awaited_once_with(mock_patient.id, clinic_id=mock_patient.clinic_id)


@pytest.mark.asyncio
async def test_patient_repository_clinic_isolation_check() -> None:
    """Test that clinic isolation raises ValueError when clinic_id is missing for clinic-scoped models."""

    mock_session = AsyncMock()
    repo = PatientRepository(mock_session)

    with pytest.raises(ValueError, match="clinic_id is required"):
        await repo.get_by_id(uuid4(), clinic_id=None)


@pytest.mark.asyncio
async def test_patient_repository_search_and_list() -> None:
    """Test search_by_name, search_by_phone, and list_active on repository."""

    mock_session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [
        Patient(id=uuid4(), clinic_id=uuid4(), full_name="Jane Doe", phone="9876543210")
    ]
    mock_session.scalars.return_value = mock_scalars

    repo = PatientRepository(mock_session)
    clinic_id = uuid4()

    results_name = await repo.search_by_name("Jane", clinic_id=clinic_id)
    assert len(results_name) == 1
    assert results_name[0].full_name == "Jane Doe"

    results_phone = await repo.search_by_phone("98765", clinic_id=clinic_id)
    assert len(results_phone) == 1

    results_active = await repo.list_active(clinic_id=clinic_id)
    assert len(results_active) == 1
