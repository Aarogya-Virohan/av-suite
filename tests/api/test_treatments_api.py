from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.treatments import get_treatment_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.treatment import TreatmentSession
from app.models.user import User
from app.services.treatment import TreatmentNotFoundError


@pytest.fixture
def mock_clinic() -> Clinic:
    return Clinic(id=uuid4(), name="Test Clinic")


@pytest.fixture
def mock_user(mock_clinic: Clinic) -> User:
    return User(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Test Therapist",
        email="therapist@example.com",
        role=UserRole.THERAPIST,
        is_active=True,
    )


@pytest.fixture
def mock_treatment_session(mock_clinic: Clinic) -> TreatmentSession:
    now = datetime.now(timezone.utc)
    return TreatmentSession(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        patient_id=uuid4(),
        therapist_id=uuid4(),
        treatment_date=now,
        pain_score=4,
        treatment="Myofascial release",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_treatment_service() -> AsyncMock:
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
async def test_create_treatment_session_api(
    mock_clinic: Clinic,
    mock_treatment_session: TreatmentSession,
    mock_treatment_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /api/v1/treatments creates a session successfully."""

    mock_treatment_service.create_session.return_value = mock_treatment_session
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_treatment_service] = lambda: mock_treatment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/treatments",
            json={
                "patient_id": str(mock_treatment_session.patient_id),
                "therapist_id": str(mock_treatment_session.therapist_id),
                "treatment_date": mock_treatment_session.treatment_date.isoformat(),
                "pain_score": 4,
                "treatment": "Myofascial release",
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["treatment"] == "Myofascial release"


@pytest.mark.asyncio
async def test_list_treatment_sessions_api(
    mock_clinic: Clinic,
    mock_treatment_session: TreatmentSession,
    mock_treatment_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/treatments lists sessions with filters."""

    mock_treatment_service.list_sessions.return_value = [mock_treatment_session]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_treatment_service] = lambda: mock_treatment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/treatments?patient_id={mock_treatment_session.patient_id}",
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_treatment_session_by_id_not_found(
    mock_clinic: Clinic,
    mock_treatment_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/treatments/{id} returns 404 when missing."""

    session_id = uuid4()
    mock_treatment_service.get_session.side_effect = TreatmentNotFoundError("Not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_treatment_service] = lambda: mock_treatment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/treatments/{session_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_treatment_session_api(
    mock_clinic: Clinic,
    mock_treatment_session: TreatmentSession,
    mock_treatment_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test DELETE /api/v1/treatments/{id} deletes session."""

    mock_treatment_service.delete_session.return_value = None
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_treatment_service] = lambda: mock_treatment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/treatments/{mock_treatment_session.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 204
