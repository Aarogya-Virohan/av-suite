import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_patients_crud_operations(client: AsyncClient, auth_headers: dict):
    # 1. Create Patient
    patient_payload = {
        "first_name": "Ramesh",
        "last_name": "Sharma",
        "phone": "9876543210",
        "date_of_birth": "1990-05-15",
    }
    create_res = await client.post(f"{settings.API_V1_PREFIX}/patients", json=patient_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    create_data = create_res.json().get("data", create_res.json())
    patient_id = create_data.get("id")
    assert patient_id is not None
    assert create_data.get("first_name") == "Ramesh"

    # 2. List Patients
    list_res = await client.get(f"{settings.API_V1_PREFIX}/patients", headers=auth_headers)
    assert list_res.status_code == 200
    res_body = list_res.json().get("data", list_res.json())
    list_items = res_body.get("items") if isinstance(res_body, dict) else res_body
    assert isinstance(list_items, list)
    assert any(p["id"] == patient_id for p in list_items)

    # 3. Get Patient Detail
    get_res = await client.get(f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers)
    assert get_res.status_code == 200
    get_data = get_res.json().get("data", get_res.json())
    assert get_data["id"] == patient_id

    # 4. Patch/Update Patient
    update_res = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}",
        json={"first_name": "Ramesh Updated"},
        headers=auth_headers
    )
    assert update_res.status_code == 200

    # 5. Delete Patient (Soft Delete)
    delete_res = await client.delete(f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers)
    assert delete_res.status_code in (200, 204)
