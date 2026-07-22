from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.assessments import get_assessment_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.treatment import SoapAssessment
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
def mock_soap_assessment(mock_clinic: Clinic) -> SoapAssessment:
    now = datetime.now(timezone.utc)
    return SoapAssessment(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        patient_id=uuid4(),
        specialty="physiotherapy",
        diagnosis="Lumbar strain",
        is_reassessment=False,
        form_data={"subjective": "Lower back pain"},
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_assessment_service() -> AsyncMock:
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
async def test_create_soap_assessment_api(
    mock_clinic: Clinic,
    mock_soap_assessment: SoapAssessment,
    mock_assessment_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /api/v1/assessments creates a SOAP assessment."""

    mock_assessment_service.create_assessment.return_value = mock_soap_assessment
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_assessment_service] = lambda: mock_assessment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/assessments",
            json={
                "patient_id": str(mock_soap_assessment.patient_id),
                "specialty": "physiotherapy",
                "diagnosis": "Lumbar strain",
                "form_data": {"subjective": "Lower back pain"},
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["specialty"] == "physiotherapy"


@pytest.mark.asyncio
async def test_list_soap_assessments_api(
    mock_clinic: Clinic,
    mock_soap_assessment: SoapAssessment,
    mock_assessment_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/assessments lists SOAP assessments with filters."""

    mock_assessment_service.list_assessments.return_value = [mock_soap_assessment]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_assessment_service] = lambda: mock_assessment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/assessments?specialty=physiotherapy&patient_id={mock_soap_assessment.patient_id}",
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_soap_assessment_by_id_not_found(
    mock_clinic: Clinic,
    mock_assessment_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/assessments/{id} returns 404 when missing."""

    assessment_id = uuid4()
    mock_assessment_service.get_assessment.side_effect = TreatmentNotFoundError("Not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_assessment_service] = lambda: mock_assessment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/assessments/{assessment_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404
