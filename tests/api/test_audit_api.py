from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.audit import get_audit_log_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.audit import AuditLog
from app.models.clinic import Clinic
from app.models.user import User
from app.services.audit import AuditLogService


@pytest.fixture
def mock_clinic() -> Clinic:
    return Clinic(id=uuid4(), name="Audit Log Test Clinic")


@pytest.fixture
def mock_user(mock_clinic: Clinic) -> User:
    return User(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Audit Staff",
        email="audit@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest.fixture
def mock_audit_log(mock_clinic: Clinic, mock_user: User) -> AuditLog:
    now = datetime.now(timezone.utc)
    return AuditLog(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        user_id=mock_user.id,
        action="create",
        entity_type="patient",
        entity_id=uuid4(),
        details={"name": "Alice Smith"},
        created_at=now,
    )


@pytest.fixture
def mock_audit_service(mock_audit_log: AuditLog) -> AsyncMock:
    service = AsyncMock()
    service.list_logs.return_value = [mock_audit_log]
    service.log_event.return_value = mock_audit_log
    return service


@pytest.fixture(autouse=True)
def mock_clinic_gate(mock_clinic: Clinic, mock_user: User):
    auth_ctx = AuthenticatedContext(user=mock_user, clinic=mock_clinic)
    with patch.object(ClinicGateMiddleware, "_resolve_context", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = auth_ctx
        yield mock_resolve


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer mock-test-token"}


# --- Audit Log API Tests ---

@pytest.mark.asyncio
async def test_list_audit_logs_success(
    mock_clinic: Clinic,
    mock_audit_log: AuditLog,
    mock_audit_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test GET /api/v1/audit-logs returns list of audit log entries."""

    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_audit_log_service] = lambda: mock_audit_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/audit-logs?entity_type=patient&action=create", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(mock_audit_log.id)
    assert data["items"][0]["action"] == "create"
    assert data["items"][0]["entity_type"] == "patient"


@pytest.mark.asyncio
async def test_log_event_service_failure_safety() -> None:
    """Test AuditLogService.log_event suppresses exception safely without crashing calling workflow."""

    failing_repo = AsyncMock()
    failing_repo.create.side_effect = RuntimeError("Database connection dropped")
    service = AuditLogService(audit_repository=failing_repo)

    result = await service.log_event(
        clinic_id=uuid4(),
        user_id=uuid4(),
        action="update",
        entity_type="appointment",
        entity_id=uuid4(),
        details={"status": "cancelled"},
    )

    assert result is None
