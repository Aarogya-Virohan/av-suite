from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.enums.shared import Specialty
from app.enums.user import UserRole
from app.models.billing import Invoice, InvoiceCounter
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.treatment import SoapAssessment
from app.models.user import User
from app.repositories.appointment import AppointmentRepository
from app.repositories.billing import (
    InvoiceItemRepository, InvoiceRepository, PackageRepository,
    PatientPackageRepository, PaymentRepository,
)
from app.repositories.patient import PatientRepository
from app.schemas.common import PaginationParams
from app.schemas.treatment import SoapAssessmentCreate
from app.services import patient_service
from app.services.billing import BillingService

pytestmark = pytest.mark.asyncio


async def _patient(db: AsyncSession, clinic_id, name: str, *, status="active", deleted=False):
    patient = Patient(
        clinic_id=clinic_id,
        first_name=name,
        last_name="Regression",
        phone=f"{uuid.uuid4().int % 10**10:010d}",
        status=status,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    db.add(patient)
    await db.flush()
    return patient


async def _workspace_user(db: AsyncSession, count: int):
    clinics = [Clinic(name=f"Login Workspace {uuid.uuid4()}") for _ in range(count)]
    db.add_all(clinics)
    await db.flush()
    user = User(
        clinic_id=clinics[0].id,
        email=f"multi-{uuid.uuid4()}@example.com",
        password_hash=get_password_hash("Correct-Pass123!"),
        role=UserRole.ADMIN,
        first_name="Test",
        last_name="Member",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    db.add_all([
        Membership(user_id=user.id, clinic_id=clinic.id, role=role)
        for clinic, role in zip(clinics, [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK][:count])
    ])
    await db.commit()
    return user, clinics


async def test_patient_status_search_deleted_pagination_and_clinic_isolation(db_session, client):
    clinic_a = Clinic(name=f"Patient filter clinic {uuid.uuid4()}")
    clinic_b = Clinic(name=f"Other clinic {uuid.uuid4()}")
    db_session.add_all([clinic_a, clinic_b])
    await db_session.flush()
    user = User(
        clinic_id=clinic_a.id, email=f"patient-filter-{uuid.uuid4()}@example.test",
        password_hash=get_password_hash("Correct-Pass123!"), role=UserRole.ADMIN,
        first_name="Filter", last_name="Admin", is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(Membership(user_id=user.id, clinic_id=clinic_a.id, role=UserRole.ADMIN))

    matching = await _patient(db_session, clinic_a.id, "Status Match", status="active")
    matching_two = await _patient(db_session, clinic_a.id, "Status Match Two", status="active")
    await _patient(db_session, clinic_a.id, "Status Mismatch", status="inactive")
    deleted = await _patient(db_session, clinic_a.id, "Deleted Match", deleted=True)
    await _patient(db_session, clinic_b.id, "Foreign Match")
    await db_session.commit()

    headers = {"Authorization": "Bearer " + create_access_token(
        subject=user.id, clinic_id=clinic_a.id, role="admin"
    )}

    listing = await client.get(f"{settings.API_V1_PREFIX}/patients?status=active&page=1&page_size=1", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] == 2
    assert len(listing.json()["data"]) == 1
    page_two = await client.get(
        f"{settings.API_V1_PREFIX}/patients?status=active&page=2&page_size=1",
        headers=headers,
    )
    assert page_two.status_code == 200
    assert page_two.json()["meta"]["total"] == 2
    assert len(page_two.json()["data"]) == 1
    assert {listing.json()["data"][0]["id"], page_two.json()["data"][0]["id"]} == {
        str(matching.id), str(matching_two.id)
    }

    search = await client.get(
        f"{settings.API_V1_PREFIX}/patients?search=Status&status=active&page_size=20",
        headers=headers,
    )
    assert search.status_code == 200
    ids = {row["id"] for row in search.json()["data"]}
    assert ids == {str(matching.id), str(matching_two.id)}
    assert str(deleted.id) not in ids
    assert all(row["id"] != str(deleted.id) for row in listing.json()["data"])

    # Service-level pages retain their clinic scope and deleted row exclusion.
    rows, total = await patient_service.get_patients(
        db_session, str(clinic_a.id), PaginationParams(page=1, page_size=20), status="active"
    )
    assert total == 2
    assert {row.clinic_id for row in rows} == {clinic_a.id}
    assert {row.id for row in rows} == {matching.id, matching_two.id}
    no_filter, no_filter_total = await patient_service.get_patients(
        db_session, str(clinic_a.id), PaginationParams(page=1, page_size=20)
    )
    assert no_filter_total == 3
    assert {
        row.status.value if hasattr(row.status, "value") else row.status
        for row in no_filter
    } == {"active", "inactive"}


async def test_login_workspace_selection_and_authentication_disclosure(client, db_session):
    one_user, _ = await _workspace_user(db_session, 1)
    login_url = f"{settings.API_V1_PREFIX}/auth/login"
    result = await client.post(login_url, json={"email": one_user.email, "password": "Correct-Pass123!"})
    assert result.status_code == 200, result.text

    user, clinics = await _workspace_user(db_session, 2)
    base = {"email": user.email, "password": "Correct-Pass123!"}
    missing = await client.post(login_url, json=base)
    assert missing.status_code == 400
    detail = missing.json()["detail"]
    assert detail["code"] == "WORKSPACE_SELECTION_REQUIRED"
    listed = {row["clinic_id"]: row for row in detail["workspaces"]}
    assert set(listed) == {str(c.id) for c in clinics}
    assert {row["name"] for row in listed.values()} == {c.name for c in clinics}
    assert {row["role"] for row in listed.values()} == {"admin", "therapist"}

    success = await client.post(login_url, json={**base, "clinic_id": str(clinics[1].id)})
    assert success.status_code == 200
    outsider = Clinic(name=f"Not member {uuid.uuid4()}")
    db_session.add(outsider)
    await db_session.commit()
    forbidden = await client.post(login_url, json={**base, "clinic_id": str(outsider.id)})
    assert forbidden.status_code == 403

    invalid = await client.post(login_url, json={"email": user.email, "password": "wrong"})
    assert invalid.status_code == 401
    assert "workspaces" not in invalid.text
    assert "WORKSPACE_SELECTION_REQUIRED" not in invalid.text


async def test_specialty_values_validate_persist_and_are_accepted_by_api(db_session, client):
    clinic = await db_session.scalar(select(Clinic).limit(1))
    patient = await _patient(db_session, clinic.id, "Specialty Patient")
    canonical = [value.value for value in Specialty]
    assert len(canonical) == 12
    for specialty in canonical:
        payload = SoapAssessmentCreate(patient_id=patient.id, specialty=specialty)
        assert payload.specialty.value == specialty
        db_session.add(SoapAssessment(
            clinic_id=clinic.id, patient_id=patient.id, specialty=payload.specialty,
            form_data={}, is_reassessment=False, finalized=False,
        ))
    await db_session.flush()
    stored = set((await db_session.scalars(select(SoapAssessment.specialty))).all())
    assert {value.value for value in stored} >= set(canonical)
    with pytest.raises(ValidationError):
        SoapAssessmentCreate(patient_id=patient.id, specialty="not-a-specialty")
    user = await db_session.scalar(select(User).where(User.clinic_id == clinic.id))
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role="admin")
    for specialty in canonical:
        response = await client.post(
            f"{settings.API_V1_PREFIX}/assessments",
            headers={"Authorization": f"Bearer {token}"},
            json={"patient_id": str(patient.id), "specialty": specialty},
        )
        assert response.status_code == 201, response.text
    invalid = await client.post(
        f"{settings.API_V1_PREFIX}/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"patient_id": str(patient.id), "specialty": "not-a-specialty"},
    )
    assert invalid.status_code == 422


async def _billing_service(session: AsyncSession) -> BillingService:
    return BillingService(
        PackageRepository(session), PatientPackageRepository(session),
        InvoiceRepository(session), InvoiceItemRepository(session),
        PaymentRepository(session), PatientRepository(session),
        AppointmentRepository(session),
    )


def _invoice_payload(patient_id):
    from app.schemas.billing import InvoiceCreate
    return InvoiceCreate(
        patient_id=patient_id, invoice_number="caller-value-is-ignored",
        issue_date=datetime.now(timezone.utc), items=[], line_items=[],
    )


async def test_invoice_numbers_are_per_clinic_sequential_seeded_and_unique(db_session, sessionmaker):
    clinic_a = Clinic(name=f"Invoice clinic A {uuid.uuid4()}")
    clinic_b = Clinic(name=f"Invoice clinic B {uuid.uuid4()}")
    db_session.add_all([clinic_a, clinic_b])
    await db_session.flush()
    patient_a = await _patient(db_session, clinic_a.id, "Invoice Patient A")
    patient_b = await _patient(db_session, clinic_b.id, "Invoice Patient B")
    await db_session.commit()

    first_a = await (await _billing_service(db_session)).create_invoice(clinic_a.id, _invoice_payload(patient_a.id))
    second_a = await (await _billing_service(db_session)).create_invoice(clinic_a.id, _invoice_payload(patient_a.id))
    first_b = await (await _billing_service(db_session)).create_invoice(clinic_b.id, _invoice_payload(patient_b.id))
    assert (first_a.invoice_number, second_a.invoice_number, first_b.invoice_number) == (
        "INV-0001", "INV-0002", "INV-0001"
    )

    # Existing formatted invoice and its migration-seeded counter are retained.
    clinic_existing = Clinic(name=f"Existing invoice clinic {uuid.uuid4()}")
    db_session.add(clinic_existing)
    await db_session.flush()
    patient_existing = await _patient(db_session, clinic_existing.id, "Existing Invoice Patient")
    legacy = Invoice(
        clinic_id=clinic_existing.id, patient_id=patient_existing.id, invoice_number="INV-0007",
        issue_date=datetime.now(timezone.utc), subtotal=Decimal("0"),
        total_amount=Decimal("0"), paid_amount=Decimal("0"), status="issued",
    )
    db_session.add_all([legacy, InvoiceCounter(clinic_id=clinic_existing.id, last_number=7)])
    await db_session.commit()

    async with sessionmaker() as session:
        next_existing = await (await _billing_service(session)).create_invoice(
            clinic_existing.id, _invoice_payload(patient_existing.id)
        )
    assert next_existing.invoice_number == "INV-0008"
    assert legacy.invoice_number == "INV-0007"

    duplicate = Invoice(
        clinic_id=clinic_existing.id, patient_id=patient_existing.id, invoice_number="INV-0007",
        issue_date=datetime.now(timezone.utc), subtotal=Decimal("0"),
        total_amount=Decimal("0"), paid_amount=Decimal("0"), status="issued",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_concurrent_invoice_number_generation_is_unique(db_session, sessionmaker):
    clinic = Clinic(name=f"Concurrent invoice clinic {uuid.uuid4()}")
    db_session.add(clinic)
    await db_session.flush()
    patient = await _patient(db_session, clinic.id, "Concurrent Invoice Patient")
    await db_session.commit()

    async def create_one():
        async with sessionmaker() as session:
            invoice = await (await _billing_service(session)).create_invoice(
                clinic.id, _invoice_payload(patient.id)
            )
            return invoice.invoice_number

    numbers = await asyncio.gather(*(create_one() for _ in range(8)))
    assert sorted(numbers) == [f"INV-{n:04d}" for n in range(1, 9)]


async def test_auth_me_includes_clinic_slug(client, db_session):
    clinic = await db_session.scalar(select(Clinic).limit(1))
    clinic.slug = f"auth-slug-{uuid.uuid4().hex[:8]}"
    user = await db_session.scalar(select(User).where(User.clinic_id == clinic.id))
    await db_session.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role="admin")
    response = await client.get(
        f"{settings.API_V1_PREFIX}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["clinic"]["slug"] == clinic.slug


async def test_uuid_branding_lookup_returns_canonical_clinic_slug(client, db_session):
    clinic = await db_session.scalar(select(Clinic).limit(1))
    clinic.slug = f"brand-slug-{uuid.uuid4().hex[:8]}"
    await db_session.commit()
    response = await client.get(f"{settings.API_V1_PREFIX}/booking/branding/{clinic.id}")
    assert response.status_code == 200
    assert response.json()["data"]["slug"] == clinic.slug
    assert response.json()["data"]["slug"] != str(clinic.id)
