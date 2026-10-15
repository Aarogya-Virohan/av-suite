from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.enums.billing import InvoiceStatus
from app.models.billing import Invoice
from app.models.clinic import Clinic
from app.models.patient import Patient


async def _create_patient(client, auth_headers):
    response = await client.post(
        f"{settings.API_V1_PREFIX}/patients",
        json={"first_name": "Billing", "last_name": "Patient", "phone": "9876500101"},
        headers=auth_headers,
    )
    assert response.status_code in (200, 201), response.text
    return UUID(response.json()["data"]["id"])


async def _create_invoice(client, auth_headers, patient_id, total="10000.00", **extra):
    response = await client.post(
        f"{settings.API_V1_PREFIX}/invoices",
        json={
            "patient_id": str(patient_id),
            "issue_date": "2026-10-15T10:00:00Z",
            "items": [{"description": "Treatment", "quantity": 1, "unit_price": total}],
            **extra,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _record_payment(client, auth_headers, invoice, patient_id, amount):
    return await client.post(
        f"{settings.API_V1_PREFIX}/payments",
        json={
            "invoice_id": invoice["id"],
            "patient_id": str(patient_id),
            "amount": str(amount),
            "payment_method": "cash",
            "payment_date": "2026-10-15T10:00:00Z",
        },
        headers=auth_headers,
    )


@pytest.mark.asyncio
async def test_partial_and_exact_balance_payments_and_overpayment(client, auth_headers):
    patient_id = await _create_patient(client, auth_headers)
    invoice = await _create_invoice(client, auth_headers, patient_id)

    first = await _record_payment(client, auth_headers, invoice, patient_id, "3000.00")
    assert first.status_code == 201, first.text
    after_first = await client.get(
        f"{settings.API_V1_PREFIX}/invoices/{invoice['id']}", headers=auth_headers
    )
    assert after_first.json()["paid_amount"] == "3000.00"
    assert after_first.json()["status"] == InvoiceStatus.PARTIAL

    second = await _record_payment(client, auth_headers, invoice, patient_id, "4000.00")
    assert second.status_code == 201, second.text
    final = await _record_payment(client, auth_headers, invoice, patient_id, "3000.00")
    assert final.status_code == 201, final.text
    paid = await client.get(
        f"{settings.API_V1_PREFIX}/invoices/{invoice['id']}", headers=auth_headers
    )
    assert paid.json()["paid_amount"] == "10000.00"
    assert paid.json()["status"] == InvoiceStatus.PAID

    overpayment = await _record_payment(client, auth_headers, invoice, patient_id, "0.01")
    assert overpayment.status_code == 400
    payment_list = await client.get(
        f"{settings.API_V1_PREFIX}/payments",
        params={"invoice_id": invoice["id"]},
        headers=auth_headers,
    )
    assert payment_list.json()["total"] == 3


@pytest.mark.asyncio
async def test_payment_above_remaining_balance_is_rejected_without_changes(
    client, auth_headers
):
    patient_id = await _create_patient(client, auth_headers)
    invoice = await _create_invoice(client, auth_headers, patient_id, total="100.00")

    overpayment = await _record_payment(client, auth_headers, invoice, patient_id, "100.01")
    assert overpayment.status_code == 400
    current = await client.get(
        f"{settings.API_V1_PREFIX}/invoices/{invoice['id']}", headers=auth_headers
    )
    assert current.json()["paid_amount"] == "0.00"
    payments = await client.get(
        f"{settings.API_V1_PREFIX}/payments",
        params={"invoice_id": invoice["id"]},
        headers=auth_headers,
    )
    assert payments.json()["total"] == 0


@pytest.mark.asyncio
async def test_invoice_numbers_are_backend_generated_and_clinic_unique(
    client, auth_headers, db_session
):
    patient_id = await _create_patient(client, auth_headers)
    first = await _create_invoice(
        client,
        auth_headers,
        patient_id,
        total="25.00",
        invoice_number="CLIENT-CONTROLLED",
    )
    second = await _create_invoice(client, auth_headers, patient_id, total="25.00")

    assert first["invoice_number"] != "CLIENT-CONTROLLED"
    assert first["invoice_number"] == f"INV-{UUID(first['id']).hex.upper()}"
    assert second["invoice_number"] == f"INV-{UUID(second['id']).hex.upper()}"
    assert first["invoice_number"] != second["invoice_number"]

    stored = await db_session.get(Invoice, UUID(first["id"]))
    assert stored.invoice_number == first["invoice_number"]
    stored_clinic_id = stored.clinic_id
    stored_patient_id = stored.patient_id
    stored_number = stored.invoice_number

    duplicate = Invoice(
        clinic_id=stored_clinic_id,
        patient_id=stored_patient_id,
        invoice_number=stored_number,
        issue_date=datetime.now(timezone.utc),
        subtotal=Decimal("1.00"),
        total_amount=Decimal("1.00"),
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    other_clinic = Clinic(name="Other Billing Clinic")
    db_session.add(other_clinic)
    await db_session.flush()
    other_patient = Patient(
        clinic_id=other_clinic.id,
        first_name="Other",
        last_name="Patient",
        phone="9876500102",
    )
    db_session.add(other_patient)
    await db_session.flush()
    cross_clinic_invoice = Invoice(
        clinic_id=other_clinic.id,
        patient_id=other_patient.id,
        invoice_number=stored_number,
        issue_date=datetime.now(timezone.utc),
        subtotal=Decimal("1.00"),
        total_amount=Decimal("1.00"),
    )
    db_session.add(cross_clinic_invoice)
    await db_session.flush()
