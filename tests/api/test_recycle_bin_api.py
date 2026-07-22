from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.recycle_bin import get_recycle_bin_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.schemas.recycle_bin import (
    RecycleBinItemResponse,
    RecycleBinRestoreResponse,
)
from app.services.recycle_bin import (
    RecycleBinError,
    RecycleBinNotFoundError,
)


@pytest.fixture
def mock_clinic() -> Clinic:
    return Clinic(id=uuid4(), name="Recycle Bin Test Clinic")


@pytest.fixture
def mock_user(mock_clinic: Clinic) -> User:
    return User(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Test User",
        email="recycle@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest.fixture
def mock_deleted_patient(mock_clinic: Clinic) -> Patient:
    now = datetime.now(timezone.utc)
    p = Patient(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        full_name="Deleted Patient",
        phone="+1987654321",
        created_at=now,
        updated_at=now,
    )
    p.deleted_at = now
    p.deleted_by = uuid4()
    return p


@pytest.fixture
def mock_recycle_bin_service() -> AsyncMock:
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


# --- Recycle Bin API Tests ---

@pytest.mark.asyncio
async def test_list_recycle_bin_items_success(
    mock_clinic: Clinic,
    mock_deleted_patient: Patient,
    mock_recycle_bin_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/recycle-bin lists soft-deleted resources."""

    item = RecycleBinItemResponse(
        id=mock_deleted_patient.id,
        resource_type="patient",
        title=mock_deleted_patient.full_name,
        deleted_at=mock_deleted_patient.deleted_at or datetime.now(timezone.utc),
        deleted_by=mock_deleted_patient.deleted_by,
    )
    mock_recycle_bin_service.list_deleted.return_value = [item]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_recycle_bin_service] = lambda: mock_recycle_bin_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/recycle-bin", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(mock_deleted_patient.id)
    assert data["items"][0]["resource_type"] == "patient"


@pytest.mark.asyncio
async def test_restore_recycle_bin_item_success(
    mock_clinic: Clinic,
    mock_deleted_patient: Patient,
    mock_recycle_bin_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /api/v1/recycle-bin/{resource}/{id}/restore restores soft-deleted item."""

    restore_resp = RecycleBinRestoreResponse(
        message="Patient restored successfully.",
        resource_type="patient",
        id=mock_deleted_patient.id,
        restored=True,
    )
    mock_recycle_bin_service.restore_resource.return_value = restore_resp
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_recycle_bin_service] = lambda: mock_recycle_bin_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/recycle-bin/patient/{mock_deleted_patient.id}/restore",
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["restored"] is True
    assert data["id"] == str(mock_deleted_patient.id)


@pytest.mark.asyncio
async def test_restore_missing_resource_returns_404(
    mock_clinic: Clinic,
    mock_recycle_bin_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /api/v1/recycle-bin/{resource}/{id}/restore returns 404 for missing resource."""

    resource_id = uuid4()
    mock_recycle_bin_service.restore_resource.side_effect = RecycleBinNotFoundError("Resource not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_recycle_bin_service] = lambda: mock_recycle_bin_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/recycle-bin/patient/{resource_id}/restore",
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_restore_already_active_resource_returns_400(
    mock_clinic: Clinic,
    mock_recycle_bin_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /api/v1/recycle-bin/{resource}/{id}/restore returns 400 for already restored resource."""

    resource_id = uuid4()
    mock_recycle_bin_service.restore_resource.side_effect = RecycleBinError("Resource is not deleted")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_recycle_bin_service] = lambda: mock_recycle_bin_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/recycle-bin/patient/{resource_id}/restore",
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Resource is not deleted"
