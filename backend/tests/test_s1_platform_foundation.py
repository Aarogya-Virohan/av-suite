from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.enums.clinic import ClinicType
from app.enums.organization import (
    ClinicStatus,
    OrganizationRole,
    OrganizationStatus,
    OrganizationType,
)
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.organization import Organization, OrganizationMembership
from app.models.product import WorkspaceProduct
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def register_workspace(client: AsyncClient, name: str = "S1 Workspace"):
    email = f"s1-{uuid.uuid4()}@example.com"
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "clinic_name": name,
            "email": email,
            "password": "Password123!",
            "first_name": "S1",
            "last_name": "Owner",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["data"]["access_token"]
    clinic_id = uuid.UUID(decode_token(token)["clinic_id"])
    return email, clinic_id, {"Authorization": f"Bearer {token}"}


def error_code(response) -> str | None:
    return response.json().get("meta", {}).get("error", {}).get("code")


@pytest.mark.parametrize("clinic_name", ["   ", "x" * 256])
async def test_registration_rejects_blank_or_overlong_clinic_names(
    client: AsyncClient, clinic_name: str
) -> None:
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "clinic_name": clinic_name,
            "email": f"s1-{uuid.uuid4()}@example.com",
            "password": "Password123!",
            "first_name": "S1",
            "last_name": "Owner",
        },
    )
    assert response.status_code == 422


async def test_async_listener_creates_organization_for_clinic_without_type(
    db_session: AsyncSession,
) -> None:
    clinic = Clinic(name="Listener Clinic")
    db_session.add(clinic)
    await db_session.flush()

    organization = await db_session.get(Organization, clinic.organization_id)
    assert organization is not None
    assert organization.name == clinic.name
    assert organization.slug == clinic.slug
    assert organization.type == OrganizationType.CLINIC


async def test_async_listener_maps_solo_and_keeps_explicit_organization(
    db_session: AsyncSession,
) -> None:
    solo = Clinic(name="Solo Listener Clinic", type=ClinicType.SOLO)
    explicit = Organization(
        name="Existing Organization",
        slug=f"org-{uuid.uuid4().hex}",
        type=OrganizationType.CHAIN,
    )
    db_session.add_all([solo, explicit])
    await db_session.flush()
    explicit_clinic = Clinic(
        name="Explicit Organization Clinic",
        organization_id=explicit.id,
    )
    db_session.add(explicit_clinic)
    await db_session.flush()

    solo_org = await db_session.get(Organization, solo.organization_id)
    explicit_org = await db_session.get(Organization, explicit_clinic.organization_id)
    assert solo_org is not None and solo_org.type == OrganizationType.INDIVIDUAL
    assert explicit_org is not None and explicit_org.id == explicit.id


async def test_registration_creates_organization_and_owner_membership(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email, clinic_id, _ = await register_workspace(client, "Registration S1 Clinic")
    user = await db_session.scalar(select(User).where(User.email == email))
    clinic = await db_session.get(Clinic, clinic_id)
    assert user is not None and clinic is not None
    assert clinic.organization_id is not None
    assert await db_session.scalar(
        select(func.count()).select_from(Membership).where(
            Membership.user_id == user.id, Membership.clinic_id == clinic_id
        )
    ) == 1
    owner = await db_session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == clinic.organization_id,
        )
    )
    assert owner is not None and owner.role == OrganizationRole.ORG_OWNER


async def test_suspended_clinic_blocks_me_crm_and_exercise_routes(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, clinic_id, headers = await register_workspace(client, "Suspended Clinic")
    clinic = await db_session.get(Clinic, clinic_id)
    assert clinic is not None
    clinic.status = ClinicStatus.SUSPENDED
    await db_session.flush()

    for path in ("/auth/me", "/patients", "/exercises"):
        response = await client.get(f"{settings.API_V1_PREFIX}{path}", headers=headers)
        assert response.status_code == 403, (path, response.text)
        assert error_code(response) == "WORKSPACE_SUSPENDED"
        assert response.json()["meta"]["error"]["details"]["level"] == "clinic"


async def test_suspended_organization_blocks_clinic_workspace(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email, clinic_id, first_headers = await register_workspace(
        client, "Suspended Organization Clinic"
    )
    clinic = await db_session.get(Clinic, clinic_id)
    assert clinic is not None
    organization = await db_session.get(Organization, clinic.organization_id)
    assert organization is not None
    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None

    second_clinic = Clinic(
        name="Second Organization Branch", organization_id=organization.id
    )
    db_session.add(second_clinic)
    await db_session.flush()
    db_session.add(
        Membership(user_id=user.id, clinic_id=second_clinic.id, role=UserRole.ADMIN)
    )
    await db_session.commit()
    second_login = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "email": email,
            "password": "Password123!",
            "clinic_id": str(second_clinic.id),
        },
    )
    assert second_login.status_code == 200
    second_headers = {
        "Authorization": f"Bearer {second_login.json()['data']['access_token']}"
    }

    organization.status = OrganizationStatus.SUSPENDED
    await db_session.flush()

    for headers in (first_headers, second_headers):
        response = await client.get(f"{settings.API_V1_PREFIX}/auth/me", headers=headers)
        assert response.status_code == 403
        assert error_code(response) == "WORKSPACE_SUSPENDED"
        assert response.json()["meta"]["error"]["details"]["level"] == "organization"


async def test_login_to_suspended_clinic_is_403_not_500(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email, clinic_id, _ = await register_workspace(client, "Suspended Login Clinic")
    clinic = await db_session.get(Clinic, clinic_id)
    assert clinic is not None
    clinic.status = ClinicStatus.SUSPENDED
    await db_session.flush()

    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": email, "password": "Password123!", "clinic_id": str(clinic_id)},
    )
    assert response.status_code == 403
    assert error_code(response) == "WORKSPACE_SUSPENDED"


async def test_suspended_public_booking_matches_unknown_slug_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, clinic_id, _ = await register_workspace(client, "Suspended Booking Clinic")
    clinic = await db_session.get(Clinic, clinic_id)
    assert clinic is not None
    slug = clinic.slug
    clinic.status = ClinicStatus.SUSPENDED
    await db_session.flush()

    branding_suspended = await client.get(
        f"{settings.API_V1_PREFIX}/booking/branding/{slug}"
    )
    branding_unknown = await client.get(
        f"{settings.API_V1_PREFIX}/booking/branding/missing-{uuid.uuid4().hex}"
    )
    assert branding_suspended.status_code == branding_unknown.status_code == 404
    assert branding_suspended.json()["detail"] == f"Clinic '{slug}' not found."
    assert branding_unknown.json()["detail"].startswith("Clinic 'missing-")

    payload = {"name": "Booking Patient", "phone": "5550101"}
    request_suspended = await client.post(
        f"{settings.API_V1_PREFIX}/booking/request?clinic_slug={slug}", json=payload
    )
    unknown_slug = f"missing-{uuid.uuid4().hex}"
    request_unknown = await client.post(
        f"{settings.API_V1_PREFIX}/booking/request?clinic_slug={unknown_slug}",
        json=payload,
    )
    assert request_suspended.status_code == request_unknown.status_code == 404
    assert request_suspended.json()["detail"] == (
        f"Clinic with slug '{slug}' not found."
    )
    assert request_unknown.json()["detail"] == (
        f"Clinic with slug '{unknown_slug}' not found."
    )


async def test_multi_clinic_login_can_select_active_clinic_when_other_is_suspended(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email, suspended_id, _ = await register_workspace(client, "One Suspended Clinic")
    user = await db_session.scalar(select(User).where(User.email == email))
    suspended = await db_session.get(Clinic, suspended_id)
    assert user is not None and suspended is not None
    active = Clinic(name="Second Active Clinic")
    db_session.add(active)
    await db_session.flush()
    db_session.add(
        Membership(user_id=user.id, clinic_id=active.id, role=UserRole.ADMIN)
    )
    suspended.status = ClinicStatus.SUSPENDED
    await db_session.commit()

    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": email, "password": "Password123!", "clinic_id": str(active.id)},
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    assert decode_token(token)["clinic_id"] == str(active.id)
    me = await client.get(
        f"{settings.API_V1_PREFIX}/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200, me.text
    assert str(me.json()["data"]["active_workspace"]["id"]) == str(active.id)


async def _registered_crm_entitlement(client, db_session):
    _, clinic_id, headers = await register_workspace(client, f"Entitlement {uuid.uuid4().hex}")
    entitlement = await db_session.scalar(
        select(WorkspaceProduct).where(
            WorkspaceProduct.clinic_id == clinic_id,
            WorkspaceProduct.product_id == "crm",
        )
    )
    assert entitlement is not None
    return clinic_id, headers, entitlement


async def test_expired_entitlement_blocks_capability_and_me_listing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, headers, entitlement = await _registered_crm_entitlement(client, db_session)
    entitlement.status = EntitlementStatus.ENABLED
    entitlement.valid_until = datetime.now(timezone.utc) - timedelta(seconds=2)
    await db_session.flush()

    protected = await client.get(f"{settings.API_V1_PREFIX}/leads", headers=headers)
    me = await client.get(f"{settings.API_V1_PREFIX}/me", headers=headers)
    assert protected.status_code == 403 and error_code(protected) == "PRODUCT_NOT_ENTITLED"
    assert all(product["key"] != "crm" for product in me.json()["data"]["active_products"])
    assert "leads.view" not in me.json()["data"]["capabilities"]


async def test_future_entitlement_blocks_capability_and_me_listing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, headers, entitlement = await _registered_crm_entitlement(client, db_session)
    entitlement.status = EntitlementStatus.ENABLED
    entitlement.valid_from = datetime.now(timezone.utc) + timedelta(days=1)
    entitlement.valid_until = None
    await db_session.flush()

    protected = await client.get(f"{settings.API_V1_PREFIX}/leads", headers=headers)
    me = await client.get(f"{settings.API_V1_PREFIX}/me", headers=headers)
    assert protected.status_code == 403 and error_code(protected) == "PRODUCT_NOT_ENTITLED"
    assert all(product["key"] != "crm" for product in me.json()["data"]["active_products"])
    assert "leads.view" not in me.json()["data"]["capabilities"]


@pytest.mark.parametrize(
    "valid_from,valid_until",
    [
        (None, None),
        (
            datetime.now(timezone.utc) - timedelta(days=1),
            datetime.now(timezone.utc) + timedelta(days=1),
        ),
    ],
)
async def test_null_or_current_entitlement_window_allows_capability(
    client: AsyncClient,
    db_session: AsyncSession,
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> None:
    _, headers, entitlement = await _registered_crm_entitlement(client, db_session)
    entitlement.status = EntitlementStatus.ENABLED
    entitlement.valid_from = valid_from
    entitlement.valid_until = valid_until
    await db_session.flush()

    response = await client.get(f"{settings.API_V1_PREFIX}/leads", headers=headers)
    assert response.status_code == 200, response.text


async def test_marketplace_enabled_flag_respects_entitlement_expiry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, headers, entitlement = await _registered_crm_entitlement(client, db_session)
    entitlement.status = EntitlementStatus.ENABLED
    entitlement.valid_until = datetime.now(timezone.utc) - timedelta(seconds=2)
    await db_session.flush()

    response = await client.get(
        f"{settings.API_V1_PREFIX}/marketplace/products", headers=headers
    )
    assert response.status_code == 200, response.text
    crm = next(item for item in response.json()["data"] if item["product_key"] == "crm")
    assert crm["installed"] is True
    assert crm["enabled"] is False
