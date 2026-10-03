from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.enums.booking import AppointmentRequestStatus
from app.enums.billing import InvoiceStatus
from app.services.booking import BookingService
from app.services.billing import BillingService
from app.services import prescription_service
from app.utils.whatsapp import build_whatsapp_link

pytestmark = pytest.mark.asyncio


def test_build_whatsapp_link_normalizes_and_encodes_phone_and_message() -> None:
    link = build_whatsapp_link("+91 98765-43210", "Hello & welcome, doctor.")

    assert link == "https://wa.me/919876543210?text=Hello%20%26%20welcome%2C%20doctor."


class _BookingRequestRepo:
    def __init__(self, request: SimpleNamespace) -> None:
        self.request = request

    async def get_by_id(
        self, request_id: UUID, clinic_id: UUID | None = None
    ) -> SimpleNamespace | None:
        return self.request

    async def update(
        self, req: SimpleNamespace, update_data: dict[str, object]
    ) -> SimpleNamespace:
        for key, value in update_data.items():
            setattr(req, key, value)
        return req


class _BookingPatientRepo:
    async def search_by_phone(
        self, phone: str, clinic_id: UUID | None = None
    ) -> list[SimpleNamespace]:
        return []

    async def create(self, payload: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(
            id=uuid4(),
            full_name=payload["full_name"],
            phone=payload["phone"],
        )


class _BookingAppointmentRepo:
    async def create(self, payload: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(
            id=uuid4(),
            patient_id=payload["patient_id"],
            scheduled_at=payload["scheduled_at"],
        )


class _BookingClinicRepo:
    async def get_by_id(self, clinic_id: UUID) -> SimpleNamespace | None:
        return SimpleNamespace(id=clinic_id)


async def test_booking_approval_includes_whatsapp_link() -> None:
    clinic_id = uuid4()
    request = SimpleNamespace(
        id=uuid4(),
        clinic_id=clinic_id,
        name="Jane Doe",
        phone="98765-43210",
        age=29,
        gender="Female",
        chief_complaint="Back pain",
        notes=None,
        preferred_date=date(2026, 8, 3),
        preferred_slot="morning",
        status=AppointmentRequestStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service = BookingService(
        request_repository=_BookingRequestRepo(request),
        appointment_repository=_BookingAppointmentRepo(),
        patient_repository=_BookingPatientRepo(),
        clinic_repository=_BookingClinicRepo(),
    )

    payload = SimpleNamespace(
        therapist_id=uuid4(), scheduled_date=date(2026, 8, 3), start_time="17:00:00"
    )
    response = await service.approve_request(clinic_id, request.id, payload)

    assert response["message"] == "Appointment request approved successfully."
    assert response["request"]["status"] == AppointmentRequestStatus.APPROVED.value
    assert response["whatsapp_link"].startswith("https://wa.me/919876543210?text=")
    assert "Hello%20Jane%20Doe" in response["whatsapp_link"]


class _BillingInvoiceRepo:
    def __init__(self, invoice: SimpleNamespace) -> None:
        self.invoice = invoice

    async def get_by_id_with_items(
        self, invoice_id: UUID, clinic_id: UUID | None = None
    ) -> SimpleNamespace | None:
        return self.invoice


class _BillingPatientRepo:
    def __init__(self, patient: SimpleNamespace) -> None:
        self.patient = patient

    async def get_by_patient_id(
        self, patient_id: UUID, clinic_id: UUID | None = None
    ) -> SimpleNamespace | None:
        return self.patient


class _NoopRepo:
    pass


async def test_invoice_pdf_response_includes_whatsapp_link() -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    invoice = SimpleNamespace(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        invoice_number="INV-1001",
        issue_date=datetime.now(timezone.utc),
        due_date=None,
        discount_amount=0,
        tax_amount=0,
        subtotal=1500,
        total_amount=1500,
        paid_amount=0,
        status=InvoiceStatus.ISSUED,
        line_items=[],
        items=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    patient = SimpleNamespace(id=patient_id, full_name="Jane Doe", phone="9876543210")

    service = BillingService(
        package_repository=_NoopRepo(),
        patient_package_repository=_NoopRepo(),
        invoice_repository=_BillingInvoiceRepo(invoice),
        invoice_item_repository=_NoopRepo(),
        payment_repository=_NoopRepo(),
        patient_repository=_BillingPatientRepo(patient),
        appointment_repository=_NoopRepo(),
    )

    response = await service.generate_invoice_pdf_response(clinic_id, invoice.id)

    assert response["invoice_id"] == str(invoice.id)
    assert (
        response["download_url"]
        == f"/api/v1/billing/invoices/{invoice.id}/pdf/download"
    )
    assert response["whatsapp_link"].startswith("https://wa.me/919876543210?text=")
    assert (
        "You%20can%20download%20your%20invoice%20here%3A" in response["whatsapp_link"]
    )


async def test_prescription_pdf_response_includes_whatsapp_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prescription_id = uuid4()
    clinic_id = uuid4()
    patient = SimpleNamespace(first_name="Jane", last_name="Doe", phone="9876543210")
    rx = SimpleNamespace(patient=patient)

    async def fake_generate_prescription_pdf(db, clinic_id_arg, prescription_id_arg):
        return f"/api/v1/prescriptions/{prescription_id_arg}/pdf/download"

    async def fake_get_prescription_by_id(db, clinic_id_arg, prescription_id_arg):
        return rx

    monkeypatch.setattr(
        prescription_service,
        "generate_prescription_pdf",
        fake_generate_prescription_pdf,
    )
    monkeypatch.setattr(
        prescription_service, "get_prescription_by_id", fake_get_prescription_by_id
    )

    response = await prescription_service.generate_prescription_pdf_response(
        object(), clinic_id, prescription_id
    )

    assert (
        response["pdf_url"] == f"/api/v1/prescriptions/{prescription_id}/pdf/download"
    )
    assert response["whatsapp_link"].startswith("https://wa.me/919876543210?text=")
    assert "Your%20prescription%20is%20ready." in response["whatsapp_link"]
