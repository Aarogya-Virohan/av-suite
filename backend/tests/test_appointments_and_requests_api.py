import pytest
from httpx import AsyncClient
from app.core.config import settings
import jwt

@pytest.mark.asyncio
async def test_public_booking_request_and_approval_flow(client: AsyncClient, auth_headers: dict):
    # 1. Staff View Pending Booking Requests
    list_req_res = await client.get(f"{settings.API_V1_PREFIX}/appointment-requests", headers=auth_headers)
    assert list_req_res.status_code == 200

    # 2. Register a clinic & get valid token and therapist/admin user ID
    reg_response = await client.post(f"{settings.API_V1_PREFIX}/auth/register", json={
        "clinic_name": "Booking Test Clinic",
        "email": "booking_admin@test.com",
        "password": "Password123!",
        "first_name": "Booking",
        "last_name": "Admin"
    })
    assert reg_response.status_code in (200, 201)
    token = reg_response.json()["data"]["access_token"]
    decoded = jwt.decode(token, options={"verify_signature": False})
    clinic_id = decoded["clinic_id"]
    user_id = decoded["sub"]

    # 3. Public Booking Request (Unauthenticated with clinic_id)
    booking_req_payload = {
        "name": "Vikas Verma",
        "phone": "9899887766",
        "age": 32,
        "gender": "male",
        "chief_complaint": "Acute neck spasm",
        "preferred_date": "2026-08-10",
        "preferred_slot": "10:00 AM",
        "notes": "Prefers morning session"
    }
    req_res = await client.post(f"{settings.API_V1_PREFIX}/booking/request?clinic_id={clinic_id}", json=booking_req_payload)
    assert req_res.status_code in (200, 201)

    # 4. Staff View Pending Requests for this clinic
    headers = {"Authorization": f"Bearer {token}"}
    list_req_res2 = await client.get(f"{settings.API_V1_PREFIX}/appointment-requests", headers=headers)
    assert list_req_res2.status_code == 200
    res_body = list_req_res2.json().get("data", list_req_res2.json())
    requests_list = res_body.get("items") if isinstance(res_body, dict) else res_body
    assert isinstance(requests_list, list)
    assert len(requests_list) > 0

    req_id = requests_list[0]["id"]
    
    # 5. Approve Request with valid therapist_id
    approve_res = await client.post(
        f"{settings.API_V1_PREFIX}/appointment-requests/{req_id}/approve",
        json={"therapist_id": user_id, "duration_minutes": 30},
        headers=headers
    )
    assert approve_res.status_code == 200
    approve_data = approve_res.json().get("data", approve_res.json())
    assert approve_data.get("appointment_id") is not None or approve_data.get("request", {}).get("status") == "approved"


@pytest.mark.asyncio
async def test_appointment_date_range_rejects_reversed_range(client, auth_headers):
    params = {"start_date": "2026-10-11", "end_date": "2026-10-10"}
    response = await client.get(f"{settings.API_V1_PREFIX}/appointments", params=params, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [
    {"start_date": "2026-10-10"},
    {"end_date": "2026-10-10"},
])
async def test_appointment_date_range_accepts_open_ranges(client, auth_headers, params):
    # Open ranges are allowed since D-028 (CRM Upcoming and Past lists); their
    # filtering is checked in test_appointment_list_order_and_ranges.py.
    response = await client.get(f"{settings.API_V1_PREFIX}/appointments", params=params, headers=auth_headers)
    assert response.status_code == 200, response.text
