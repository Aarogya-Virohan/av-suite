import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_leads_crud_and_conversion_flow(client: AsyncClient, auth_headers: dict):
    # 1. Create Lead
    lead_payload = {
        "name": "Neha Kapoor",
        "phone": "9811122233",
        "email": "neha@example.com",
        "source": "social_media",
        "stage": "new",
        "notes": "Inquired for shoulder rehab"
    }
    create_res = await client.post(f"{settings.API_V1_PREFIX}/leads", json=lead_payload, headers=auth_headers)
    assert create_res.status_code in (200, 201)
    lead_data = create_res.json().get("data", create_res.json())
    lead_id = lead_data.get("id")
    assert lead_id is not None

    # 2. List Leads
    list_res = await client.get(f"{settings.API_V1_PREFIX}/leads", headers=auth_headers)
    assert list_res.status_code == 200
    res_body = list_res.json().get("data", list_res.json())
    list_data = res_body.get("items") if isinstance(res_body, dict) else res_body
    assert isinstance(list_data, list)
    assert any(l["id"] == lead_id for l in list_data)

    # 3. Update Lead Stage
    update_res = await client.patch(
        f"{settings.API_V1_PREFIX}/leads/{lead_id}",
        json={"stage": "qualified"},
        headers=auth_headers
    )
    assert update_res.status_code == 200
    assert update_res.json().get("data", update_res.json()).get("stage") == "qualified"

    # 4. Convert Lead to Patient
    convert_res = await client.post(f"{settings.API_V1_PREFIX}/leads/{lead_id}/convert", headers=auth_headers)
    assert convert_res.status_code == 200
    convert_data = convert_res.json().get("data", convert_res.json())
    assert convert_data.get("patient_id") is not None or convert_data.get("lead", {}).get("stage") == "converted"
