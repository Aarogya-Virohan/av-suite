from __future__ import annotations

import uuid

import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_capability
from app.core.security import create_access_token
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.main import app
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.services.product_entitlements import ensure_crm_entitlement


pytestmark = pytest.mark.asyncio


router = APIRouter()


@router.get("/test-product-entitled-crm")
async def product_entitled_crm(
    scope: CapabilityScope = Depends(require_capability("leads.view")),
):
    return {"scope": scope}


@router.get("/test-platform-core")
async def platform_core(
    scope: CapabilityScope = Depends(require_capability("patients.view")),
):
    return {"scope": scope}


@router.get("/test-product-unmapped")
async def product_unmapped(
    scope: CapabilityScope = Depends(require_capability("analytics.clinic_financials")),
):
    return {"scope": scope}


@router.get("/test-product-exercises")
async def product_exercises(
    scope: CapabilityScope = Depends(require_capability("exercises.view")),
):
    return {"scope": scope}


@router.get("/test-product-posture")
async def product_posture(
    scope: CapabilityScope = Depends(require_capability("posture.view")),
):
    return {"scope": scope}


@router.get("/test-product-prescriptions")
async def product_prescriptions(
    scope: CapabilityScope = Depends(require_capability("prescriptions.view")),
):
    return {"scope": scope}


app.include_router(router)


async def create_workspace_user(
    db_session: AsyncSession,
    *,
    email: str,
    role: UserRole = UserRole.ADMIN,
    grant_crm: bool = False,
    disable_crm: bool = False,
    existing_user: User | None = None,
) -> tuple[Clinic, User, dict[str, str]]:
    clinic = Clinic(name=f"Entitlement Clinic {uuid.uuid4()}")
    user = existing_user or User(
        id=uuid.uuid4(),
        clinic_id=None,
        email=email,
        password_hash="hash",
        role=role,
        first_name="Entitled",
        last_name="User",
        is_active=True,
    )
    db_session.add(clinic)
    if existing_user is None:
        db_session.add(user)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, clinic_id=clinic.id, role=role))

    if grant_crm:
        await ensure_crm_entitlement(db_session, clinic.id)
    if disable_crm:
        await ensure_crm_entitlement(db_session, clinic.id)
        current = await db_session.scalar(
            select(WorkspaceProduct).where(
                WorkspaceProduct.clinic_id == clinic.id,
                WorkspaceProduct.product_id == "crm",
            )
        )
        assert current is not None
        current.status = EntitlementStatus.DISABLED

    await db_session.commit()

    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=role.value)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return clinic, user, headers


def product_error_code(response) -> str:
    return response.json()["meta"]["error"]["code"]


async def test_product_entitlement_allows_mapped_capability(
    client: AsyncClient,
    db_session: AsyncSession,
):
    _, _, headers = await create_workspace_user(
        db_session,
        email=f"entitled-{uuid.uuid4()}@avtest.com",
        grant_crm=True,
    )

    response = await client.get("/test-product-entitled-crm", headers=headers)

    assert response.status_code == 200
    assert response.json()["scope"] == "all"


async def test_missing_entitlement_denies_before_rbac(
    client: AsyncClient,
    db_session: AsyncSession,
):
    _, _, headers = await create_workspace_user(
        db_session,
        email=f"not-entitled-{uuid.uuid4()}@avtest.com",
        role=UserRole.FRONT_DESK,
        grant_crm=False,
    )

    response = await client.get("/test-product-entitled-crm", headers=headers)

    assert response.status_code == 403
    assert product_error_code(response) == "PRODUCT_NOT_ENTITLED"


async def test_disabled_entitlement_denies_mapped_capability(
    client: AsyncClient,
    db_session: AsyncSession,
):
    clinic, _, headers = await create_workspace_user(
        db_session,
        email=f"disabled-{uuid.uuid4()}@avtest.com",
        grant_crm=True,
    )

    entitlement = await db_session.scalar(
        select(WorkspaceProduct).where(
            WorkspaceProduct.clinic_id == clinic.id,
            WorkspaceProduct.product_id == "crm",
        )
    )
    assert entitlement is not None
    entitlement.status = EntitlementStatus.DISABLED
    await db_session.commit()

    response = await client.get("/test-product-entitled-crm", headers=headers)

    assert response.status_code == 403
    assert product_error_code(response) == "PRODUCT_NOT_ENTITLED"


async def test_entitlement_is_workspace_isolated(
    client: AsyncClient,
    db_session: AsyncSession,
):
    _, _, entitled_headers = await create_workspace_user(
        db_session,
        email=f"isolated-a-{uuid.uuid4()}@avtest.com",
        grant_crm=True,
    )
    _, _, unentitled_headers = await create_workspace_user(
        db_session,
        email=f"isolated-b-{uuid.uuid4()}@avtest.com",
        grant_crm=False,
    )

    entitled_response = await client.get(
        "/test-product-entitled-crm", headers=entitled_headers
    )
    unentitled_response = await client.get(
        "/test-product-entitled-crm", headers=unentitled_headers
    )

    assert entitled_response.status_code == 200
    assert unentitled_response.status_code == 403
    assert product_error_code(unentitled_response) == "PRODUCT_NOT_ENTITLED"


async def test_same_user_entitlements_follow_active_workspace(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email=f"multi-{uuid.uuid4()}@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Multi",
        last_name="Workspace",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    _, _, entitled_headers = await create_workspace_user(
        db_session,
        email=user.email,
        grant_crm=True,
        existing_user=user,
    )
    _, _, unentitled_headers = await create_workspace_user(
        db_session,
        email=user.email,
        grant_crm=False,
        existing_user=user,
    )

    assert (
        await client.get("/test-product-entitled-crm", headers=entitled_headers)
    ).status_code == 200
    unentitled_response = await client.get(
        "/test-product-entitled-crm", headers=unentitled_headers
    )
    assert unentitled_response.status_code == 403
    assert product_error_code(unentitled_response) == "PRODUCT_NOT_ENTITLED"


async def test_unmapped_capability_keeps_existing_rbac_behavior(
    client: AsyncClient,
    db_session: AsyncSession,
):
    _, _, headers = await create_workspace_user(
        db_session,
        email=f"unmapped-{uuid.uuid4()}@avtest.com",
        grant_crm=False,
    )

    response = await client.get("/test-product-unmapped", headers=headers)

    assert response.status_code == 200
    assert response.json()["scope"] == "all"


async def test_platform_core_capability_does_not_require_crm(
    client: AsyncClient,
    db_session: AsyncSession,
):
    _, _, headers = await create_workspace_user(
        db_session,
        email=f"platform-core-{uuid.uuid4()}@avtest.com",
    )

    response = await client.get("/test-platform-core", headers=headers)

    assert response.status_code == 200
    assert response.json()["scope"] == "all"


@pytest.mark.parametrize(
    ("product_id", "path"),
    [
        ("exercise-library", "/test-product-exercises"),
        ("posture-tool", "/test-product-posture"),
        ("exercise-prescription", "/test-product-prescriptions"),
    ],
)
async def test_tool_capability_requires_its_product_entitlement(
    client: AsyncClient,
    db_session: AsyncSession,
    product_id: str,
    path: str,
):
    clinic, _, headers = await create_workspace_user(
        db_session,
        email=f"tool-entitlement-{uuid.uuid4()}@avtest.com",
    )

    denied = await client.get(path, headers=headers)
    assert denied.status_code == 403
    assert product_error_code(denied) == "PRODUCT_NOT_ENTITLED"

    db_session.add(
        WorkspaceProduct(
            clinic_id=clinic.id,
            product_id=product_id,
            status=EntitlementStatus.ENABLED,
        )
    )
    await db_session.commit()

    allowed = await client.get(path, headers=headers)
    assert allowed.status_code == 200
    assert allowed.json()["scope"] == "all"
