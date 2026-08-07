import pytest
from httpx import AsyncClient
from app.core.config import settings
from jose import jwt

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
    decoded = jwt.decode(token, key="", options={"verify_signature": False})
    clinic_id = decoded["clinic_id"]
    user_id = decoded["sub"]

    # 3. Public Booking Request (Unauthenticated with clinic_id)
    booking_req_payload = {
        "name": "Vikas Verma",
        "phone": "9899887766",
        "age": 32,
        "gender": "Male",
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
