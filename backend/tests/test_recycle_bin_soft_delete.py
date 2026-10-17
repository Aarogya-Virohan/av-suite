from jose import jwt
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.config import settings
from app.enums.document import DocumentCategory
from app.enums.billing import InvoiceStatus
from app.models.billing import Invoice
from app.models.document import PatientDocument


@pytest.mark.asyncio
async def test_patient_delete_attribution_recycle_bin_and_restore(client, auth_headers):
    created = await client.post(
        f"{settings.API_V1_PREFIX}/patients",
        json={"first_name": "Recycle", "last_name": "Patient", "phone": "9876501234"},
        headers=auth_headers,
    )
    assert created.status_code in (200, 201), created.text
    patient_id = created.json()["data"]["id"]
    token = auth_headers["Authorization"].split(" ", 1)[1]
    user_id = jwt.decode(token, key="", options={"verify_signature": False})["sub"]

    deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert deleted.status_code == 200, deleted.text

    deleted_get = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert deleted_get.status_code == 404
    deleted_patch = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}",
        json={"first_name": "Should Not Persist"}, headers=auth_headers,
    )
    assert deleted_patch.status_code == 404

    recycle = await client.get(
        f"{settings.API_V1_PREFIX}/recycle-bin",
        params={"resource_type": "patient"},
        headers=auth_headers,
    )
    assert recycle.status_code == 200, recycle.text
    item = next(row for row in recycle.json()["items"] if row["id"] == patient_id)
    assert item["deleted_at"]
    assert item["deleted_by"] == user_id

    restored = await client.post(
        f"{settings.API_V1_PREFIX}/recycle-bin/patient/{patient_id}/restore",
        headers=auth_headers,
    )
    assert restored.status_code == 200, restored.text

    after_restore = await client.get(
        f"{settings.API_V1_PREFIX}/recycle-bin",
        params={"resource_type": "patient"},
        headers=auth_headers,
    )
    assert after_restore.status_code == 200
    assert all(row["id"] != patient_id for row in after_restore.json()["items"])

    active = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert active.status_code == 200
    active_patch = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}",
        json={"first_name": "Restored Patient"}, headers=auth_headers,
    )
    assert active_patch.status_code == 200, active_patch.text
    assert active_patch.json()["data"]["first_name"] == "Restored Patient"


@pytest.mark.asyncio
async def test_other_soft_delete_flows_record_authenticated_user(
    client, auth_headers, db_session
):
    token = auth_headers["Authorization"].split(" ", 1)[1]
    claims = jwt.decode(token, key="", options={"verify_signature": False})
    user_id = UUID(claims["sub"])
    clinic_id = UUID(claims["clinic_id"])

    patient_response = await client.post(
        f"{settings.API_V1_PREFIX}/patients",
        json={"first_name": "Soft", "last_name": "Delete", "phone": "9876504321"},
        headers=auth_headers,
    )
    assert patient_response.status_code in (200, 201), patient_response.text
    patient_id = UUID(patient_response.json()["data"]["id"])

    lead_response = await client.post(
        f"{settings.API_V1_PREFIX}/leads",
        json={"name": "Lead To Delete", "phone": "9876507654"},
        headers=auth_headers,
    )
    assert lead_response.status_code == 201, lead_response.text
    lead_id = lead_response.json()["id"]
    lead_deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/leads/{lead_id}", headers=auth_headers
    )
    assert lead_deleted.status_code == 204, lead_deleted.text

    appointment_response = await client.post(
        f"{settings.API_V1_PREFIX}/appointments",
        json={
            "patient_id": str(patient_id),
            "therapist_id": str(user_id),
            "scheduled_at": "2026-11-01T10:00:00Z",
            "duration_minutes": 30,
        },
        headers=auth_headers,
    )
    assert appointment_response.status_code == 201, appointment_response.text
    appointment_id = appointment_response.json()["id"]
    appointment_deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/appointments/{appointment_id}",
        headers=auth_headers,
    )
    assert appointment_deleted.status_code == 200, appointment_deleted.text

    invoice = Invoice(
        clinic_id=clinic_id,
        patient_id=patient_id,
        invoice_number="RECYCLE-ATTRIBUTION-001",
        issue_date=datetime.now(timezone.utc),
        subtotal=Decimal("10.00"),
        total_amount=Decimal("10.00"),
        status=InvoiceStatus.ISSUED,
    )
    document = PatientDocument(
        clinic_id=clinic_id,
        patient_id=patient_id,
        uploaded_by=user_id,
        file_url="https://example.test/file.pdf",
        file_type="application/pdf",
        label="Recycle attribution document",
        category=DocumentCategory.OTHER,
    )
    db_session.add_all([invoice, document])
    await db_session.flush()

    invoice_deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/invoices/{invoice.id}", headers=auth_headers
    )
    assert invoice_deleted.status_code == 204, invoice_deleted.text
    document_deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/documents/{document.id}", headers=auth_headers
    )
    assert document_deleted.status_code == 204, document_deleted.text

    for resource, resource_id in (
        ("lead", UUID(lead_id)),
        ("appointment", UUID(appointment_id)),
        ("invoice", invoice.id),
        ("document", document.id),
    ):
        result = await client.get(
            f"{settings.API_V1_PREFIX}/recycle-bin",
            params={"resource_type": resource},
            headers=auth_headers,
        )
        assert result.status_code == 200, result.text
        item = next(row for row in result.json()["items"] if row["id"] == str(resource_id))
        assert item["deleted_by"] == str(user_id)
        assert item["deleted_at"]


@pytest.mark.asyncio
async def test_recycle_bin_list_and_restore_are_clinic_scoped(client, auth_headers):
    registered = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "clinic_name": "Recycle Isolation Clinic",
            "email": "recycle-isolation-test@avsuite.com",
            "password": "Password123!",
            "first_name": "Recycle",
            "last_name": "Admin",
        },
    )
    assert registered.status_code in (200, 201), registered.text
    other_headers = {
        "Authorization": f"Bearer {registered.json()['data']['access_token']}",
        "Content-Type": "application/json",
    }
    patient = await client.post(
        f"{settings.API_V1_PREFIX}/patients",
        json={"first_name": "Other", "last_name": "Clinic", "phone": "9876509876"},
        headers=other_headers,
    )
    assert patient.status_code in (200, 201), patient.text
    patient_id = patient.json()["data"]["id"]
    deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=other_headers
    )
    assert deleted.status_code == 200, deleted.text

    own_bin = await client.get(
        f"{settings.API_V1_PREFIX}/recycle-bin",
        params={"resource_type": "patient"},
        headers=auth_headers,
    )
    assert own_bin.status_code == 200, own_bin.text
    assert all(item["id"] != patient_id for item in own_bin.json()["items"])

    cross_clinic_restore = await client.post(
        f"{settings.API_V1_PREFIX}/recycle-bin/patient/{patient_id}/restore",
        headers=auth_headers,
    )
    assert cross_clinic_restore.status_code == 404

