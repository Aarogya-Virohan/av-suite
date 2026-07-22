from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.patients import get_patient_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.patient import PatientStatus
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.services.patient import PatientNotFoundError


@pytest.fixture
def mock_clinic() -> Clinic:
    return Clinic(id=uuid4(), name="Test Clinic")


@pytest.fixture
def mock_user(mock_clinic: Clinic) -> User:
    return User(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Test User",
        email="test@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest.fixture
def mock_patient(mock_clinic: Clinic) -> Patient:
    now = datetime.now(timezone.utc)
    return Patient(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        full_name="Jane Doe",
        phone="+1234567890",
        age=30,
        gender="female",
        chief_complaint="Lower back pain",
        referral_source="Google",
        status=PatientStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_patient_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_clinic_gate(mock_clinic: Clinic, mock_user: User):
    auth_ctx = AuthenticatedContext(user=mock_user, clinic=mock_clinic)
    with patch.object(ClinicGateMiddleware, "_resolve_context", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = auth_ctx
        yield mock_resolve


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer mock-test-token"}


@pytest.mark.asyncio
async def test_create_patient_api_success(
    mock_clinic: Clinic, mock_patient: Patient, mock_patient_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/patients creates a patient successfully."""

    mock_patient_service.create_patient.return_value = mock_patient
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_patient_service] = lambda: mock_patient_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/patients",
            json={
                "full_name": "Jane Doe",
                "phone": "+1234567890",
                "age": 30,
                "gender": "female",
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Jane Doe"
    assert data["clinic_id"] == str(mock_clinic.id)


@pytest.mark.asyncio
async def test_get_patient_by_id_api_success(
    mock_clinic: Clinic, mock_patient: Patient, mock_patient_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/patients/{id} returns patient detail."""

    mock_patient_service.get_patient.return_value = mock_patient
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_patient_service] = lambda: mock_patient_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/patients/{mock_patient.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(mock_patient.id)


@pytest.mark.asyncio
async def test_get_patient_by_id_api_not_found(
    mock_clinic: Clinic, mock_patient_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/patients/{id} returns 404 when patient does not exist."""

    patient_id = uuid4()
    mock_patient_service.get_patient.side_effect = PatientNotFoundError("Not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_patient_service] = lambda: mock_patient_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/patients/{patient_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"


@pytest.mark.asyncio
async def test_list_patients_api_success(
    mock_clinic: Clinic, mock_patient: Patient, mock_patient_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/patients returns paginated patient list."""

    mock_patient_service.list_patients.return_value = [mock_patient]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_patient_service] = lambda: mock_patient_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/patients?offset=0&limit=10", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["full_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_patch_patient_api_success(
    mock_clinic: Clinic, mock_patient: Patient, mock_patient_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test PATCH /api/v1/patients/{id} updates patient successfully."""

    mock_patient_service.update_patient.return_value = mock_patient
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_patient_service] = lambda: mock_patient_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/patients/{mock_patient.id}",
            json={"phone": "+9999999999"},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_patient.id)


@pytest.mark.asyncio
async def test_delete_patient_api_success(
    mock_clinic: Clinic, mock_patient: Patient, mock_patient_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test DELETE /api/v1/patients/{id} deletes patient successfully."""

    mock_patient_service.delete_patient.return_value = None
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_patient_service] = lambda: mock_patient_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/patients/{mock_patient.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 204
