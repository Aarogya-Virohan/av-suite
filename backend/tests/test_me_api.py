from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.enums.clinic import ClinicType
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementSource, EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission

pytestmark = pytest.mark.asyncio


async def create_platform_user(
    db_session: AsyncSession,
    *,
    memberships: list[tuple[str, ClinicType, UserRole]],
    active_index: int = 0,
    legacy_clinic_index: int | None = None,
    active_products: list[tuple[str, EntitlementStatus]] | None = None,
) -> tuple[User, list[Clinic], dict[str, str]]:
    clinics = [
        Clinic(name=name, type=workspace_type)
        for name, workspace_type, _ in memberships
    ]
    db_session.add_all(clinics)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        clinic_id=(
            clinics[legacy_clinic_index].id if legacy_clinic_index is not None else None
        ),
        email=f"platform-context-{uuid.uuid4()}@avtest.com",
        password_hash="not-returned",
        role=UserRole.ADMIN,
        first_name="Platform",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    db_session.add_all(
        [
            Membership(user_id=user.id, clinic_id=clinic.id, role=role)
            for clinic, (_, _, role) in zip(clinics, memberships, strict=True)
        ]
    )
    if active_products:
        db_session.add_all(
            [
                WorkspaceProduct(
                    clinic_id=clinics[active_index].id,
                    product_id=product_id,
                    status=product_status,
                    source=EntitlementSource.DIRECT,
                )
                for product_id, product_status in active_products
            ]
        )
    await db_session.commit()

    active_role = memberships[active_index][2]
    token = create_access_token(
        subject=user.id,
        clinic_id=clinics[active_index].id,
        role=active_role.value,
    )
    return user, clinics, {"Authorization": f"Bearer {token}"}


async def test_me_returns_user_workspace_products_and_authorized_capabilities(
    client: AsyncClient, db_session: AsyncSession
):
    user, clinics, headers = await create_platform_user(
        db_session,
        memberships=[("Single Workspace", ClinicType.CLINIC, UserRole.ADMIN)],
        active_products=[("crm", EntitlementStatus.ENABLED)],
    )

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user"] == {
        "id": str(user.id),
        "email": user.email,
        "name": "Platform User",
        "role": "admin",
    }
    assert data["user"].get("password_hash") is None
    assert data["workspaces"] == [
        {
            "id": str(clinics[0].id),
            "name": "Single Workspace",
            "type": "clinic",
            "role": "admin",
        }
    ]
    assert data["active_workspace"] == data["workspaces"][0]
    assert [product["key"] for product in data["active_products"]] == ["crm"]
    assert data["active_products"][0]["status"] == "enabled"
    assert data["active_products"][0]["valid_from"] is None
    assert data["active_products"][0]["valid_until"] is None
    assert "patients.view" in data["capabilities"]
    assert "unknown.capability" not in data["capabilities"]
    assert "exercises.view" not in data["capabilities"]
    assert "posture.view" not in data["capabilities"]
    assert "prescriptions.view" not in data["capabilities"]
    assert "users.view" in data["capabilities"]
    assert "permissions.view" in data["capabilities"]
    assert "audit.view" in data["capabilities"]
    assert "settings.view" in data["capabilities"]


async def test_me_exposes_core_capabilities_without_crm(
    client: AsyncClient, db_session: AsyncSession
):
    _, _, headers = await create_platform_user(
        db_session,
        memberships=[("Core-only Workspace", ClinicType.CLINIC, UserRole.ADMIN)],
    )

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["active_products"] == []
    assert {
        "patients.view",
        "users.view",
        "permissions.view",
        "audit.view",
        "settings.view",
    }.issubset(data["capabilities"])
    assert "leads.view" not in data["capabilities"]
    assert "exercises.view" not in data["capabilities"]
    assert "posture.view" not in data["capabilities"]
    assert "prescriptions.view" not in data["capabilities"]


async def test_me_filters_capabilities_by_multiple_enabled_products(
    client: AsyncClient, db_session: AsyncSession
):
    _, _, headers = await create_platform_user(
        db_session,
        memberships=[("Multi-product Workspace", ClinicType.CLINIC, UserRole.ADMIN)],
        active_products=[
            ("crm", EntitlementStatus.ENABLED),
            ("exercise-library", EntitlementStatus.ENABLED),
            ("posture-tool", EntitlementStatus.ENABLED),
        ],
    )

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    capabilities = set(data["capabilities"])
    assert "patients.view" in capabilities
    assert "leads.view" in capabilities
    assert "exercises.view" in capabilities
    assert "posture.view" in capabilities
    assert "prescriptions.view" not in capabilities
    assert {"crm", "exercise-library", "posture-tool"} == {
        product["key"] for product in data["active_products"]
    }


async def test_me_lists_exercise_prescription_capabilities_when_entitled(
    client: AsyncClient, db_session: AsyncSession
):
    _, _, headers = await create_platform_user(
        db_session,
        memberships=[("Prescription Workspace", ClinicType.CLINIC, UserRole.ADMIN)],
        active_products=[
            ("exercise-prescription", EntitlementStatus.ENABLED),
        ],
    )

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    capabilities = set(response.json()["data"]["capabilities"])
    assert "prescriptions.view" in capabilities
    assert "exercises.view" not in capabilities
    assert "patients.view" in capabilities


async def test_me_uses_membership_roles_for_each_workspace_and_active_context(
    client: AsyncClient, db_session: AsyncSession
):
    _, clinics, headers = await create_platform_user(
        db_session,
        memberships=[
            ("Admin Workspace", ClinicType.CLINIC, UserRole.ADMIN),
            ("Therapist Workspace", ClinicType.SOLO, UserRole.THERAPIST),
        ],
        active_index=1,
        legacy_clinic_index=0,
    )

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert {
        workspace["name"]: workspace["role"] for workspace in data["workspaces"]
    } == {
        "Admin Workspace": "admin",
        "Therapist Workspace": "therapist",
    }
    assert data["active_workspace"]["id"] == str(clinics[1].id)
    assert data["active_workspace"]["role"] == "therapist"
    assert data["user"]["role"] == "therapist"
    assert data["capabilities"] == []


async def test_me_omits_disabled_products_and_their_mapped_capabilities(
    client: AsyncClient, db_session: AsyncSession
):
    _, _, headers = await create_platform_user(
        db_session,
        memberships=[("Disabled CRM Workspace", ClinicType.CLINIC, UserRole.ADMIN)],
        active_products=[("crm", EntitlementStatus.DISABLED)],
    )

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["active_products"] == []
    assert "patients.view" in data["capabilities"]
    assert "leads.view" not in data["capabilities"]


async def test_me_applies_user_specific_capability_overrides(
    client: AsyncClient, db_session: AsyncSession
):
    user, clinics, headers = await create_platform_user(
        db_session,
        memberships=[("Override Workspace", ClinicType.CLINIC, UserRole.ADMIN)],
        active_products=[("crm", EntitlementStatus.ENABLED)],
    )
    db_session.add(
        UserPermission(
            user_id=user.id,
            clinic_id=clinics[0].id,
            capability_key="patients.view",
            scope=CapabilityScope.NONE,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    assert "patients.view" not in response.json()["data"]["capabilities"]


async def test_me_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/me")

    assert response.status_code == 401


async def test_me_isolates_active_workspace_products_and_capabilities(
    client: AsyncClient, db_session: AsyncSession
):
    _, clinics, headers = await create_platform_user(
        db_session,
        memberships=[
            ("Entitled Workspace", ClinicType.CLINIC, UserRole.ADMIN),
            ("Unentitled Workspace", ClinicType.PERSONAL, UserRole.ADMIN),
        ],
        active_index=1,
    )
    db_session.add(
        WorkspaceProduct(
            clinic_id=clinics[0].id,
            product_id="crm",
            status=EntitlementStatus.ENABLED,
            source=EntitlementSource.DIRECT,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["active_workspace"]["id"] == str(clinics[1].id)
    assert data["active_products"] == []
    assert "patients.view" in data["capabilities"]
    assert "leads.view" not in data["capabilities"]
