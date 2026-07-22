from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.leads import get_lead_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.lead import LeadStage
from app.enums.patient import PatientStatus
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.lead import Lead
from app.models.patient import Patient
from app.models.user import User
from app.services.lead import LeadNotFoundError, LeadValidationError


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
def mock_lead(mock_clinic: Clinic, mock_user: User) -> Lead:
    now = datetime.now(timezone.utc)
    return Lead(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Alice Smith",
        phone="+1987654321",
        email="alice@example.com",
        source="google",
        stage=LeadStage.NEW,
        assigned_to=mock_user.id,
        notes="Interested in knee therapy",
        converted_patient_id=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_converted_lead(mock_clinic: Clinic, mock_user: User) -> tuple[Lead, Patient]:
    now = datetime.now(timezone.utc)
    patient_id = uuid4()
    lead = Lead(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Alice Smith",
        phone="+1987654321",
        email="alice@example.com",
        source="google",
        stage=LeadStage.CONVERTED,
        assigned_to=mock_user.id,
        notes="Interested in knee therapy",
        converted_patient_id=patient_id,
        created_at=now,
        updated_at=now,
    )
    patient = Patient(
        id=patient_id,
        clinic_id=mock_clinic.id,
        full_name="Alice Smith",
        phone="+1987654321",
        status=PatientStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    return lead, patient


@pytest.fixture
def mock_lead_service() -> AsyncMock:
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


# --- Lead API Tests ---

@pytest.mark.asyncio
async def test_create_lead_api_success(
    mock_clinic: Clinic, mock_lead: Lead, mock_lead_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/leads creates a new sales lead."""

    mock_lead_service.create_lead.return_value = mock_lead
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/leads",
            json={
                "name": "Alice Smith",
                "phone": "+1987654321",
                "email": "alice@example.com",
                "source": "google",
                "stage": "new",
                "notes": "Interested in knee therapy",
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice Smith"
    assert data["clinic_id"] == str(mock_clinic.id)


@pytest.mark.asyncio
async def test_get_lead_api_success(
    mock_clinic: Clinic, mock_lead: Lead, mock_lead_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/leads/{id} returns lead details."""

    mock_lead_service.get_lead.return_value = mock_lead
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/leads/{mock_lead.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_lead.id)


@pytest.mark.asyncio
async def test_list_leads_api_success(
    mock_clinic: Clinic, mock_lead: Lead, mock_lead_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/leads returns paginated and filtered leads."""

    mock_lead_service.list_leads.return_value = [mock_lead]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/leads?stage=new&source=google&offset=0&limit=10", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(mock_lead.id)


@pytest.mark.asyncio
async def test_patch_lead_api_success(
    mock_clinic: Clinic, mock_lead: Lead, mock_lead_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test PATCH /api/v1/leads/{id} updates lead stage and details."""

    mock_lead_service.update_lead.return_value = mock_lead
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/leads/{mock_lead.id}",
            json={"stage": "contacted", "notes": "Called, follow up next week"},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_lead.id)


@pytest.mark.asyncio
async def test_convert_lead_api_success(
    mock_clinic: Clinic,
    mock_converted_lead: tuple[Lead, Patient],
    mock_lead_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /api/v1/leads/{id}/convert converts lead to patient."""

    lead, patient = mock_converted_lead
    mock_lead_service.convert_lead_to_patient.return_value = (lead, patient)
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/leads/{lead.id}/convert", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == str(patient.id)
    assert data["lead"]["stage"] == "converted"


@pytest.mark.asyncio
async def test_convert_lead_duplicate_rejection(
    mock_clinic: Clinic, mock_lead_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/leads/{id}/convert returns 400 when lead is already converted."""

    lead_id = uuid4()
    mock_lead_service.convert_lead_to_patient.side_effect = LeadValidationError("Lead has already been converted")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/leads/{lead_id}/convert", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Lead has already been converted"


@pytest.mark.asyncio
async def test_delete_lead_api_success(
    mock_clinic: Clinic, mock_lead_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test DELETE /api/v1/leads/{id} deletes lead record."""

    lead_id = uuid4()
    mock_lead_service.delete_lead.return_value = None
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/leads/{lead_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_lead_not_found(
    mock_clinic: Clinic, mock_lead_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/leads/{id} returns 404 when lead is missing."""

    lead_id = uuid4()
    mock_lead_service.get_lead.side_effect = LeadNotFoundError("Lead not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_lead_service] = lambda: mock_lead_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404
