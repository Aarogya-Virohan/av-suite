from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, decode_token, get_password_hash
from app.enums.clinic import ClinicType
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def register_workspace(client: AsyncClient, name: str) -> tuple[uuid.UUID, dict[str, str]]:
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "clinic_name": name,
            "email": f"{uuid.uuid4()}@avtest.com",
            "password": "Password123!",
            "first_name": "Workspace",
            "last_name": "Admin",
        },
    )
    assert response.status_code == 201
    token = response.json()["data"]["access_token"]
    clinic_id = uuid.UUID(decode_token(token)["clinic_id"])
    return clinic_id, {"Authorization": f"Bearer {token}"}


async def create_staff(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    email: str,
    role: str = "therapist",
    password: str = "StaffPassword123!",
) -> dict:
    response = await client.post(
        f"{settings.API_V1_PREFIX}/users",
        headers=headers,
        json={
            "name": "Test Staff",
            "email": email,
            "password": password,
            "role": role,
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_post_users_membership_login_and_me_are_membership_based(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic_id, admin_headers = await register_workspace(client, "Staff Creation Workspace")
    email = f"therapist-{uuid.uuid4()}@avtest.com"
    created = await create_staff(client, admin_headers, email=email)

    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    memberships = (
        await db_session.scalars(select(Membership).where(Membership.user_id == user.id))
    ).all()
    assert len(memberships) == 1
    assert memberships[0].clinic_id == clinic_id
    assert memberships[0].role == UserRole.THERAPIST

    # Deliberately make both legacy values misleading before login.
    user.clinic_id = None
    user.role = UserRole.ADMIN
    await db_session.commit()

    login = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": email, "password": "StaffPassword123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    assert decode_token(token)["role"] == UserRole.THERAPIST.value
    staff_headers = {"Authorization": f"Bearer {token}"}

    auth_me = await client.get(f"{settings.API_V1_PREFIX}/auth/me", headers=staff_headers)
    assert auth_me.status_code == 200
    assert auth_me.json()["data"]["user"]["role"] == UserRole.THERAPIST.value

    me = await client.get(f"{settings.API_V1_PREFIX}/me", headers=staff_headers)
    assert me.status_code == 200
    me_data = me.json()["data"]
    assert me_data["active_workspace"]["id"] == str(clinic_id)
    assert me_data["active_workspace"]["role"] == UserRole.THERAPIST.value
    assert [workspace["id"] for workspace in me_data["workspaces"]] == [str(clinic_id)]
    assert created["id"] == str(user.id)


async def test_existing_email_joins_second_workspace_without_duplicate_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic_a_id, admin_a = await register_workspace(client, "Workspace A")
    clinic_b_id, admin_b = await register_workspace(client, "Workspace B")
    email = f"shared-staff-{uuid.uuid4()}@avtest.com"
    await create_staff(client, admin_a, email=email, role="therapist")
    user_before = await db_session.scalar(select(User).where(User.email == email))
    assert user_before is not None
    original_password_hash = user_before.password_hash

    await create_staff(
        client,
        admin_b,
        email=email,
        role="front_desk",
        password="IgnoredReplacementPassword123!",
    )
    await create_staff(client, admin_b, email=email, role="front_desk")

    assert await db_session.scalar(
        select(func.count()).select_from(User).where(User.email == email)
    ) == 1
    db_session.expire_all()
    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.password_hash == original_password_hash
    memberships = (
        await db_session.scalars(select(Membership).where(Membership.user_id == user.id))
    ).all()
    by_clinic = {membership.clinic_id: membership.role for membership in memberships}
    assert by_clinic == {
        clinic_a_id: UserRole.THERAPIST,
        clinic_b_id: UserRole.FRONT_DESK,
    }

    login_without_workspace = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": email, "password": "StaffPassword123!"},
    )
    assert login_without_workspace.status_code == 400

    login_b = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "email": email,
            "password": "StaffPassword123!",
            "clinic_id": str(clinic_b_id),
        },
    )
    assert login_b.status_code == 200
    staff_headers = {
        "Authorization": f"Bearer {login_b.json()['data']['access_token']}"
    }
    me = await client.get(f"{settings.API_V1_PREFIX}/me", headers=staff_headers)
    assert me.status_code == 200
    data = me.json()["data"]
    assert {workspace["id"] for workspace in data["workspaces"]} == {
        str(clinic_a_id),
        str(clinic_b_id),
    }
    assert data["active_workspace"]["id"] == str(clinic_b_id)

    staff_a = await client.get(f"{settings.API_V1_PREFIX}/users", headers=admin_a)
    staff_b = await client.get(f"{settings.API_V1_PREFIX}/users", headers=admin_b)
    assert any(item["id"] == str(user.id) for item in staff_a.json()["data"])
    assert any(item["id"] == str(user.id) for item in staff_b.json()["data"])
    admin_a_id = decode_token(admin_a["Authorization"].removeprefix("Bearer "))["sub"]
    admin_b_id = decode_token(admin_b["Authorization"].removeprefix("Bearer "))["sub"]
    assert all(item["id"] != admin_a_id for item in staff_b.json()["data"])
    assert all(item["id"] != admin_b_id for item in staff_a.json()["data"])


async def test_workspace_switch_uses_membership_and_rejects_nonmember(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic_a = Clinic(name="Switch A", type=ClinicType.CLINIC)
    clinic_b = Clinic(name="Switch B", type=ClinicType.SOLO)
    clinic_c = Clinic(name="Switch C", type=ClinicType.PERSONAL)
    user = User(
        email=f"switch-{uuid.uuid4()}@avtest.com",
        password_hash=get_password_hash("Password123!"),
        role=UserRole.ADMIN,
        first_name="Switch",
        last_name="User",
        is_active=True,
    )
    db_session.add_all([clinic_a, clinic_b, clinic_c, user])
    await db_session.flush()
    db_session.add_all(
        [
            Membership(user_id=user.id, clinic_id=clinic_a.id, role=UserRole.ADMIN),
            Membership(user_id=user.id, clinic_id=clinic_b.id, role=UserRole.THERAPIST),
        ]
    )
    await db_session.commit()

    token_a = create_access_token(
        subject=user.id, clinic_id=clinic_a.id, role=UserRole.ADMIN.value
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}
    initial_me = await client.get(f"{settings.API_V1_PREFIX}/me", headers=headers_a)
    assert initial_me.status_code == 200
    assert initial_me.json()["data"]["active_workspace"]["id"] == str(clinic_a.id)

    switched = await client.post(
        f"{settings.API_V1_PREFIX}/auth/switch-workspace",
        headers=headers_a,
        json={"clinic_id": str(clinic_b.id)},
    )
    assert switched.status_code == 200
    token_b = switched.json()["data"]["access_token"]
    assert token_b != token_a
    assert decode_token(token_b)["clinic_id"] == str(clinic_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}
    switched_me = await client.get(f"{settings.API_V1_PREFIX}/me", headers=headers_b)
    assert switched_me.status_code == 200
    assert switched_me.json()["data"]["active_workspace"]["id"] == str(clinic_b.id)
    assert switched_me.json()["data"]["active_workspace"]["role"] == "therapist"

    denied = await client.post(
        f"{settings.API_V1_PREFIX}/auth/switch-workspace",
        headers=headers_b,
        json={"clinic_id": str(clinic_c.id)},
    )
    assert denied.status_code == 403
    still_b = await client.get(f"{settings.API_V1_PREFIX}/me", headers=headers_b)
    assert still_b.status_code == 200
    assert still_b.json()["data"]["active_workspace"]["id"] == str(clinic_b.id)


async def test_staff_removal_removes_only_active_workspace_membership(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic_a_id, admin_a = await register_workspace(client, "Removal Workspace A")
    clinic_b_id, admin_b = await register_workspace(client, "Removal Workspace B")
    email = f"removable-{uuid.uuid4()}@avtest.com"
    await create_staff(client, admin_a, email=email)
    created = await create_staff(client, admin_b, email=email)
    user_id = uuid.UUID(created["id"])

    removed = await client.delete(
        f"{settings.API_V1_PREFIX}/users/{user_id}", headers=admin_a
    )
    assert removed.status_code == 200, removed.text
    assert await db_session.get(User, user_id) is not None
    memberships = (
        await db_session.scalars(select(Membership).where(Membership.user_id == user_id))
    ).all()
    assert [(membership.clinic_id, membership.role) for membership in memberships] == [
        (clinic_b_id, UserRole.THERAPIST)
    ]

    staff_a = await client.get(f"{settings.API_V1_PREFIX}/users", headers=admin_a)
    staff_b = await client.get(f"{settings.API_V1_PREFIX}/users", headers=admin_b)
    assert all(item["id"] != str(user_id) for item in staff_a.json()["data"])
    assert any(item["id"] == str(user_id) for item in staff_b.json()["data"])
    assert clinic_a_id != clinic_b_id


async def test_login_rejects_legacy_user_without_membership(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = Clinic(name="Legacy Fallback Disabled", type=ClinicType.CLINIC)
    user = User(
        email=f"no-membership-{uuid.uuid4()}@avtest.com",
        password_hash=get_password_hash("Password123!"),
        role=UserRole.ADMIN,
        first_name="Legacy",
        last_name="Fallback",
        is_active=True,
    )
    db_session.add_all([clinic, user])
    await db_session.flush()
    user.clinic_id = clinic.id
    await db_session.commit()

    login = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": user.email, "password": "Password123!"},
    )
    assert login.status_code == 401
    assert "membership" in login.json()["detail"].lower()

    legacy_token = create_access_token(
        subject=user.id, clinic_id=clinic.id, role=UserRole.ADMIN.value
    )
    protected = await client.get(
        f"{settings.API_V1_PREFIX}/me",
        headers={"Authorization": f"Bearer {legacy_token}"},
    )
    assert protected.status_code == 403
