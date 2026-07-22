from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.appointments import get_appointment_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.appointment import AppointmentSource, AppointmentStatus
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.user import User
from app.services.appointment import AppointmentNotFoundError



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
def mock_appointment(mock_clinic: Clinic) -> Appointment:
    now = datetime.now(timezone.utc)
    return Appointment(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        patient_id=uuid4(),
        therapist_id=uuid4(),
        scheduled_at=now,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        source=AppointmentSource.MANUAL,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_appointment_service() -> AsyncMock:
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
async def test_create_appointment_api_success(
    mock_clinic: Clinic, mock_appointment: Appointment, mock_appointment_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/appointments creates an appointment successfully."""

    mock_appointment_service.create_appointment.return_value = mock_appointment
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_appointment_service] = lambda: mock_appointment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/appointments",
            json={
                "patient_id": str(mock_appointment.patient_id),
                "therapist_id": str(mock_appointment.therapist_id),
                "scheduled_at": mock_appointment.scheduled_at.isoformat(),
                "duration_minutes": 30,
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["clinic_id"] == str(mock_clinic.id)
    assert data["duration_minutes"] == 30


@pytest.mark.asyncio
async def test_list_appointments_api_with_filters(
    mock_clinic: Clinic, mock_appointment: Appointment, mock_appointment_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/appointments returns paginated appointments matching filters."""

    mock_appointment_service.list_appointments.return_value = [mock_appointment]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_appointment_service] = lambda: mock_appointment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/appointments?patient={mock_appointment.patient_id}&therapist={mock_appointment.therapist_id}&date=2026-07-22",
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_get_appointment_by_id_api_success(
    mock_clinic: Clinic, mock_appointment: Appointment, mock_appointment_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/appointments/{id} returns appointment details."""

    mock_appointment_service.get_appointment.return_value = mock_appointment
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_appointment_service] = lambda: mock_appointment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/appointments/{mock_appointment.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_appointment.id)


@pytest.mark.asyncio
async def test_get_appointment_by_id_api_not_found(
    mock_clinic: Clinic, mock_appointment_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/appointments/{id} returns 404 when not found."""

    appt_id = uuid4()
    mock_appointment_service.get_appointment.side_effect = AppointmentNotFoundError("Not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_appointment_service] = lambda: mock_appointment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/appointments/{appt_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_appointment_api_success(
    mock_clinic: Clinic, mock_appointment: Appointment, mock_appointment_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test PATCH /api/v1/appointments/{id} reschedules/updates an appointment."""

    mock_appointment_service.update_appointment.return_value = mock_appointment
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_appointment_service] = lambda: mock_appointment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/appointments/{mock_appointment.id}",
            json={"duration_minutes": 45},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_appointment_api_soft_cancel(
    mock_clinic: Clinic, mock_appointment: Appointment, mock_appointment_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test DELETE /api/v1/appointments/{id} soft-cancels the appointment."""

    mock_appointment_service.soft_cancel.return_value = mock_appointment
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_appointment_service] = lambda: mock_appointment_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/appointments/{mock_appointment.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_appointment.id)
