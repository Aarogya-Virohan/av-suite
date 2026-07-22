from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.documents import get_document_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.document import DocumentCategory
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.document import PatientDocument
from app.models.user import User
from app.services.document import DocumentNotFoundError, DocumentValidationError


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
def mock_document(mock_clinic: Clinic, mock_user: User) -> PatientDocument:
    now = datetime.now(timezone.utc)
    return PatientDocument(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        patient_id=uuid4(),
        uploaded_by=mock_user.id,
        treatment_id=None,
        file_url="https://storage.supabase.co/v1/object/authenticated/docs/report.pdf",
        file_type="application/pdf",
        file_size=1024500,
        label="Blood Test Report",
        category=DocumentCategory.LAB_RESULT,
        notes="Normal blood values",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_document_service() -> AsyncMock:
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


# --- Document API Tests ---

@pytest.mark.asyncio
async def test_create_document_api_success(
    mock_clinic: Clinic, mock_document: PatientDocument, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/documents creates a patient document metadata record."""

    mock_document_service.create_document.return_value = mock_document
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            json={
                "patient_id": str(mock_document.patient_id),
                "file_url": "https://storage.supabase.co/v1/object/authenticated/docs/report.pdf",
                "file_type": "application/pdf",
                "file_size": 1024500,
                "label": "Blood Test Report",
                "category": "lab_result",
                "notes": "Normal blood values",
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == "Blood Test Report"
    assert data["clinic_id"] == str(mock_clinic.id)


@pytest.mark.asyncio
async def test_get_document_api_success(
    mock_clinic: Clinic, mock_document: PatientDocument, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/documents/{id} returns document detail."""

    mock_document_service.get_document.return_value = mock_document
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/documents/{mock_document.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_document.id)


@pytest.mark.asyncio
async def test_download_document_api_success(
    mock_clinic: Clinic, mock_document: PatientDocument, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/documents/{id}/download redirects to file URL."""

    mock_document_service.get_document.return_value = mock_document
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as client:
        response = await client.get(f"/api/v1/documents/{mock_document.id}/download", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 307
    assert response.headers["location"] == mock_document.file_url


@pytest.mark.asyncio
async def test_list_documents_api_success(
    mock_clinic: Clinic, mock_document: PatientDocument, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/documents returns paginated list."""

    mock_document_service.list_documents.return_value = [mock_document]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/documents?offset=0&limit=10", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(mock_document.id)


@pytest.mark.asyncio
async def test_patch_document_api_success(
    mock_clinic: Clinic, mock_document: PatientDocument, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test PATCH /api/v1/documents/{id} updates document metadata."""

    mock_document_service.update_document.return_value = mock_document
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/documents/{mock_document.id}",
            json={"label": "Updated Blood Test Report"},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_document.id)


@pytest.mark.asyncio
async def test_delete_document_api_success(
    mock_clinic: Clinic, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test DELETE /api/v1/documents/{id} deletes document record."""

    doc_id = uuid4()
    mock_document_service.delete_document.return_value = None
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_document_not_found(
    mock_clinic: Clinic, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/documents/{id} returns 404 when document missing."""

    doc_id = uuid4()
    mock_document_service.get_document.side_effect = DocumentNotFoundError("Document not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_document_validation_error(
    mock_clinic: Clinic, mock_document_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/documents returns 400 on business validation failure."""

    mock_document_service.create_document.side_effect = DocumentValidationError("Patient does not exist")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_document_service] = lambda: mock_document_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents",
            json={
                "patient_id": str(uuid4()),
                "file_url": "https://storage.supabase.co/v1/object/authenticated/docs/report.pdf",
                "file_type": "application/pdf",
                "label": "Invalid Report",
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Patient does not exist"
