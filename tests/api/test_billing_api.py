from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient

from app.api.v1.billing import get_billing_service
from app.core.dependencies import AuthenticatedContext, get_current_clinic
from app.enums.billing import InvoiceStatus, PaymentMethod
from app.enums.package import PackageStatus
from app.enums.user import UserRole
from app.main import app
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.models.billing import Invoice, InvoiceItem, Package, PatientPackage, Payment
from app.models.clinic import Clinic
from app.models.user import User
from app.services.billing import BillingNotFoundError, BillingValidationError


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
def mock_package(mock_clinic: Clinic) -> Package:
    now = datetime.now(timezone.utc)
    return Package(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        name="Physio 10 Sessions",
        total_sessions=10,
        price=Decimal("5000.00"),
        validity_days=90,
        status=PackageStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_patient_package(mock_clinic: Clinic) -> PatientPackage:
    now = datetime.now(timezone.utc)
    return PatientPackage(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        patient_id=uuid4(),
        package_id=uuid4(),
        package_name="Physio 10 Sessions",
        total_sessions=10,
        completed_sessions=2,
        price=Decimal("5000.00"),
        status=PackageStatus.ACTIVE,
        purchased_at=now,
        expires_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_invoice(mock_clinic: Clinic) -> Invoice:
    now = datetime.now(timezone.utc)
    invoice_id = uuid4()
    item = InvoiceItem(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        invoice_id=invoice_id,
        description="Initial Consultation",
        quantity=1,
        unit_price=Decimal("1500.00"),
        total_price=Decimal("1500.00"),
        created_at=now,
        updated_at=now,
    )
    invoice = Invoice(
        id=invoice_id,
        clinic_id=mock_clinic.id,
        patient_id=uuid4(),
        appointment_id=None,
        invoice_number="INV-2026-001",
        issue_date=now,
        due_date=now,
        subtotal=Decimal("1500.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("1500.00"),
        paid_amount=Decimal("0.00"),
        status=InvoiceStatus.ISSUED,
        line_items=[{"description": "Initial Consultation", "quantity": 1, "unit_price": "1500.00", "total_price": "1500.00"}],
        notes="Thank you for your visit.",
        created_at=now,
        updated_at=now,
    )
    invoice.items = [item]
    invoice.payments = []
    return invoice


@pytest.fixture
def mock_payment(mock_clinic: Clinic, mock_invoice: Invoice) -> Payment:
    now = datetime.now(timezone.utc)
    return Payment(
        id=uuid4(),
        clinic_id=mock_clinic.id,
        invoice_id=mock_invoice.id,
        patient_id=mock_invoice.patient_id,
        amount=Decimal("1500.00"),
        payment_method=PaymentMethod.UPI,
        payment_date=now,
        transaction_reference="UPI-123456789",
        notes="Paid via UPI",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_billing_service() -> AsyncMock:
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


# --- Package Catalog API Tests ---

@pytest.mark.asyncio
async def test_create_package_api_success(
    mock_clinic: Clinic, mock_package: Package, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/billing/packages creates a package catalog item."""

    mock_billing_service.create_package.return_value = mock_package
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/billing/packages",
            json={
                "name": "Physio 10 Sessions",
                "total_sessions": 10,
                "price": "5000.00",
                "validity_days": 90,
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Physio 10 Sessions"
    assert data["clinic_id"] == str(mock_clinic.id)


@pytest.mark.asyncio
async def test_list_packages_api_success(
    mock_clinic: Clinic, mock_package: Package, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/billing/packages lists catalog items."""

    mock_billing_service.list_packages.return_value = [mock_package]
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/billing/packages", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(mock_package.id)


@pytest.mark.asyncio
async def test_get_package_api_not_found(
    mock_clinic: Clinic, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/billing/packages/{id} returns 404 when package missing."""

    pkg_id = uuid4()
    mock_billing_service.get_package.side_effect = BillingNotFoundError("Package not found")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/billing/packages/{pkg_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_package_api_success(
    mock_clinic: Clinic, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test DELETE /api/v1/billing/packages/{id} deletes a package."""

    pkg_id = uuid4()
    mock_billing_service.delete_package.return_value = None
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/api/v1/billing/packages/{pkg_id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 204


# --- Patient Package API Tests ---

@pytest.mark.asyncio
async def test_sell_patient_package_api_success(
    mock_clinic: Clinic, mock_patient_package: PatientPackage, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/billing/patients/{patient_id}/packages sells a package."""

    mock_billing_service.sell_package.return_value = mock_patient_package
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/billing/patients/{mock_patient_package.patient_id}/packages",
            json={
                "patient_id": str(mock_patient_package.patient_id),
                "package_id": str(mock_patient_package.package_id),
                "package_name": "Physio 10 Sessions",
                "total_sessions": 10,
                "price": "5000.00",
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["id"] == str(mock_patient_package.id)


# --- Invoice API Tests ---

@pytest.mark.asyncio
async def test_create_invoice_api_success(
    mock_clinic: Clinic, mock_invoice: Invoice, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/billing/invoices creates an invoice."""

    mock_billing_service.create_invoice.return_value = mock_invoice
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/billing/invoices",
            json={
                "patient_id": str(mock_invoice.patient_id),
                "invoice_number": "INV-2026-001",
                "issue_date": datetime.now(timezone.utc).isoformat(),
                "items": [
                    {
                        "description": "Initial Consultation",
                        "quantity": 1,
                        "unit_price": "1500.00",
                    }
                ],
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    data = response.json()
    assert data["invoice_number"] == "INV-2026-001"


@pytest.mark.asyncio
async def test_get_invoice_api_success(
    mock_clinic: Clinic, mock_invoice: Invoice, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/billing/invoices/{id} returns invoice detail."""

    mock_billing_service.get_invoice.return_value = mock_invoice
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/billing/invoices/{mock_invoice.id}", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == str(mock_invoice.id)


@pytest.mark.asyncio
async def test_invoice_pdf_download_api_success(
    mock_clinic: Clinic, mock_invoice: Invoice, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test GET /api/v1/billing/invoices/{id}/pdf/download returns PDF response."""

    mock_billing_service.generate_invoice_pdf.return_value = b"%PDF-1.4 mock content"
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/billing/invoices/{mock_invoice.id}/pdf/download", headers=auth_headers)

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


# --- Payment API Tests ---

@pytest.mark.asyncio
async def test_record_payment_api_success(
    mock_clinic: Clinic, mock_payment: Payment, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/billing/payments records a payment."""

    mock_billing_service.record_payment.return_value = mock_payment
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/billing/payments",
            json={
                "invoice_id": str(mock_payment.invoice_id),
                "patient_id": str(mock_payment.patient_id),
                "amount": "1500.00",
                "payment_method": "upi",
                "payment_date": datetime.now(timezone.utc).isoformat(),
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["id"] == str(mock_payment.id)


@pytest.mark.asyncio
async def test_record_payment_validation_error(
    mock_clinic: Clinic, mock_billing_service: AsyncMock, auth_headers: dict[str, str]
) -> None:
    """Test POST /api/v1/billing/payments returns 400 on business logic validation failure."""

    mock_billing_service.record_payment.side_effect = BillingValidationError("Invoice belong to another patient")
    app.dependency_overrides[get_current_clinic] = lambda: mock_clinic
    app.dependency_overrides[get_billing_service] = lambda: mock_billing_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/billing/payments",
            json={
                "invoice_id": str(uuid4()),
                "patient_id": str(uuid4()),
                "amount": "1500.00",
                "payment_method": "upi",
                "payment_date": datetime.now(timezone.utc).isoformat(),
            },
            headers=auth_headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "Invoice belong to another patient"
