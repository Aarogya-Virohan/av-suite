import pytest
from httpx import AsyncClient
from uuid import uuid4
from fastapi import status

# Using pytest.mark.asyncio for all tests in this file
pytestmark = pytest.mark.asyncio

async def test_front_desk_cannot_create_treatment(
    client: AsyncClient, frontdesk_auth_headers: dict
):
    """Front desk should not be able to create treatments (ADMIN, THERAPIST only)."""
    response = await client.post(
        "/api/v1/treatments",
        headers=frontdesk_auth_headers,
        json={"patient_id": str(uuid4()), "notes": "Test"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_front_desk_cannot_create_assessment(
    client: AsyncClient, frontdesk_auth_headers: dict
):
    """Front desk should not be able to create assessments (ADMIN, THERAPIST only)."""
    response = await client.post(
        "/api/v1/assessments",
        headers=frontdesk_auth_headers,
        json={"patient_id": str(uuid4()), "specialty": "Physiotherapy"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_therapist_cannot_access_settings(
    client: AsyncClient, therapist_auth_headers: dict
):
    """Therapist should not be able to read or update clinic settings (ADMIN only)."""
    # Test GET
    get_response = await client.get(
        "/api/v1/settings/clinic",
        headers=therapist_auth_headers
    )
    assert get_response.status_code == status.HTTP_403_FORBIDDEN

    # Test PATCH
    patch_response = await client.patch(
        "/api/v1/settings/clinic",
        headers=therapist_auth_headers,
        json={"clinic_name": "New Name"}
    )
    assert patch_response.status_code == status.HTTP_403_FORBIDDEN


async def test_front_desk_cannot_access_settings(
    client: AsyncClient, frontdesk_auth_headers: dict
):
    """Front desk should not be able to read or update clinic settings (ADMIN only)."""
    get_response = await client.get(
        "/api/v1/settings/clinic",
        headers=frontdesk_auth_headers
    )
    assert get_response.status_code == status.HTTP_403_FORBIDDEN


async def test_therapist_cannot_delete_patient(
    client: AsyncClient, therapist_auth_headers: dict
):
    """Therapist should not be able to delete a patient (ADMIN only)."""
    response = await client.delete(
        f"/api/v1/patients/{uuid4()}",
        headers=therapist_auth_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_therapist_cannot_manage_packages(
    client: AsyncClient, therapist_auth_headers: dict
):
    """Therapist should not be able to access billing/packages at all."""
    # Since billing router requires ADMIN or FRONT_DESK, this should be 403
    response = await client.post(
        "/api/v1/packages",
        headers=therapist_auth_headers,
        json={"name": "Test Package", "price": 100.0}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_front_desk_cannot_manage_packages(
    client: AsyncClient, frontdesk_auth_headers: dict
):
    """Front desk can access billing but NOT manage packages (ADMIN only override)."""
    response = await client.post(
        "/api/v1/packages",
        headers=frontdesk_auth_headers,
        json={"name": "Test Package", "price": 100.0}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_front_desk_cannot_access_analytics(
    client: AsyncClient, frontdesk_auth_headers: dict
):
    """Front desk should not be able to view analytics."""
    response = await client.get(
        "/api/v1/analytics/overview",
        headers=frontdesk_auth_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
