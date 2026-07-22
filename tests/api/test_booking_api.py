from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.booking import get_booking_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.appointment import AppointmentSource, AppointmentStatus
from app.enums.booking import AppointmentRequestStatus
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.appointment import Appointment
from app.models.booking import AppointmentRequest
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.booking import PublicClinicBrandingResponse
from app.services.booking import BookingValidationError


@pytest.fixture
def mock_clinic() -> Clinic:
    return Clinic(
        id=uuid4(),
        name="Arogya Physio Clinic",
        branding_logo_url="https://example.com/logo.png",
        branding_color="#008080",
    )


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
def mock_appointment_request(mock_clinic: Clinic) -> AppointmentRequest:
    now = datetime.now(timezone.utc)
    return AppointmentRequest(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Jane Doe",
        phone="+1987654321",
        age=28,
        gender="female",
        chief_complaint="Shoulder pain",
        notes="Prefers morning slot",
        preferred_date=date.today(),
        preferred_slot="morning",
        status=AppointmentRequestStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_approved_appointment(mock_clinic: Clinic, mock_user: User) -> Appointment:
    now = datetime.now(timezone.utc)
    return Appointment(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        patient_id=uuid4(),
        therapist_id=mock_user.id,
        scheduled_at=now,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        source=AppointmentSource.PUBLIC_BOOKING,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_booking_service() -> AsyncMock:
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


# --- Public Unauthenticated Booking API Tests ---

@pytest.mark.asyncio
async def test_get_public_clinic_branding_success(
    mock_clinic: Clinic, mock_booking_service: AsyncMock
) -> None:
    """Test GET /api/v1/booking/branding/{clinic_slug} returns public branding."""

    branding = PublicClinicBrandingResponse(
        clinic_id=mock_clinic.id,
        name=mock_clinic.name,
        slug="arogya-physio-clinic",
        logo_url=mock_clinic.branding_logo_url,
        brand_color=mock_clinic.branding_color,
    )
    mock_booking_service.get_clinic_branding.return_value = branding
    app.dependency_overrides[get_booking_service] = lambda: mock_booking_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/booking/branding/arogya-physio-clinic")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Arogya Physio Clinic"
    assert data["clinic_id"] == str(mock_clinic.id)


@pytest.mark.asyncio
async def test_create_public_appointment_request_success(
    mock_clinic: Clinic, mock_appointment_request: AppointmentRequest, mock_booking_service: AsyncMock
) -> None:
    """Test POST /api/v1/booking/request submits an appointment request."""

    mock_booking_service.create_request.return_value = mock_appointment_request
    app.dependency_overrides[get_booking_service] = lambda: mock_booking_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/booking/request?clinic_id={mock_clinic.id}",
            json={
                "name": "Jane Doe",
                "phone": "+1987654321",
                "age": 28,
                "gender": "female",
                "chief_complaint": "Shoulder pain",
                "preferred_slot": "morning",
            },
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["clinic_id"] == str(mock_clinic.id)


# --- Authenticated Staff Appointment Request Queue API Tests ---

@pytest.mark.asyncio
async def test_list_appointment_requests_api_success(
    mock_clinic: Clinic, mock_appointment_request: AppointmentRequest, mock_booking_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/appointment-requests returns request queue."""

    mock_booking_service.list_requests.return_value = [mock_appointment_request]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_booking_service] = lambda: mock_booking_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/appointment-requests?status=pending", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(mock_appointment_request.id)


@pytest.mark.asyncio
async def test_approve_appointment_request_api_success(
    mock_clinic: Clinic,
    mock_appointment_request: AppointmentRequest,
    mock_approved_appointment: Appointment,
    mock_booking_service: AsyncMock,
    auth_headers: dict[str, str],
) -> None:
    """Test POST /api/v1/appointment-requests/{id}/approve approves request and schedules appointment."""

    mock_appointment_request.status = AppointmentRequestStatus.APPROVED
    mock_booking_service.approve_request.return_value = (mock_appointment_request, mock_approved_appointment)
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_booking_service] = lambda: mock_booking_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/appointment-requests/{mock_appointment_request.id}/approve",
            json={"scheduled_date": date.today().isoformat(), "start_time": "10:00:00"},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["appointment_id"] == str(mock_approved_appointment.id)
    assert data["request"]["status"] == "approved"


@pytest.mark.asyncio
async def test_approve_duplicate_rejection(
    mock_clinic: Clinic, mock_booking_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/appointment-requests/{id}/approve rejects duplicate approval."""

    req_id = uuid4()
    mock_booking_service.approve_request.side_effect = BookingValidationError("Already approved")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_booking_service] = lambda: mock_booking_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/appointment-requests/{req_id}/approve",
            json={},
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Already approved"


@pytest.mark.asyncio
async def test_reject_appointment_request_api_success(
    mock_clinic: Clinic, mock_appointment_request: AppointmentRequest, mock_booking_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/appointment-requests/{id}/reject rejects request."""

    mock_appointment_request.status = AppointmentRequestStatus.REJECTED
    mock_booking_service.reject_request.return_value = mock_appointment_request
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_booking_service] = lambda: mock_booking_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/appointment-requests/{mock_appointment_request.id}/reject?notes=Not+available",
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
