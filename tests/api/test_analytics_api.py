from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.analytics import get_analytics_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AppointmentAnalytics,
    BookingAnalytics,
    LeadAnalytics,
    PatientAnalytics,
    RevenueAnalytics,
)


@pytest.fixture
def mock_clinic() -> Clinic:
    return Clinic(id=uuid4(), name="Analytics Test Clinic")


@pytest.fixture
def mock_user(mock_clinic: Clinic) -> User:
    return User(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Analytics Staff",
        email="analytics@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest.fixture
def mock_overview_response() -> AnalyticsOverviewResponse:
    return AnalyticsOverviewResponse(
        patients=PatientAnalytics(total_patients=15, active_patients=12, new_patients_this_month=5),
        appointments=AppointmentAnalytics(
            today_appointments=3,
            this_week_appointments=18,
            completed_appointments=12,
            cancelled_appointments=2,
            no_show_appointments=1,
        ),
        revenue=RevenueAnalytics(
            revenue_this_month=Decimal("4500.00"),
            paid_invoices_count=8,
            unpaid_invoices_count=2,
            partial_invoices_count=1,
            total_outstanding_amount=Decimal("1200.00"),
        ),
        leads=LeadAnalytics(
            total_leads=10,
            leads_by_stage={"new": 3, "contacted": 2, "qualified": 2, "converted": 2, "lost": 1},
            conversion_rate=20.0,
        ),
        booking=BookingAnalytics(pending_requests=4, approved_requests=5, rejected_requests=1),
    )


@pytest.fixture
def mock_analytics_service(mock_overview_response: AnalyticsOverviewResponse) -> AsyncMock:
    service = AsyncMock()
    service.get_overview.return_value = mock_overview_response
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


# --- Analytics API Tests ---

@pytest.mark.asyncio
async def test_get_analytics_overview_success(
    mock_clinic: Clinic, mock_analytics_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/analytics/overview returns aggregated metrics overview."""

    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/overview", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["patients"]["total_patients"] == 15
    assert data["appointments"]["today_appointments"] == 3
    assert data["revenue"]["revenue_this_month"] == "4500.00"
    assert data["leads"]["total_leads"] == 10
    assert data["booking"]["pending_requests"] == 4


@pytest.mark.asyncio
async def test_get_analytics_overview_empty_db(
    mock_clinic: Clinic, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/analytics/overview handles empty database zero state cleanly."""

    empty_service = AsyncMock()
    empty_service.get_overview.return_value = AnalyticsOverviewResponse(
        patients=PatientAnalytics(total_patients=0, active_patients=0, new_patients_this_month=0),
        appointments=AppointmentAnalytics(
            today_appointments=0,
            this_week_appointments=0,
            completed_appointments=0,
            cancelled_appointments=0,
            no_show_appointments=0,
        ),
        revenue=RevenueAnalytics(
            revenue_this_month=Decimal("0.00"),
            paid_invoices_count=0,
            unpaid_invoices_count=0,
            partial_invoices_count=0,
            total_outstanding_amount=Decimal("0.00"),
        ),
        leads=LeadAnalytics(
            total_leads=0,
            leads_by_stage={"new": 0, "contacted": 0, "qualified": 0, "converted": 0, "lost": 0},
            conversion_rate=0.0,
        ),
        booking=BookingAnalytics(pending_requests=0, approved_requests=0, rejected_requests=0),
    )

    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_analytics_service] = lambda: empty_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/analytics/overview", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["patients"]["total_patients"] == 0
    assert data["leads"]["conversion_rate"] == 0.0
