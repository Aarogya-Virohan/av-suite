"""bcrypt 5 rejects passwords over 72 bytes; the API must answer 422, not 500."""

import pytest
from httpx import AsyncClient

from app.core.config import settings

REGISTER = f"{settings.API_V1_PREFIX}/auth/register"


def _register(email: str, password: str) -> dict:
    return {
        "clinic_name": "Password Length Clinic",
        "email": email,
        "password": password,
        "first_name": "Len",
        "last_name": "Test",
    }


@pytest.mark.asyncio
async def test_register_rejects_password_over_72_bytes(client: AsyncClient):
    res = await client.post(REGISTER, json=_register("len80@avtest.com", "a" * 80))
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_register_counts_bytes_not_characters(client: AsyncClient):
    # 25 Devanagari letters are 25 characters but 75 bytes in UTF-8.
    res = await client.post(REGISTER, json=_register("lenhindi@avtest.com", "क" * 25))
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_register_accepts_exactly_72_bytes_and_can_log_in(client: AsyncClient):
    password = "b" * 72
    res = await client.post(REGISTER, json=_register("len72@avtest.com", password))
    assert res.status_code in (200, 201), res.text
    login = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": "len72@avtest.com", "password": password},
    )
    assert login.status_code == 200, login.text


@pytest.mark.asyncio
async def test_user_create_rejects_password_over_72_bytes(client: AsyncClient, auth_headers):
    res = await client.post(
        f"{settings.API_V1_PREFIX}/users",
        headers=auth_headers,
        json={"name": "Long Pw", "email": "longpw@avtest.com", "password": "c" * 100, "role": "therapist", "is_active": True},
    )
    assert res.status_code == 422, res.text
