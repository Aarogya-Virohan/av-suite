import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timezone

from app.enums.permission import CapabilityScope
from app.models.user import User
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.treatment import TreatmentSession
from app.models.user_permission import UserPermission

pytestmark = pytest.mark.asyncio

async def create_user_permission(db_session: AsyncSession, user_id, clinic_id, key, scope):
    stmt = select(UserPermission).where(
        UserPermission.user_id == user_id,
        UserPermission.clinic_id == clinic_id,
        UserPermission.capability_key == key
    )
    existing = (await db_session.execute(stmt)).scalars().first()
    if existing:
        await db_session.delete(existing)
        await db_session.commit()

    perm = UserPermission(
        user_id=user_id,
        clinic_id=clinic_id,
        capability_key=key,
        scope=scope
    )
    db_session.add(perm)
    await db_session.commit()
    return perm

@pytest.fixture
async def patient(db_session: AsyncSession):
    stmt = select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
    clinic = (await db_session.execute(stmt)).scalars().first()
    
    # Check if patient exists
    stmt = select(Patient).where(Patient.first_name == "Test", Patient.last_name == "Pat")
    pat = (await db_session.execute(stmt)).scalars().first()
    if not pat:
        pat = Patient(id=uuid4(), clinic_id=clinic.id, first_name="Test", last_name="Pat", phone="1234567890", gender="male", date_of_birth=datetime(1990, 1, 1).date())
        db_session.add(pat)
        await db_session.commit()
    return pat

@pytest.fixture
async def other_therapist(db_session: AsyncSession):
    stmt = select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
    clinic = (await db_session.execute(stmt)).scalars().first()

    stmt = select(User).where(User.email == "other_therapist@avtest.com")
    t = (await db_session.execute(stmt)).scalars().first()
    if not t:
        t = User(id=uuid4(), clinic_id=clinic.id, email="other_therapist@avtest.com", password_hash="hash", role="therapist", first_name="Other", last_name="Therapist", phone="1111111111", is_active=True)
        db_session.add(t)
        await db_session.commit()
    return t

@pytest.fixture
async def treatment(db_session: AsyncSession, patient: Patient, other_therapist: User):
    stmt = select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
    clinic = (await db_session.execute(stmt)).scalars().first()

    stmt = select(User).where(User.email == "therapist@avtest.com")
    therapist = (await db_session.execute(stmt)).scalar_one()

    # Clean up previous tests
    stmt = select(TreatmentSession).where(TreatmentSession.patient_id == patient.id)
    for ts in (await db_session.execute(stmt)).scalars().all():
        await db_session.delete(ts)
    await db_session.commit()

    ts = TreatmentSession(
        id=uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        therapist_id=therapist.id,
        treatment_date=datetime.now(timezone.utc),
        treatment="Test treatment"
    )
    
    ts_other = TreatmentSession(
        id=uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        therapist_id=other_therapist.id,
        treatment_date=datetime.now(timezone.utc),
        treatment="Other treatment"
    )
    
    db_session.add_all([ts, ts_other])
    await db_session.commit()
    
    # Also clean up any UserPermission on therapist so that it falls back to ROLE_TEMPLATE
    stmt = select(UserPermission).where(UserPermission.user_id == therapist.id)
    for p in (await db_session.execute(stmt)).scalars().all():
        await db_session.delete(p)
    await db_session.commit()
    
    return ts, ts_other

async def test_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/treatments")
    assert response.status_code == 401

async def test_no_view_permission(client: AsyncClient, therapist_auth_headers: dict, db_session: AsyncSession):
    stmt = select(User).where(User.email == "therapist@avtest.com")
    user = (await db_session.execute(stmt)).scalar_one()
    await create_user_permission(db_session, user.id, user.clinic_id, "treatments.view", CapabilityScope.NONE)
    
    response = await client.get("/api/v1/treatments", headers=therapist_auth_headers)
    assert response.status_code == 403

async def test_view_own_scope(client: AsyncClient, therapist_auth_headers: dict, treatment):
    ts, ts_other = treatment
    # Therapist has OWN scope via role template
    response = await client.get("/api/v1/treatments", headers=therapist_auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Should only return the treatment assigned to this therapist
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(ts.id)

async def test_view_own_cannot_access_other(client: AsyncClient, therapist_auth_headers: dict, treatment):
    ts, ts_other = treatment
    response = await client.get(f"/api/v1/treatments/{ts_other.id}", headers=therapist_auth_headers)
    assert response.status_code == 403

async def test_view_all_scope(client: AsyncClient, auth_headers: dict, treatment):
    ts, ts_other = treatment
    # Admin has ALL scope via role template
    response = await client.get("/api/v1/treatments", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2

async def test_create_permission_enforcement(client: AsyncClient, frontdesk_auth_headers: dict, patient: Patient, db_session: AsyncSession):
    # Front desk has no template for treatments.create -> NONE -> 403
    stmt = select(User).where(User.email == "frontdesk@avtest.com")
    user = (await db_session.execute(stmt)).scalar_one()
    
    payload = {
        "patient_id": str(patient.id),
        "therapist_id": str(user.id),
        "treatment_date": datetime.now(timezone.utc).isoformat(),
        "treatment": "New treatment"
    }
    response = await client.post("/api/v1/treatments", json=payload, headers=frontdesk_auth_headers)
    assert response.status_code == 403

    # Override to ALL
    await create_user_permission(db_session, user.id, user.clinic_id, "treatments.create", CapabilityScope.ALL)
    response = await client.post("/api/v1/treatments", json=payload, headers=frontdesk_auth_headers)
    assert response.status_code == 201

async def test_create_own_must_be_self(client: AsyncClient, therapist_auth_headers: dict, patient: Patient, other_therapist: User):
    # Therapist has OWN scope. Try to create for other therapist
    payload = {
        "patient_id": str(patient.id),
        "therapist_id": str(other_therapist.id),
        "treatment_date": datetime.now(timezone.utc).isoformat(),
        "treatment": "New treatment"
    }
    response = await client.post("/api/v1/treatments", json=payload, headers=therapist_auth_headers)
    assert response.status_code == 403

async def test_edit_own_cannot_edit_other(client: AsyncClient, therapist_auth_headers: dict, treatment):
    ts, ts_other = treatment
    payload = {"treatment": "Updated"}
    response = await client.patch(f"/api/v1/treatments/{ts_other.id}", json=payload, headers=therapist_auth_headers)
    assert response.status_code == 403

async def test_edit_all_can_edit_any(client: AsyncClient, auth_headers: dict, treatment):
    ts, ts_other = treatment
    payload = {"treatment": "Updated"}
    response = await client.patch(f"/api/v1/treatments/{ts_other.id}", json=payload, headers=auth_headers)
    assert response.status_code == 200

async def test_edit_own_cannot_reassign(client: AsyncClient, therapist_auth_headers: dict, treatment, other_therapist: User):
    ts, ts_other = treatment
    payload = {"therapist_id": str(other_therapist.id)}
    response = await client.patch(f"/api/v1/treatments/{ts.id}", json=payload, headers=therapist_auth_headers)
    assert response.status_code == 403

async def test_cross_clinic_access_denied(client: AsyncClient, auth_headers: dict, db_session: AsyncSession, patient: Patient, other_therapist: User):
    # Admin has ALL scope. 
    # Create another clinic and treatment
    other_clinic = Clinic(id=uuid4(), name="Other", plan_tier="clinical_pro", is_partner_clinic=True)
    db_session.add(other_clinic)
    await db_session.commit()
    
    ts = TreatmentSession(
        id=uuid4(),
        clinic_id=other_clinic.id,
        patient_id=patient.id,
        therapist_id=other_therapist.id,
        treatment_date=datetime.now(timezone.utc),
        treatment="Other treatment"
    )
    db_session.add(ts)
    await db_session.commit()

    # Try to access it
    response = await client.get(f"/api/v1/treatments/{ts.id}", headers=auth_headers)
    assert response.status_code == 404 # 404 because get_by_id scopes by clinic
