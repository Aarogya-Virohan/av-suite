import pytest
from httpx import AsyncClient
from app.core.config import settings
import uuid

@pytest.mark.asyncio
async def test_patients_crud_admin(client: AsyncClient, auth_headers: dict):
    # Admin has ALL capabilities
    patient_payload = {
        "first_name": "Ramesh",
        "last_name": "Sharma",
        "phone": "9876543210",
        "date_of_birth": "1990-05-15",
    }
    # 1. Create Patient
    create_res = await client.post(f"{settings.API_V1_PREFIX}/patients", json=patient_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    patient_id = create_res.json()["data"]["id"]

    # 2. List Patients
    list_res = await client.get(f"{settings.API_V1_PREFIX}/patients", headers=auth_headers)
    assert list_res.status_code == 200
    assert any(p["id"] == patient_id for p in list_res.json()["data"])

    # 3. Get Patient Detail
    get_res = await client.get(f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers)
    assert get_res.status_code == 200

    # 4. Patch/Update Patient
    update_res = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}",
        json={"first_name": "Ramesh Updated"},
        headers=auth_headers
    )
    assert update_res.status_code == 200

    # 5. Delete Patient (Admin can delete)
    delete_res = await client.delete(f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers)
    assert delete_res.status_code == 200


@pytest.mark.asyncio
async def test_patients_crud_therapist_scope(client: AsyncClient, therapist_auth_headers: dict, auth_headers: dict):
    # Therapist has create=ALL, view=OWN, edit=OWN, delete=NONE
    
    # 1. Therapist creates patient
    patient_payload = {
        "first_name": "Therapist",
        "last_name": "Patient",
        "phone": "9876543211",
    }
    create_res = await client.post(f"{settings.API_V1_PREFIX}/patients", json=patient_payload, headers=therapist_auth_headers)
    assert create_res.status_code in (200, 201)
    patient_id = create_res.json()["data"]["id"]
    
    # Wait! Therapist just created the patient, but they don't have a treatment session yet.
    # Therefore, scope=OWN means they should NOT see the patient in the list right now!
    list_res = await client.get(f"{settings.API_V1_PREFIX}/patients", headers=therapist_auth_headers)
    assert list_res.status_code == 200
    # Patient should not be in the list for the therapist yet
    assert not any(p["id"] == patient_id for p in list_res.json()["data"])
    
    # 2. Therapist cannot delete
    delete_res = await client.delete(f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=therapist_auth_headers)
    assert delete_res.status_code == 403


@pytest.mark.asyncio
async def test_patients_crud_frontdesk(client: AsyncClient, frontdesk_auth_headers: dict):
    # Front Desk has view=ALL, create=ALL, edit=ALL, delete=NONE
    patient_payload = {
        "first_name": "FD",
        "last_name": "Patient",
        "phone": "9876543212",
    }
    create_res = await client.post(f"{settings.API_V1_PREFIX}/patients", json=patient_payload, headers=frontdesk_auth_headers)
    assert create_res.status_code in (200, 201)
    patient_id = create_res.json()["data"]["id"]
    
    # Front desk sees the patient because view=ALL
    list_res = await client.get(f"{settings.API_V1_PREFIX}/patients", headers=frontdesk_auth_headers)
    assert list_res.status_code == 200
    assert any(p["id"] == patient_id for p in list_res.json()["data"])
    
    # Front desk cannot delete
    delete_res = await client.delete(f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=frontdesk_auth_headers)
    assert delete_res.status_code == 403


@pytest.mark.asyncio
async def test_patient_list_status_filter_applies_to_search_and_rejects_invalid(
    client: AsyncClient, auth_headers: dict
):
    created_ids = {}
    for first_name, status_value in (("StatusActive", "active"), ("StatusInactive", "inactive")):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/patients",
            json={"first_name": first_name, "last_name": "Filter", "status": status_value},
            headers=auth_headers,
        )
        assert response.status_code in (200, 201)
        created_ids[first_name] = response.json()["data"]["id"]

    for params in ({"status": "inactive"}, {"status": "inactive", "search": "Status"}):
        response = await client.get(
            f"{settings.API_V1_PREFIX}/patients", params=params, headers=auth_headers
        )
        assert response.status_code == 200
        result_ids = {patient["id"] for patient in response.json()["data"]}
        assert created_ids["StatusInactive"] in result_ids
        assert created_ids["StatusActive"] not in result_ids

    invalid = await client.get(
        f"{settings.API_V1_PREFIX}/patients",
        params={"status": "archived"},
        headers=auth_headers,
    )
    assert invalid.status_code == 422
