import pytest
from httpx import AsyncClient
from app.core.config import settings

pytestmark = pytest.mark.asyncio

async def test_clinic_isolation(client: AsyncClient):
    # 1. Register Clinic A and User A (admin)
    reg_response_a = await client.post(f"{settings.API_V1_PREFIX}/auth/register", json={
        "clinic_name": "Clinic A",
        "email": "admin_a@test.com",
        "password": "password123",
        "first_name": "Admin",
        "last_name": "A"
    })
    assert reg_response_a.status_code == 201
    token_a = reg_response_a.json()["data"]["access_token"]
    
    # 2. Register Clinic B and User B (admin)
    reg_response_b = await client.post(f"{settings.API_V1_PREFIX}/auth/register", json={
        "clinic_name": "Clinic B",
        "email": "admin_b@test.com",
        "password": "password123",
        "first_name": "Admin",
        "last_name": "B"
    })
    assert reg_response_b.status_code == 201
    token_b = reg_response_b.json()["data"]["access_token"]

    # 3. Create an exercise in Clinic A
    headers_a = {"Authorization": f"Bearer {token_a}"}
    ex_response_a = await client.post(f"{settings.API_V1_PREFIX}/exercises", json={
        "title": "Exercise A",
        "description": "Desc A",
        "is_free": False
    }, headers=headers_a)
    assert ex_response_a.status_code == 201
    ex_a_id = ex_response_a.json()["data"]["id"]

    # 4. Create an exercise in Clinic B
    headers_b = {"Authorization": f"Bearer {token_b}"}
    ex_response_b = await client.post(f"{settings.API_V1_PREFIX}/exercises", json={
        "title": "Exercise B",
        "description": "Desc B",
        "is_free": False
    }, headers=headers_b)
    assert ex_response_b.status_code == 201
    ex_b_id = ex_response_b.json()["data"]["id"]

    # 5. List exercises as Clinic A's admin and verify isolation
    list_response_a = await client.get(f"{settings.API_V1_PREFIX}/exercises", headers=headers_a)
    assert list_response_a.status_code == 200
    exercises_a = list_response_a.json()["data"]
    
    # We should see Exercise A, but not Exercise B
    exercise_ids = [ex["id"] for ex in exercises_a]
    assert ex_a_id in exercise_ids
    assert ex_b_id not in exercise_ids

    # 6. Verify GET /{id} isolation
    get_b_with_a = await client.get(f"{settings.API_V1_PREFIX}/exercises/{ex_b_id}", headers=headers_a)
    assert get_b_with_a.status_code == 404
