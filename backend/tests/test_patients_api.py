import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.config import settings
from app.core.security import create_access_token
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User


async def _therapist_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        subject=str(user.id), clinic_id=str(user.clinic_id), role="therapist"
    )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
async def other_therapist(db_session: AsyncSession) -> User:
    clinic = (
        (
            await db_session.execute(
                select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic")
            )
        )
        .scalars()
        .one()
    )
    therapist = (
        (
            await db_session.execute(
                select(User).where(User.email == "patient_other_therapist@avtest.com")
            )
        )
        .scalars()
        .first()
    )
    if therapist is None:
        therapist = User(
            id=uuid4(),
            clinic_id=clinic.id,
            email="patient_other_therapist@avtest.com",
            password_hash="unused",
            role="therapist",
            first_name="Other",
            last_name="PatientTherapist",
            is_active=True,
        )
        db_session.add(therapist)
        await db_session.commit()
    return therapist


@pytest.mark.asyncio
async def test_patients_crud_operations(client: AsyncClient, auth_headers: dict):
    # 1. Create Patient
    patient_payload = {
        "first_name": "Ramesh",
        "last_name": "Sharma",
        "phone": "9876543210",
        "date_of_birth": "1990-05-15",
    }
    create_res = await client.post(
        f"{settings.API_V1_PREFIX}/patients", json=patient_payload, headers=auth_headers
    )
    assert create_res.status_code in (200, 201)
    create_data = create_res.json().get("data", create_res.json())
    patient_id = create_data.get("id")
    assert patient_id is not None
    assert create_data.get("first_name") == "Ramesh"

    # 2. List Patients
    list_res = await client.get(
        f"{settings.API_V1_PREFIX}/patients", headers=auth_headers
    )
    assert list_res.status_code == 200
    res_body = list_res.json().get("data", list_res.json())
    list_items = res_body.get("items") if isinstance(res_body, dict) else res_body
    assert isinstance(list_items, list)
    assert any(p["id"] == patient_id for p in list_items)

    # 3. Get Patient Detail
    get_res = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert get_res.status_code == 200
    get_data = get_res.json().get("data", get_res.json())
    assert get_data["id"] == patient_id

    # 4. Patch/Update Patient
    update_res = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}",
        json={"first_name": "Ramesh Updated"},
        headers=auth_headers,
    )
    assert update_res.status_code == 200

    # 5. Delete Patient (Soft Delete)
    delete_res = await client.delete(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert delete_res.status_code in (200, 204)


@pytest.mark.asyncio
async def test_patient_ownership_scopes(
    client: AsyncClient,
    db_session: AsyncSession,
    therapist_auth_headers: dict,
    auth_headers: dict,
    other_therapist: User,
):
    therapist = (
        (
            await db_session.execute(
                select(User).where(User.email == "therapist@avtest.com")
            )
        )
        .scalars()
        .one()
    )
    other_headers = await _therapist_headers(other_therapist)

    create_payload = {
        "first_name": "Owned",
        "last_name": "Patient",
        "phone": "9000000011",
        "user_id": str(other_therapist.id),
    }
    create_response = await client.post(
        f"{settings.API_V1_PREFIX}/patients",
        json=create_payload,
        headers=therapist_auth_headers,
    )
    assert create_response.status_code == 201
    owned_patient = create_response.json()["data"]
    assert owned_patient["user_id"] == str(therapist.id)

    other_patient_response = await client.post(
        f"{settings.API_V1_PREFIX}/patients",
        json={
            "first_name": "Other",
            "last_name": "Owned Patient",
            "phone": "9000000012",
        },
        headers=other_headers,
    )
    assert other_patient_response.status_code == 201
    other_patient = other_patient_response.json()["data"]
    assert other_patient["user_id"] == str(other_therapist.id)

    list_response = await client.get(
        f"{settings.API_V1_PREFIX}/patients", headers=therapist_auth_headers
    )
    assert list_response.status_code == 200
    listed_ids = {item["id"] for item in list_response.json()["data"]}
    assert owned_patient["id"] in listed_ids
    assert other_patient["id"] not in listed_ids

    search_response = await client.get(
        f"{settings.API_V1_PREFIX}/patients",
        params={"search": "Owned"},
        headers=therapist_auth_headers,
    )
    assert search_response.status_code == 200
    searched_ids = {item["id"] for item in search_response.json()["data"]}
    assert owned_patient["id"] in searched_ids
    assert other_patient["id"] not in searched_ids

    own_detail = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{owned_patient['id']}",
        headers=therapist_auth_headers,
    )
    assert own_detail.status_code == 200

    other_detail = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{other_patient['id']}",
        headers=therapist_auth_headers,
    )
    assert other_detail.status_code == 404

    own_update = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{owned_patient['id']}",
        json={"first_name": "Owned Updated", "user_id": str(other_therapist.id)},
        headers=therapist_auth_headers,
    )
    assert own_update.status_code == 200
    assert own_update.json()["data"]["user_id"] == str(therapist.id)

    other_update = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{other_patient['id']}",
        json={"first_name": "Should Not Update"},
        headers=therapist_auth_headers,
    )
    assert other_update.status_code == 404

    all_list = await client.get(
        f"{settings.API_V1_PREFIX}/patients", headers=auth_headers
    )
    assert all_list.status_code == 200
    all_ids = {item["id"] for item in all_list.json()["data"]}
    assert owned_patient["id"] in all_ids
    assert other_patient["id"] in all_ids

    all_update = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{other_patient['id']}",
        json={"first_name": "Admin Updated"},
        headers=auth_headers,
    )
    assert all_update.status_code == 200


@pytest.mark.asyncio
async def test_patient_cross_clinic_isolation(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    other_clinic = Clinic(
        id=uuid4(),
        name="Patient Isolation Clinic",
        plan_tier="clinical_pro",
        is_partner_clinic=True,
    )
    other_user = User(
        id=uuid4(),
        clinic_id=other_clinic.id,
        email="patient_isolation_admin@avtest.com",
        password_hash="unused",
        role="admin",
        first_name="Isolation",
        last_name="Admin",
        is_active=True,
    )
    other_patient = Patient(
        id=uuid4(),
        clinic_id=other_clinic.id,
        user_id=other_user.id,
        first_name="Cross",
        last_name="Clinic",
        phone="9000000013",
    )
    db_session.add_all([other_clinic, other_user, other_patient])
    await db_session.commit()

    response = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{other_patient.id}",
        headers=auth_headers,
    )
    assert response.status_code == 404
