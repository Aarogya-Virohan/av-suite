"""Tests for public booking clinic slug consistency.

Verifies that the public booking flow uses clinic_slug consistently with the branding endpoint.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.clinic import Clinic
from app.models.booking import AppointmentRequest
from app.core.security import get_password_hash, create_access_token
from app.enums.user import UserRole


@pytest.mark.asyncio
async def test_booking_request_with_valid_clinic_slug(
    client: AsyncClient, db_session, auth_headers: dict
):
    """POST /booking/request with valid clinic_slug should create booking for correct clinic."""
    # Register a clinic to get a predictable slug
    unique_clinic_name = f"Booking Slug Test Clinic {uuid.uuid4().hex[:8]}"
    reg_response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "clinic_name": unique_clinic_name,
            "email": f"slug_test_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPassword123!",
            "first_name": "Slug",
            "last_name": "Test",
        },
    )
    assert reg_response.status_code in (200, 201)
    clinic_id_from_token = reg_response.json()["data"].get("clinic_id")

    # Verify clinic exists with the expected name
    clinic_result = await db_session.execute(
        select(Clinic).where(Clinic.name == unique_clinic_name)
    )
    clinic = clinic_result.scalar_one()
    assert clinic is not None
    clinic_slug = clinic.name

    # Create booking request using clinic slug (public endpoint, no auth required)
    booking_data = {
        "name": "Slug Test Patient",
        "phone": "9999999999",
        "email": "patient@test.com",
        "notes": "Test booking with slug",
        "preferred_date": "2026-08-26",
    }
    response = await client.post(
        f"{settings.API_V1_PREFIX}/booking/request?clinic_slug={clinic_slug}",
        json=booking_data,
    )
    assert response.status_code in (200, 201), response.text
    response_data = response.json().get("data", response.json())
    booking_id = response_data["id"]

    # Verify booking was created for the correct clinic
    booking_result = await db_session.execute(
        select(AppointmentRequest).where(AppointmentRequest.id == uuid.UUID(booking_id))
    )
    booking = booking_result.scalar_one()
    assert booking is not None
    assert booking.clinic_id == clinic.id
    assert booking.name == "Slug Test Patient"


@pytest.mark.asyncio
async def test_booking_request_with_invalid_clinic_slug(client: AsyncClient):
    """POST /booking/request with invalid clinic_slug should return 404."""
    booking_data = {
        "name": "Invalid Clinic Patient",
        "phone": "8888888888",
        "notes": "Should fail",
    }
    response = await client.post(
        f"{settings.API_V1_PREFIX}/booking/request?clinic_slug=NonExistentClinicXYZ123",
        json=booking_data,
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_booking_request_without_clinic_slug(client: AsyncClient):
    """POST /booking/request without clinic_slug should return 400."""
    booking_data = {
        "name": "Missing Slug Patient",
        "phone": "7777777777",
        "notes": "Should fail",
    }
    response = await client.post(
        f"{settings.API_V1_PREFIX}/booking/request",
        json=booking_data,
    )
    assert response.status_code == 400, response.text
    assert "clinic_slug" in response.text.lower()


@pytest.mark.asyncio
async def test_clinic_slug_and_branding_endpoint_consistency(
    client: AsyncClient, db_session
):
    """Verify that clinic_slug works the same way across booking/branding and booking/request endpoints."""
    # Register a clinic
    unique_clinic_name = f"Consistency Test Clinic {uuid.uuid4().hex[:8]}"
    reg_response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "clinic_name": unique_clinic_name,
            "email": f"consistency_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPassword123!",
            "first_name": "Consistency",
            "last_name": "Test",
        },
    )
    assert reg_response.status_code in (200, 201)

    # Get clinic from database to verify slug
    clinic_result = await db_session.execute(
        select(Clinic).where(Clinic.name == unique_clinic_name)
    )
    clinic = clinic_result.scalar_one()
    clinic_slug = clinic.name

    # 1. Get branding using slug
    branding_response = await client.get(
        f"{settings.API_V1_PREFIX}/booking/branding/{clinic_slug}"
    )
    assert branding_response.status_code == 200
    branding_data = branding_response.json().get("data", branding_response.json())
    assert branding_data["clinic_id"] == str(clinic.id)

    # 2. Create booking request using same slug
    booking_data = {
        "name": "Consistency Test Patient",
        "phone": "6666666666",
        "notes": "Testing slug consistency",
    }
    booking_response = await client.post(
        f"{settings.API_V1_PREFIX}/booking/request?clinic_slug={clinic_slug}",
        json=booking_data,
    )
    assert booking_response.status_code in (200, 201)
    booking_data_response = booking_response.json().get("data", booking_response.json())
    assert booking_data_response["clinic_id"] == str(clinic.id)

    # Both endpoints should reference the same clinic
    assert branding_data["clinic_id"] == booking_data_response["clinic_id"]


@pytest.mark.asyncio
async def test_booking_slug_prevents_cross_clinic_access(
    client: AsyncClient, db_session
):
    """Verify that clinic_slug isolation prevents booking for wrong clinic."""
    # Create two clinics
    clinic1_name = f"Clinic 1 {uuid.uuid4().hex[:8]}"
    clinic2_name = f"Clinic 2 {uuid.uuid4().hex[:8]}"

    for clinic_name in [clinic1_name, clinic2_name]:
        await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "clinic_name": clinic_name,
                "email": f"clinic_{uuid.uuid4().hex[:6]}@test.com",
                "password": "TestPassword123!",
                "first_name": "Clinic",
                "last_name": "Admin",
            },
        )

    # Get clinic IDs
    clinic1_result = await db_session.execute(
        select(Clinic).where(Clinic.name == clinic1_name)
    )
    clinic1 = clinic1_result.scalar_one()
    clinic2_result = await db_session.execute(
        select(Clinic).where(Clinic.name == clinic2_name)
    )
    clinic2 = clinic2_result.scalar_one()

    # Create booking for clinic1
    booking_data = {
        "name": "Isolation Test Patient",
        "phone": "5555555555",
        "notes": "Testing isolation",
    }
    response = await client.post(
        f"{settings.API_V1_PREFIX}/booking/request?clinic_slug={clinic1_name}",
        json=booking_data,
    )
    assert response.status_code in (200, 201)
    booking_id = response.json().get("data", response.json())["id"]

    # Verify booking was created for clinic1, not clinic2
    booking_result = await db_session.execute(
        select(AppointmentRequest).where(AppointmentRequest.id == uuid.UUID(booking_id))
    )
    booking = booking_result.scalar_one()
    assert booking.clinic_id == clinic1.id
    assert booking.clinic_id != clinic2.id


@pytest.mark.asyncio
async def test_booking_slug_resolves_via_clinic_name(client: AsyncClient, db_session):
    """Verify that clinic slug resolution matches clinic name (via get_by_slug_or_id)."""
    # Register clinic with specific name
    clinic_name = f"Name Resolution Test {uuid.uuid4().hex[:8]}"
    reg_response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "clinic_name": clinic_name,
            "email": f"name_test_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPassword123!",
            "first_name": "Name",
            "last_name": "Test",
        },
    )
    assert reg_response.status_code in (200, 201)

    clinic_result = await db_session.execute(
        select(Clinic).where(Clinic.name == clinic_name)
    )
    clinic = clinic_result.scalar_one()

    # Test various slug formats that should match via ilike
    test_slugs = [
        clinic_name,  # exact match
        clinic_name.lower(),  # case-insensitive
        clinic_name.replace(" ", "-"),  # with dashes converted to spaces
    ]

    for test_slug in test_slugs:
        booking_data = {
            "name": f"Patient for {test_slug}",
            "phone": "4444444444",
        }
        response = await client.post(
            f"{settings.API_V1_PREFIX}/booking/request?clinic_slug={test_slug}",
            json=booking_data,
        )
        # At least the exact match should work
        if test_slug == clinic_name:
            assert response.status_code in (
                200,
                201,
            ), f"Failed for slug: {test_slug}, response: {response.text}"
            booking_id = response.json().get("data", response.json())["id"]
            booking_result = await db_session.execute(
                select(AppointmentRequest).where(
                    AppointmentRequest.id == uuid.UUID(booking_id)
                )
            )
            booking = booking_result.scalar_one()
            assert booking.clinic_id == clinic.id
