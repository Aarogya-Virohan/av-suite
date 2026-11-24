from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select, func, update

from app.core.config import settings
from app.enums.billing import InvoiceStatus, PaymentStatus
from app.models.audit import AuditLog
from app.models.billing import Invoice, Payment
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.models.user import User
from app.enums.document import DocumentCategory
from app.services.audit import changed_fields


API = settings.API_V1_PREFIX


@pytest.fixture(autouse=True)
async def cleanup_patients_created_by_audit_tests(db_session):
    """Keep the shared suite database below the patient list's first page."""
    existing_patient_ids = set((await db_session.scalars(select(Patient.id))).all())
    yield
    await db_session.execute(
        update(Patient)
        .where(Patient.id.not_in(existing_patient_ids))
        .values(deleted_at=func.now())
    )
    await db_session.commit()


async def _patient(client, headers):
    response = await client.post(
        f"{API}/patients",
        json={"first_name": "Audit", "last_name": "Subject", "age": 35},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def _invoice(client, headers, patient_id, **fields):
    response = await client.post(
        f"{API}/invoices",
        json={
            "patient_id": patient_id,
            "issue_date": "2026-10-20T10:00:00Z",
            "items": [{"description": "Care", "quantity": 1, "unit_price": "1000.00"}],
            **fields,
        },
        headers=headers,
    )
    return response


async def _payment(client, headers, invoice, patient_id, amount="100.00"):
    return await client.post(
        f"{API}/payments",
        json={
            "invoice_id": invoice["id"],
            "patient_id": patient_id,
            "amount": amount,
            "payment_method": "cash",
            "payment_date": "2026-10-20T10:00:00Z",
        },
        headers=headers,
    )


def test_field_audit_serialization_filters_unchanged_and_secrets():
    changes = changed_fields(
        {
            "name": "Old",
            "unchanged": Decimal("2.00"),
            "password_hash": "old-hash",
            "status": PaymentStatus.PENDING,
            "date": datetime(2026, 1, 2),
        },
        {
            "name": "New",
            "unchanged": Decimal("2.0"),
            "password_hash": "new-hash",
            "status": PaymentStatus.COMPLETED,
            "date": datetime(2026, 2, 2),
        },
    )
    assert changes == {
        "name": ["Old", "New"],
        "status": ["pending", "completed"],
        "date": ["2026-01-02T00:00:00", "2026-02-02T00:00:00"],
    }


@pytest.mark.asyncio
async def test_patient_view_and_update_emit_one_scoped_audit_with_actual_changes(
    client, auth_headers, db_session
):
    patient_id = await _patient(client, auth_headers)
    response = await client.get(f"{API}/patients/{patient_id}", headers=auth_headers)
    assert response.status_code == 200
    view_count = await db_session.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.entity_id == UUID(patient_id), AuditLog.action == "view",
            AuditLog.entity_type == "patient",
        )
    )
    assert view_count == 1
    missing_id = UUID(int=1)
    missing = await client.get(f"{API}/patients/{missing_id}", headers=auth_headers)
    assert missing.status_code == 404
    assert await db_session.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.entity_id == missing_id, AuditLog.action == "view",
            AuditLog.entity_type == "patient",
        )
    ) == 0

    changed = await client.patch(
        f"{API}/patients/{patient_id}",
        json={"first_name": "Updated", "last_name": "Subject"},
        headers=auth_headers,
    )
    assert changed.status_code == 200, changed.text
    event = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == UUID(patient_id), AuditLog.action == "update"
        ).order_by(AuditLog.created_at.desc())
    )
    assert event.details["changes"] == {"first_name": ["Audit", "Updated"]}


@pytest.mark.asyncio
async def test_lead_update_audits_only_changed_values(client, auth_headers, db_session):
    created = await client.post(
        f"{API}/leads", json={"name": "Audit Lead", "phone": "9876500199"}, headers=auth_headers
    )
    assert created.status_code == 201, created.text
    lead_id = UUID(created.json()["id"])
    updated = await client.patch(
        f"{API}/leads/{lead_id}", json={"name": "Renamed Lead", "phone": "9876500199"}, headers=auth_headers
    )
    assert updated.status_code == 200, updated.text
    event = await db_session.scalar(
        select(AuditLog).where(AuditLog.entity_type == "lead", AuditLog.entity_id == lead_id, AuditLog.action == "update")
    )
    assert event.details["changes"] == {"name": ["Audit Lead", "Renamed Lead"]}


@pytest.mark.asyncio
async def test_appointment_update_audits_multiple_changed_fields(client, auth_headers, db_session):
    patient_id = await _patient(client, auth_headers)
    therapist = await db_session.scalar(select(User).where(User.email == "therapist@avtest.com"))
    appointment = await client.post(
        f"{API}/appointments",
        json={
            "patient_id": patient_id,
            "therapist_id": str(therapist.id),
            "scheduled_at": "2026-11-20T10:00:00Z",
            "duration_minutes": 30,
        },
        headers=auth_headers,
    )
    assert appointment.status_code == 201, appointment.text
    appointment_id = UUID(appointment.json()["id"])
    updated = await client.patch(
        f"{API}/appointments/{appointment_id}",
        json={"status": "completed", "scheduled_at": "2026-11-21T10:00:00Z", "duration_minutes": 30},
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    event = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "appointment", AuditLog.entity_id == appointment_id,
            AuditLog.action == "update",
        )
    )
    assert set(event.details["changes"]) == {"status", "scheduled_at"}
    assert event.details["changes"]["status"] == ["scheduled", "completed"]


@pytest.mark.asyncio
async def test_document_download_audits_metadata_only(client, auth_headers, db_session):
    patient_id = UUID(await _patient(client, auth_headers))
    patient = await db_session.get(Patient, patient_id)
    document = PatientDocument(
        clinic_id=patient.clinic_id,
        patient_id=patient_id,
        file_url="https://files.example.invalid/private-record.pdf",
        file_type="application/pdf",
        file_size=4,
        label="Private record",
        category=DocumentCategory.OTHER,
    )
    db_session.add(document)
    await db_session.commit()
    response = await client.get(f"{API}/documents/{document.id}/download", headers=auth_headers)
    assert response.status_code == 307
    event_count = await db_session.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "download", AuditLog.entity_type == "document",
            AuditLog.entity_id == document.id,
        )
    )
    assert event_count == 1
    event = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "download", AuditLog.entity_type == "document",
            AuditLog.entity_id == document.id,
        )
    )
    assert event.details == {}


@pytest.mark.asyncio
async def test_payment_void_retains_row_recalculates_and_rejects_repeat(
    client, auth_headers, db_session
):
    patient_id = await _patient(client, auth_headers)
    invoice_response = await _invoice(client, auth_headers, patient_id, items=[
        {"description": "Care", "quantity": 1, "unit_price": "100.00"}
    ])
    assert invoice_response.status_code == 201, invoice_response.text
    invoice = invoice_response.json()
    payment_response = await _payment(client, auth_headers, invoice, patient_id, "60.00")
    assert payment_response.status_code == 201, payment_response.text
    payment_id = payment_response.json()["id"]

    invalid = await client.post(f"{API}/payments/{payment_id}/void", json={"reason": "  "}, headers=auth_headers)
    assert invalid.status_code == 422
    voided = await client.post(
        f"{API}/payments/{payment_id}/void", json={"reason": "Duplicate entry"}, headers=auth_headers
    )
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "voided"
    assert voided.json()["void_reason"] == "Duplicate entry"
    assert UUID(voided.json()["voided_by"])
    assert await db_session.get(Payment, UUID(payment_id)) is not None
    void_event = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "payment", AuditLog.entity_id == UUID(payment_id),
            AuditLog.action == "void",
        )
    )
    assert void_event.details["reason"] == "Duplicate entry"
    assert void_event.details["changes"]["status"] == ["completed", "voided"]

    invoice_state = await client.get(f"{API}/invoices/{invoice['id']}", headers=auth_headers)
    assert invoice_state.json()["paid_amount"] == "0.00"
    assert invoice_state.json()["status"] == "unpaid"
    repeated = await client.post(
        f"{API}/payments/{payment_id}/void", json={"reason": "Duplicate entry"}, headers=auth_headers
    )
    assert repeated.status_code == 409


@pytest.mark.asyncio
async def test_payment_void_requires_authorized_user(client, auth_headers, frontdesk_auth_headers):
    patient_id = await _patient(client, auth_headers)
    invoice_response = await _invoice(client, auth_headers, patient_id, items=[
        {"description": "Care", "quantity": 1, "unit_price": "100.00"}
    ])
    payment = await _payment(client, auth_headers, invoice_response.json(), patient_id, "20.00")
    denied = await client.post(
        f"{API}/payments/{payment.json()['id']}/void",
        json={"reason": "Duplicate entry"}, headers=frontdesk_auth_headers,
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_invoice_cancellation_reason_and_draft_only_deletion(client, auth_headers, db_session):
    patient_id = await _patient(client, auth_headers)
    invoice = (await _invoice(client, auth_headers, patient_id, items=[
        {"description": "Care", "quantity": 1, "unit_price": "100.00"}
    ])).json()
    missing = await client.patch(
        f"{API}/invoices/{invoice['id']}", json={"status": "cancelled"}, headers=auth_headers
    )
    assert missing.status_code == 422
    cancelled = await client.patch(
        f"{API}/invoices/{invoice['id']}",
        json={"status": "cancelled", "cancel_reason": "Patient requested cancellation"},
        headers=auth_headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["cancel_reason"] == "Patient requested cancellation"
    cancel_event = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "invoice", AuditLog.entity_id == UUID(invoice["id"]),
            AuditLog.action == "update",
        )
    )
    assert cancel_event.details["cancel_reason"] == "Patient requested cancellation"
    assert cancel_event.details["changes"]["status"] == ["issued", "cancelled"]
    conflict = await client.delete(f"{API}/invoices/{invoice['id']}", headers=auth_headers)
    assert conflict.status_code == 409

    issued = (await _invoice(client, auth_headers, patient_id, items=[
        {"description": "Care", "quantity": 1, "unit_price": "100.00"}
    ])).json()
    paid = await _payment(client, auth_headers, issued, patient_id, "100.00")
    assert paid.status_code == 201, paid.text
    # An issued (here paid) invoice must not be turned back into a draft,
    # or "only drafts can be deleted" could be bypassed in two calls.
    back_to_draft = await client.patch(
        f"{API}/invoices/{issued['id']}", json={"status": "draft"}, headers=auth_headers
    )
    assert back_to_draft.status_code == 409, back_to_draft.text
    assert (await client.delete(f"{API}/invoices/{issued['id']}", headers=auth_headers)).status_code == 409

    draft = (await _invoice(client, auth_headers, patient_id, items=[
        {"description": "Care", "quantity": 1, "unit_price": "100.00"}
    ])).json()
    await db_session.execute(
        update(Invoice).where(Invoice.id == UUID(draft["id"])).values(status=InvoiceStatus.DRAFT)
    )
    await db_session.commit()
    deleted = await client.delete(f"{API}/invoices/{draft['id']}", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_invoice_without_reason_from_before_the_rule_can_still_be_edited(
    client, auth_headers, db_session
):
    """Invoices issued before the 20% rule may have a large discount and no reason."""
    patient_id = await _patient(client, auth_headers)
    invoice = (await _invoice(
        client, auth_headers, patient_id, discount_percent="25", discount_reason="Seed reason"
    )).json()
    await db_session.execute(
        update(Invoice).where(Invoice.id == UUID(invoice["id"])).values(discount_reason=None)
    )
    await db_session.commit()

    notes = await client.patch(
        f"{API}/invoices/{invoice['id']}", json={"notes": "Called patient"}, headers=auth_headers
    )
    assert notes.status_code == 200, notes.text
    cancelled = await client.patch(
        f"{API}/invoices/{invoice['id']}",
        json={"status": "cancelled", "cancel_reason": "Billed twice"},
        headers=auth_headers,
    )
    assert cancelled.status_code == 200, cancelled.text

    # Changing the discount itself still needs the reason.
    other = (await _invoice(
        client, auth_headers, patient_id, discount_percent="25", discount_reason="Seed reason"
    )).json()
    await db_session.execute(
        update(Invoice).where(Invoice.id == UUID(other["id"])).values(discount_reason=None)
    )
    await db_session.commit()
    changed = await client.patch(
        f"{API}/invoices/{other['id']}", json={"discount_percent": "30"}, headers=auth_headers
    )
    assert changed.status_code == 422


@pytest.mark.asyncio
async def test_discount_reason_threshold_amount_and_audit(client, auth_headers, db_session):
    patient_id = await _patient(client, auth_headers)
    exact_percent = await _invoice(client, auth_headers, patient_id, discount_percent="20")
    assert exact_percent.status_code == 201, exact_percent.text
    above_percent = await _invoice(client, auth_headers, patient_id, discount_percent="20.01")
    assert above_percent.status_code == 422
    exact_amount = await _invoice(client, auth_headers, patient_id, discount_amount="200.00")
    assert exact_amount.status_code == 201, exact_amount.text
    above_amount = await _invoice(client, auth_headers, patient_id, discount_amount="200.01")
    assert above_amount.status_code == 422
    below_amount = await _invoice(client, auth_headers, patient_id, discount_amount="199.99")
    assert below_amount.status_code == 201, below_amount.text
    # 20% of 333.33 rounds to 66.67 (a fraction above 20%); exactly 20% needs no reason.
    rounded_percent = await _invoice(
        client, auth_headers, patient_id, discount_percent="20",
        items=[{"description": "Care", "quantity": 1, "unit_price": "333.33"}],
    )
    assert rounded_percent.status_code == 201, rounded_percent.text

    justified = await _invoice(
        client, auth_headers, patient_id, discount_percent="25", discount_reason="Approved hardship"
    )
    assert justified.status_code == 201, justified.text
    invoice_id = UUID(justified.json()["id"])
    stored = await db_session.get(Invoice, invoice_id)
    assert stored.discount_reason == "Approved hardship"
    event = await db_session.scalar(
        select(AuditLog).where(AuditLog.entity_id == invoice_id, AuditLog.action == "create")
    )
    assert event.details["discount_reason"] == "Approved hardship"

    missing_update_reason = await client.patch(
        f"{API}/invoices/{invoice_id}",
        json={"discount_percent": "30", "discount_reason": None},
        headers=auth_headers,
    )
    assert missing_update_reason.status_code == 422
    valid_update = await client.patch(
        f"{API}/invoices/{invoice_id}",
        json={"discount_percent": "30", "discount_reason": "Extended treatment plan"},
        headers=auth_headers,
    )
    assert valid_update.status_code == 200, valid_update.text
    assert valid_update.json()["discount_reason"] == "Extended treatment plan"


@pytest.mark.asyncio
async def test_audit_export_is_admin_only_and_records_only_allowed_fields(
    client, auth_headers, frontdesk_auth_headers, db_session
):
    response = await client.post(
        f"{API}/audit/export", json={"entity_type": "patients", "row_count": 4}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    event = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "export", AuditLog.entity_type == "patients")
        .order_by(AuditLog.created_at.desc())
    )
    assert event.details == {"entity_type": "patients", "row_count": 4}
    assert await db_session.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "export", AuditLog.user_id == event.user_id,
            AuditLog.entity_id.is_(None),
        )
    ) == 1
    denied = await client.post(
        f"{API}/audit/export", json={"entity_type": "patients", "row_count": 4}, headers=frontdesk_auth_headers
    )
    assert denied.status_code == 403
    invalid = await client.post(
        f"{API}/audit/export", json={"entity_type": "  ", "row_count": -1}, headers=auth_headers
    )
    assert invalid.status_code == 422
