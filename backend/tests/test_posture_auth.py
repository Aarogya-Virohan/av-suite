"""Posture endpoints sit behind login, the posture-tool product and posture.create.

A request that passes every gate reaches the endpoint and fails on the empty
body (422), which is how these tests tell "allowed" apart from 401 / 403
without running MediaPipe.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission

pytestmark = pytest.mark.asyncio

ENDPOINTS = [
    "/api/v1/posture/detect",
    "/api/v1/posture/report",
    "/api/v1/posture/report/pdf",
]


async def make_user(
    db_session: AsyncSession,
    *,
    role: UserRole,
    posture_product: EntitlementStatus | None = EntitlementStatus.ENABLED,
    posture_create: CapabilityScope | None = None,
) -> dict[str, str]:
    clinic = Clinic(name=f"Posture Auth Clinic {uuid.uuid4()}")
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email=f"posture-{uuid.uuid4()}@avtest.com",
        password_hash="hash",
        role=role,
        first_name="Posture",
        last_name="User",
        is_active=True,
    )
    db_session.add_all([clinic, user])
    await db_session.flush()
    db_session.add(Membership(user_id=user.id, clinic_id=clinic.id, role=role))
    if posture_product is not None:
        db_session.add(
            WorkspaceProduct(
                clinic_id=clinic.id, product_id="posture-tool", status=posture_product
            )
        )
    if posture_create is not None:
        db_session.add(
            UserPermission(
                user_id=user.id,
                clinic_id=clinic.id,
                capability_key="posture.create",
                scope=posture_create,
            )
        )
    await db_session.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("path", ENDPOINTS)
async def test_no_token_is_401(client: AsyncClient, path: str):
    response = await client.post(path)
    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/posture/detect", "/posture/report", "/posture/report/pdf"])
async def test_old_unauthenticated_path_is_gone(client: AsyncClient, path: str):
    response = await client.post(path)
    assert response.status_code == 404


@pytest.mark.parametrize("path", ENDPOINTS)
async def test_admin_with_product_reaches_endpoint(
    client: AsyncClient, db_session: AsyncSession, path: str
):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    response = await client.post(path, headers=headers)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "status", [None, EntitlementStatus.DISABLED], ids=["missing", "disabled"]
)
async def test_admin_without_posture_product_is_403(
    client: AsyncClient, db_session: AsyncSession, status
):
    headers = await make_user(db_session, role=UserRole.ADMIN, posture_product=status)
    response = await client.post(ENDPOINTS[0], headers=headers)
    assert response.status_code == 403
    assert response.json()["meta"]["error"]["code"] == "PRODUCT_NOT_ENTITLED"


@pytest.mark.parametrize("role", [UserRole.THERAPIST, UserRole.FRONT_DESK])
async def test_non_admin_without_grant_is_403(
    client: AsyncClient, db_session: AsyncSession, role: UserRole
):
    headers = await make_user(db_session, role=role)
    response = await client.post(ENDPOINTS[0], headers=headers)
    assert response.status_code == 403
    assert "posture.create" in response.text


async def test_therapist_with_explicit_none_is_403(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await make_user(
        db_session, role=UserRole.THERAPIST, posture_create=CapabilityScope.NONE
    )
    response = await client.post(ENDPOINTS[0], headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize("path", ENDPOINTS)
async def test_therapist_with_grant_reaches_endpoint(
    client: AsyncClient, db_session: AsyncSession, path: str
):
    headers = await make_user(
        db_session, role=UserRole.THERAPIST, posture_create=CapabilityScope.ALL
    )
    response = await client.post(path, headers=headers)
    assert response.status_code == 422
