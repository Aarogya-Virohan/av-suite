from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.enums.billing import InvoiceStatus, PaymentMethod
from app.enums.package import PackageStatus
from app.models.billing import Invoice, Package, Payment
from app.models.patient import Patient
from app.schemas.billing import (
    InvoiceCreate,
    InvoiceItemCreate,
    PackageCreate,
    PatientPackageCreate,
    PaymentCreate,
)
from app.services.billing import BillingNotFoundError, BillingService, BillingValidationError


@pytest.fixture
def mock_repositories() -> dict[str, AsyncMock]:
    return {
        "package": AsyncMock(),
        "patient_package": AsyncMock(),
        "invoice": AsyncMock(),
        "invoice_item": AsyncMock(),
        "payment": AsyncMock(),
        "patient": AsyncMock(),
        "appointment": AsyncMock(),
    }


@pytest.fixture
def billing_service(mock_repositories: dict[str, AsyncMock]) -> BillingService:
    return BillingService(
        package_repository=mock_repositories["package"],
        patient_package_repository=mock_repositories["patient_package"],
        invoice_repository=mock_repositories["invoice"],
        invoice_item_repository=mock_repositories["invoice_item"],
        payment_repository=mock_repositories["payment"],
        patient_repository=mock_repositories["patient"],
        appointment_repository=mock_repositories["appointment"],
    )


@pytest.mark.asyncio
async def test_create_package_service_success(billing_service: BillingService, mock_repositories: dict[str, AsyncMock]) -> None:
    """Test package catalog creation in service layer."""

    clinic_id = uuid4()
    now = datetime.now(timezone.utc)
    mock_pkg = Package(
        id=uuid4(),
        clinic_id=clinic_id,
        name="10 Sessions Pack",
        total_sessions=10,
        price=Decimal("4000.00"),
        validity_days=60,
        status=PackageStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    mock_repositories["package"].create.return_value = mock_pkg

    payload = PackageCreate(name="10 Sessions Pack", total_sessions=10, price=Decimal("4000.00"), validity_days=60)
    result = await billing_service.create_package(clinic_id, payload)
    assert result.name == "10 Sessions Pack"
    assert result.price == Decimal("4000.00")
    _ = mock_repositories["package"].create.assert_awaited_once()


@pytest.mark.asyncio
async def test_sell_package_patient_not_found(billing_service: BillingService, mock_repositories: dict[str, AsyncMock]) -> None:
    """Test error when selling package to non-existent patient."""

    mock_repositories["patient"].get_by_patient_id.return_value = None
    clinic_id = uuid4()
    patient_id = uuid4()

    payload = PatientPackageCreate(
        patient_id=patient_id,
        package_name="10 Sessions Pack",
        total_sessions=10,
        price=Decimal("4000.00"),
    )

    with pytest.raises(BillingValidationError, match="does not exist"):
        await billing_service.sell_package(clinic_id, payload)


@pytest.mark.asyncio
async def test_create_invoice_success(billing_service: BillingService, mock_repositories: dict[str, AsyncMock]) -> None:
    """Test creating an invoice with line items calculates correct subtotal and total."""

    clinic_id = uuid4()
    patient_id = uuid4()
    mock_patient = Patient(id=patient_id, clinic_id=clinic_id, full_name="John Doe")
    mock_repositories["patient"].get_by_patient_id.return_value = mock_patient

    now = datetime.now(timezone.utc)
    mock_inv = Invoice(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        invoice_number="INV-100",
        issue_date=now,
        subtotal=Decimal("2000.00"),
        discount_amount=Decimal("200.00"),
        tax_amount=Decimal("100.00"),
        total_amount=Decimal("1900.00"),
        paid_amount=Decimal("0.00"),
        status=InvoiceStatus.ISSUED,
        line_items=[],
        created_at=now,
        updated_at=now,
    )
    mock_repositories["invoice"].create.return_value = mock_inv
    mock_repositories["invoice"].get_by_id_with_items.return_value = mock_inv

    payload = InvoiceCreate(
        patient_id=patient_id,
        invoice_number="INV-100",
        issue_date=now,
        discount_amount=Decimal("200.00"),
        tax_amount=Decimal("100.00"),
        items=[InvoiceItemCreate(description="Therapy Session", quantity=2, unit_price=Decimal("1000.00"))],
    )

    result = await billing_service.create_invoice(clinic_id, payload)
    assert result.subtotal == Decimal("2000.00")
    assert result.total_amount == Decimal("1900.00")


@pytest.mark.asyncio
async def test_record_payment_updates_invoice_status(billing_service: BillingService, mock_repositories: dict[str, AsyncMock]) -> None:
    """Test recording payment updates invoice paid amount and transitions status to PAID."""

    clinic_id = uuid4()
    patient_id = uuid4()
    invoice_id = uuid4()
    now = datetime.now(timezone.utc)

    mock_patient = Patient(id=patient_id, clinic_id=clinic_id, full_name="John Doe")
    mock_repositories["patient"].get_by_patient_id.return_value = mock_patient

    mock_inv = Invoice(
        id=invoice_id,
        clinic_id=clinic_id,
        patient_id=patient_id,
        invoice_number="INV-100",
        issue_date=now,
        subtotal=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
        paid_amount=Decimal("0.00"),
        status=InvoiceStatus.ISSUED,
        line_items=[],
        created_at=now,
        updated_at=now,
    )
    mock_repositories["invoice"].get_by_id_with_items.return_value = mock_inv

    mock_pmt = Payment(
        id=uuid4(),
        clinic_id=clinic_id,
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=Decimal("1000.00"),
        payment_method=PaymentMethod.CASH,
        payment_date=now,
        created_at=now,
        updated_at=now,
    )
    mock_repositories["payment"].create.return_value = mock_pmt

    payload = PaymentCreate(
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=Decimal("1000.00"),
        payment_method=PaymentMethod.CASH,
        payment_date=now,
    )

    payment = await billing_service.record_payment(clinic_id, payload)
    assert payment.amount == Decimal("1000.00")
    _ = mock_repositories["invoice"].update.assert_awaited_once_with(
        mock_inv, {"paid_amount": Decimal("1000.00"), "status": InvoiceStatus.PAID}
    )


@pytest.mark.asyncio
async def test_get_invoice_not_found(billing_service: BillingService, mock_repositories: dict[str, AsyncMock]) -> None:
    """Test BillingNotFoundError when invoice does not exist."""

    mock_repositories["invoice"].get_by_id_with_items.return_value = None
    clinic_id = uuid4()
    invoice_id = uuid4()

    with pytest.raises(BillingNotFoundError, match=f"Invoice '{invoice_id}' not found"):
        await billing_service.get_invoice(clinic_id, invoice_id)
