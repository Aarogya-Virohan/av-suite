from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.settings import get_settings_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic, get_current_user
from app.enums.clinic import ClinicPlanTier
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.user import User
from app.services.settings import SettingsNotFoundError


@pytest.fixture
def mock_clinic() -> Clinic:
    now = datetime.now(timezone.utc)
    return Clinic(
        id=uuid4(),
        name="Arogya Main Clinic",
        branding_logo_url="https://example.com/logo.png",
        branding_color="#008080",
        plan_tier=ClinicPlanTier.CLINICAL_PRO,
        is_partner_clinic=False,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_admin_user(mock_clinic: Clinic) -> User:
    return User(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Admin User",
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest.fixture
def mock_therapist_user(mock_clinic: Clinic) -> User:
    return User(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Therapist User",
        email="therapist@example.com",
        role=UserRole.THERAPIST,
        is_active=True,
    )


@pytest.fixture
def mock_settings_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def mock_clinic_gate(mock_clinic: Clinic, mock_admin_user: User):
    auth_ctx = AuthenticatedContext(user=mock_admin_user, clinic=mock_clinic)
    with patch.object(ClinicGateMiddleware, "_resolve_context", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = auth_ctx
        yield mock_resolve


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer mock-test-token"}


# --- Settings API Tests ---

@pytest.mark.asyncio
async def test_get_clinic_settings_success(
    mock_clinic: Clinic, mock_settings_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/settings/clinic returns clinic settings."""

    mock_settings_service.get_settings.return_value = mock_clinic
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_settings_service] = lambda: mock_settings_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/settings/clinic", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Arogya Main Clinic"
    assert data["plan_tier"] == "clinical_pro"
    assert data["is_partner_clinic"] is False


@pytest.mark.asyncio
async def test_patch_clinic_settings_success(
    mock_clinic: Clinic,
    mock_admin_user: User,
    mock_settings_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test PATCH /api/v1/settings/clinic updates allowed branding settings for Admin."""

    mock_clinic.name = "Updated Arogya Clinic"
    mock_settings_service.update_settings.return_value = mock_clinic
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_settings_service] = lambda: mock_settings_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/settings/clinic",
            json={"name": "Updated Arogya Clinic", "branding_color": "#FF5733"},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Arogya Clinic"


@pytest.mark.asyncio
async def test_patch_clinic_settings_forbidden_for_therapist(
    mock_clinic: Clinic,
    mock_therapist_user: User,
    mock_settings_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test PATCH /api/v1/settings/clinic returns 403 Forbidden for non-admin staff."""

    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_current_user] = lambda: mock_therapist_user
    app.dependency_overrides[get_settings_service] = lambda: mock_settings_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/settings/clinic",
            json={"name": "Attempted Name Change"},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "Only clinic administrators may update clinic settings."


@pytest.mark.asyncio
async def test_get_clinic_settings_not_found(
    mock_clinic: Clinic, mock_settings_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/settings/clinic returns 404 when clinic record is missing."""

    mock_settings_service.get_settings.side_effect = SettingsNotFoundError("Clinic not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_settings_service] = lambda: mock_settings_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/settings/clinic", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404
