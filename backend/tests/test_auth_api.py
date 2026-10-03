import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_auth_register_and_login_flow(client: AsyncClient):
    # 1. Test registration
    register_payload = {
        "email": "admin_flow_test@aarogya.com",
        "password": "Password123!",
        "clinic_name": "Aarogya Flow Test Center",
        "first_name": "Flow",
        "last_name": "Admin"
    }
    reg_response = await client.post(f"{settings.API_V1_PREFIX}/auth/register", json=register_payload)
    assert reg_response.status_code in (200, 201)
    reg_json = reg_response.json()
    assert "access_token" in reg_json.get("data", reg_json)

    # 2. Test login with correct credentials
    login_payload = {
        "email": "admin_flow_test@aarogya.com",
        "password": "Password123!",
    }
    login_response = await client.post(f"{settings.API_V1_PREFIX}/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_json = login_response.json()
    token = login_json.get("data", login_json).get("access_token")
    assert token is not None

    # 3. Test login with invalid password
    bad_login_payload = {
        "email": "admin_flow_test@aarogya.com",
        "password": "WrongPassword!",
    }
    bad_response = await client.post(f"{settings.API_V1_PREFIX}/auth/login", json=bad_login_payload)
    assert bad_response.status_code == 401
