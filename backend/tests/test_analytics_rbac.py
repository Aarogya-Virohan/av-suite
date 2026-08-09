from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _seed_analytics_context(db_session):
    clinic_a = Clinic(id=uuid4(), name="Clinic A")
    clinic_b = Clinic(id=uuid4(), name="Clinic B")

    admin_a = User(
        id=uuid4(),
        clinic_id=clinic_a.id,
        email=f"admin-{uuid4()}@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.ADMIN,
        first_name="Admin",
        last_name="A",
        is_active=True,
    )
    therapist_a = User(
        id=uuid4(),
        clinic_id=clinic_a.id,
        email=f"therapist-{uuid4()}@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.THERAPIST,
        first_name="Thera",
        last_name="Pist",
        is_active=True,
    )
    front_desk_a = User(
        id=uuid4(),
        clinic_id=clinic_a.id,
        email=f"frontdesk-{uuid4()}@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.FRONT_DESK,
        first_name="Front",
        last_name="Desk",
        is_active=True,
    )

    patient_a = Patient(
        id=uuid4(),
        clinic_id=clinic_a.id,
        first_name="Alice",
        last_name="One",
        phone="9876543210",
        status="active",
    )
    patient_b = Patient(
        id=uuid4(),
        clinic_id=clinic_b.id,
        first_name="Bob",
        last_name="Two",
        phone="9123456780",
        status="active",
    )

    db_session.add_all(
        [
            clinic_a,
            clinic_b,
            admin_a,
            therapist_a,
            front_desk_a,
            patient_a,
            patient_b,
        ]
    )
    await db_session.commit()

    return {
        "admin": {
            "Authorization": "Bearer "
            + create_access_token(admin_a.id, str(clinic_a.id), admin_a.role.value)
        },
        "therapist": {
            "Authorization": "Bearer "
            + create_access_token(therapist_a.id, str(clinic_a.id), therapist_a.role.value)
        },
        "front_desk": {
            "Authorization": "Bearer "
            + create_access_token(front_desk_a.id, str(clinic_a.id), front_desk_a.role.value)
        },
    }


async def test_analytics_overview_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(f"{settings.API_V1_PREFIX}/analytics/overview")

    assert response.status_code == 401


async def test_analytics_overview_forbids_front_desk_role(
    client: AsyncClient, db_session
) -> None:
    headers = await _seed_analytics_context(db_session)

    response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview",
        headers=headers["front_desk"],
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to perform this action."


@pytest.mark.parametrize("role_key", ["admin", "therapist"])
async def test_analytics_overview_allows_authorized_roles_and_preserves_clinic_isolation(
    client: AsyncClient, db_session, role_key: str
) -> None:
    headers = await _seed_analytics_context(db_session)

    response = await client.get(
        f"{settings.API_V1_PREFIX}/analytics/overview",
        headers=headers[role_key],
    )

    assert response.status_code == 200

    payload = response.json()["data"]
    assert payload["patients"]["total_patients"] == 1
    assert payload["patients"]["active_patients"] == 1
    assert payload["patients"]["new_patients_this_month"] == 1
