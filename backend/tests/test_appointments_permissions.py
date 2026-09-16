"""
Focused scoped-permission tests for the Appointments module (Rev 3).

Coverage:
  - unauthenticated → 401
  - missing view permission → 403
  - own scope returns only own records
  - all scope returns all same-clinic records
  - own cannot access another therapist's appointment (GET /{id} → 403)
  - all cannot cross clinic boundaries (→ 404 via repo scoping)
  - create permission enforcement (none → 403, granted → 201)
  - own create cannot assign to another therapist → 403
  - edit permission enforcement (own cannot update another's appt → 403)
  - all can edit any same-clinic appointment
  - own cannot reassign therapist → 403
  - delete (soft-cancel) permission enforcement
  - clinic isolation via repository layer
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.permission import CapabilityScope
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.user_permission import UserPermission

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _set_permission(
    db: AsyncSession,
    user_id,
    clinic_id,
    key: str,
    scope: CapabilityScope,
) -> None:
    """Upsert a UserPermission override for one capability."""
    stmt = select(UserPermission).where(
        UserPermission.user_id == user_id,
        UserPermission.clinic_id == clinic_id,
        UserPermission.capability_key == key,
    )
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        await db.delete(existing)
        await db.commit()

    perm = UserPermission(
        user_id=user_id,
        clinic_id=clinic_id,
        capability_key=key,
        scope=scope,
    )
    db.add(perm)
    await db.commit()


async def _clear_permissions(db: AsyncSession, user_id) -> None:
    """Remove all explicit overrides so role-template defaults apply."""
    stmt = select(UserPermission).where(UserPermission.user_id == user_id)
    for p in (await db.execute(stmt)).scalars().all():
        await db.delete(p)
    await db.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def seeded_patient(db_session: AsyncSession) -> Patient:
    """Return (or create) a test patient in the seeded clinic."""
    stmt = select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
    clinic = (await db_session.execute(stmt)).scalars().first()

    stmt = select(Patient).where(Patient.first_name == "ApptTest", Patient.last_name == "Patient")
    pat = (await db_session.execute(stmt)).scalars().first()
    if not pat:
        pat = Patient(
            id=uuid4(),
            clinic_id=clinic.id,
            first_name="ApptTest",
            last_name="Patient",
            phone="9000000001",
            gender="male",
            date_of_birth=datetime(1990, 6, 15).date(),
        )
        db_session.add(pat)
        await db_session.commit()
    return pat


@pytest.fixture
async def other_therapist(db_session: AsyncSession) -> User:
    """Return (or create) a second therapist in the seeded clinic."""
    stmt = select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
    clinic = (await db_session.execute(stmt)).scalars().first()

    stmt = select(User).where(User.email == "appt_other_therapist@avtest.com")
    t = (await db_session.execute(stmt)).scalars().first()
    if not t:
        t = User(
            id=uuid4(),
            clinic_id=clinic.id,
            email="appt_other_therapist@avtest.com",
            password_hash="hash",
            role="therapist",
            first_name="Other",
            last_name="ApptTherapist",
            phone="9000000002",
            is_active=True,
        )
        db_session.add(t)
        await db_session.commit()
    return t


@pytest.fixture
async def appointments(
    db_session: AsyncSession,
    seeded_patient: Patient,
    other_therapist: User,
) -> tuple[Appointment, Appointment]:
    """
    Create two appointments in the seeded clinic:
      - appt_own  → owned by therapist@avtest.com (the default test therapist)
      - appt_other → owned by other_therapist
    Cleans up stale records first, and resets the therapist's explicit overrides.
    """
    stmt = select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
    clinic = (await db_session.execute(stmt)).scalars().first()

    stmt = select(User).where(User.email == "therapist@avtest.com")
    therapist = (await db_session.execute(stmt)).scalar_one()

    # Purge leftover appointments for this patient
    stmt = select(Appointment).where(Appointment.patient_id == seeded_patient.id)
    for a in (await db_session.execute(stmt)).scalars().all():
        await db_session.delete(a)
    await db_session.commit()

    appt_own = Appointment(
        id=uuid4(),
        clinic_id=clinic.id,
        patient_id=seeded_patient.id,
        therapist_id=therapist.id,
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
    )
    appt_other = Appointment(
        id=uuid4(),
        clinic_id=clinic.id,
        patient_id=seeded_patient.id,
        therapist_id=other_therapist.id,
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
    )
    db_session.add_all([appt_own, appt_other])
    await db_session.commit()

    # Reset explicit overrides so role-template defaults apply
    await _clear_permissions(db_session, therapist.id)

    return appt_own, appt_other


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_unauthenticated_list(client: AsyncClient) -> None:
    """No token → 401."""
    response = await client.get("/api/v1/appointments")
    assert response.status_code == 401


async def test_unauthenticated_get(client: AsyncClient) -> None:
    """No token on GET /{id} → 401."""
    response = await client.get(f"/api/v1/appointments/{uuid4()}")
    assert response.status_code == 401


async def test_no_view_permission(
    client: AsyncClient,
    frontdesk_auth_headers: dict,
    db_session: AsyncSession,
) -> None:
    """Front desk with explicit NONE override on appointments.view → 403."""
    stmt = select(User).where(User.email == "frontdesk@avtest.com")
    user = (await db_session.execute(stmt)).scalar_one()

    await _set_permission(db_session, user.id, user.clinic_id, "appointments.view", CapabilityScope.NONE)

    response = await client.get("/api/v1/appointments", headers=frontdesk_auth_headers)
    assert response.status_code == 403

    # Restore default
    await _clear_permissions(db_session, user.id)


async def test_view_own_scope_list(
    client: AsyncClient,
    therapist_auth_headers: dict,
    appointments: tuple,
) -> None:
    """Therapist (OWN by role template) sees only their own appointments."""
    appt_own, appt_other = appointments
    response = await client.get("/api/v1/appointments", headers=therapist_auth_headers)
    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data["items"]]
    assert str(appt_own.id) in ids
    assert str(appt_other.id) not in ids


async def test_view_own_cannot_access_other(
    client: AsyncClient,
    therapist_auth_headers: dict,
    appointments: tuple,
) -> None:
    """Therapist (OWN) cannot GET another therapist's appointment → 403."""
    _, appt_other = appointments
    response = await client.get(f"/api/v1/appointments/{appt_other.id}", headers=therapist_auth_headers)
    assert response.status_code == 403


async def test_view_all_scope_list(
    client: AsyncClient,
    auth_headers: dict,
    appointments: tuple,
) -> None:
    """Admin (ALL) sees both same-clinic appointments."""
    appt_own, appt_other = appointments
    response = await client.get("/api/v1/appointments", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data["items"]]
    assert str(appt_own.id) in ids
    assert str(appt_other.id) in ids


async def test_view_all_get_own(
    client: AsyncClient,
    auth_headers: dict,
    appointments: tuple,
) -> None:
    """Admin (ALL) can GET any same-clinic appointment."""
    appt_own, _ = appointments
    response = await client.get(f"/api/v1/appointments/{appt_own.id}", headers=auth_headers)
    assert response.status_code == 200


async def test_cross_clinic_access_denied(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    seeded_patient: Patient,
    other_therapist: User,
) -> None:
    """Admin (ALL on their clinic) cannot access a cross-clinic appointment → 404."""
    other_clinic = Clinic(id=uuid4(), name="CrossClinic Test", plan_tier="clinical_pro", is_partner_clinic=True)
    db_session.add(other_clinic)
    await db_session.commit()

    cross_appt = Appointment(
        id=uuid4(),
        clinic_id=other_clinic.id,
        patient_id=seeded_patient.id,
        therapist_id=other_therapist.id,
        scheduled_at=datetime.now(timezone.utc),
        duration_minutes=30,
    )
    db_session.add(cross_appt)
    await db_session.commit()

    response = await client.get(f"/api/v1/appointments/{cross_appt.id}", headers=auth_headers)
    # Clinic-scoped lookup returns 404 — correct isolation
    assert response.status_code == 404


async def test_create_no_permission(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_patient: Patient,
    other_therapist: User,
) -> None:
    """User with NONE on appointments.create → 403."""
    from app.core.security import create_access_token

    stmt = select(User).where(User.email == "admin@avtest.com")
    admin = (await db_session.execute(stmt)).scalar_one()
    await _set_permission(db_session, admin.id, admin.clinic_id, "appointments.create", CapabilityScope.NONE)

    try:
        token = create_access_token(
            subject=str(admin.id),
            clinic_id=str(admin.clinic_id),
            role="admin",
        )
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        payload = {
            "patient_id": str(seeded_patient.id),
            "therapist_id": str(admin.id),
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "duration_minutes": 30,
        }
        response = await client.post("/api/v1/appointments", json=payload, headers=headers)
        assert response.status_code == 403
    finally:
        # Always restore so this test cannot contaminate subsequent tests
        await _clear_permissions(db_session, admin.id)


async def test_create_own_must_be_self(
    client: AsyncClient,
    therapist_auth_headers: dict,
    seeded_patient: Patient,
    other_therapist: User,
) -> None:
    """Therapist (OWN) cannot create an appointment for another therapist → 403."""
    payload = {
        "patient_id": str(seeded_patient.id),
        "therapist_id": str(other_therapist.id),
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "duration_minutes": 30,
    }
    response = await client.post("/api/v1/appointments", json=payload, headers=therapist_auth_headers)
    assert response.status_code == 403


async def test_create_all_scope(
    client: AsyncClient,
    auth_headers: dict,
    seeded_patient: Patient,
    other_therapist: User,
) -> None:
    """Admin (ALL) can create an appointment for any therapist in the clinic."""
    payload = {
        "patient_id": str(seeded_patient.id),
        "therapist_id": str(other_therapist.id),
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "duration_minutes": 45,
    }
    response = await client.post("/api/v1/appointments", json=payload, headers=auth_headers)
    assert response.status_code == 201


async def test_edit_own_cannot_update_other(
    client: AsyncClient,
    therapist_auth_headers: dict,
    appointments: tuple,
) -> None:
    """Therapist (OWN) cannot PATCH another therapist's appointment → 403."""
    _, appt_other = appointments
    response = await client.patch(
        f"/api/v1/appointments/{appt_other.id}",
        json={"duration_minutes": 60},
        headers=therapist_auth_headers,
    )
    assert response.status_code == 403


async def test_edit_all_can_update_any(
    client: AsyncClient,
    auth_headers: dict,
    appointments: tuple,
) -> None:
    """Admin (ALL) can PATCH any same-clinic appointment."""
    _, appt_other = appointments
    response = await client.patch(
        f"/api/v1/appointments/{appt_other.id}",
        json={"duration_minutes": 60},
        headers=auth_headers,
    )
    assert response.status_code == 200


async def test_edit_own_cannot_reassign(
    client: AsyncClient,
    therapist_auth_headers: dict,
    appointments: tuple,
    other_therapist: User,
) -> None:
    """Therapist (OWN) cannot reassign their own appointment to another therapist → 403."""
    appt_own, _ = appointments
    response = await client.patch(
        f"/api/v1/appointments/{appt_own.id}",
        json={"therapist_id": str(other_therapist.id)},
        headers=therapist_auth_headers,
    )
    assert response.status_code == 403


async def test_delete_own_cannot_cancel_other(
    client: AsyncClient,
    therapist_auth_headers: dict,
    appointments: tuple,
) -> None:
    """Therapist (OWN) cannot soft-cancel another therapist's appointment → 403."""
    _, appt_other = appointments
    response = await client.delete(
        f"/api/v1/appointments/{appt_other.id}",
        headers=therapist_auth_headers,
    )
    assert response.status_code == 403


async def test_delete_all_can_cancel_any(
    client: AsyncClient,
    auth_headers: dict,
    appointments: tuple,
) -> None:
    """Admin (ALL) can soft-cancel any same-clinic appointment."""
    appt_own, _ = appointments
    response = await client.delete(
        f"/api/v1/appointments/{appt_own.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_frontdesk_can_view_and_create(
    client: AsyncClient,
    frontdesk_auth_headers: dict,
    db_session: AsyncSession,
    seeded_patient: Patient,
    other_therapist: User,
) -> None:
    """Front desk (ALL for view/create by role template) can list and create appointments."""
    # List
    list_response = await client.get("/api/v1/appointments", headers=frontdesk_auth_headers)
    assert list_response.status_code == 200

    # Create
    payload = {
        "patient_id": str(seeded_patient.id),
        "therapist_id": str(other_therapist.id),
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "duration_minutes": 30,
    }
    create_response = await client.post("/api/v1/appointments", json=payload, headers=frontdesk_auth_headers)
    assert create_response.status_code == 201


async def test_frontdesk_cannot_edit(
    client: AsyncClient,
    frontdesk_auth_headers: dict,
    appointments: tuple,
) -> None:
    """Front desk has NONE for appointments.edit (not in role template) → 403."""
    appt_own, _ = appointments
    response = await client.patch(
        f"/api/v1/appointments/{appt_own.id}",
        json={"duration_minutes": 45},
        headers=frontdesk_auth_headers,
    )
    assert response.status_code == 403
