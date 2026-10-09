from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.enums.clinic import ClinicType
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.audit import AuditLog
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.product import (
    PlatformBundle,
    PlatformBundleProduct,
    Product,
    WorkspaceProduct,
)
from app.models.user import User
from app.main import app

pytestmark = pytest.mark.asyncio


async def create_workspace(
    db_session: AsyncSession,
    *,
    workspace_type: ClinicType = ClinicType.CLINIC,
    existing_user: User | None = None,
) -> tuple[Clinic, dict[str, str]]:
    clinic = Clinic(name=f"Marketplace Workspace {uuid.uuid4()}", type=workspace_type)
    user = existing_user or User(
        id=uuid.uuid4(),
        clinic_id=None,
        email=f"marketplace-{uuid.uuid4()}@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Market",
        last_name="User",
        is_active=True,
    )
    db_session.add_all([clinic, user] if existing_user is None else [clinic])
    await db_session.flush()
    db_session.add(
        Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN)
    )
    await db_session.commit()
    token = create_access_token(
        subject=user.id,
        clinic_id=clinic.id,
        role=UserRole.ADMIN.value,
    )
    return clinic, {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def create_product(
    db_session: AsyncSession,
    *,
    allowed_types: list[str] | None = None,
    is_active: bool = True,
) -> Product:
    key = f"market-{uuid.uuid4().hex}"
    product = Product(
        id=key,
        slug=key,
        name="Marketplace Test Product",
        description="Test product",
        allowed_clinic_types=allowed_types or [item.value for item in ClinicType],
        is_active=is_active,
    )
    db_session.add(product)
    await db_session.commit()
    return product


def marketplace_url(path: str) -> str:
    return f"{settings.API_V1_PREFIX}/marketplace{path}"


async def test_catalog_and_installed_products_are_workspace_scoped(
    client: AsyncClient, db_session: AsyncSession
):
    clinic, headers = await create_workspace(db_session)
    product = await create_product(db_session)
    db_session.add(
        WorkspaceProduct(
            clinic_id=clinic.id,
            product_id=product.id,
            status=EntitlementStatus.DISABLED,
        )
    )
    await db_session.commit()

    catalog = await client.get(marketplace_url("/products"), headers=headers)
    installed = await client.get(marketplace_url("/installed"), headers=headers)

    item = next(
        row for row in catalog.json()["data"] if row["product_key"] == product.slug
    )
    assert item["workspace_eligible"] is True
    assert item["installed"] is True
    assert item["enabled"] is False
    assert any(row["product_key"] == product.slug for row in installed.json()["data"])


async def test_install_is_idempotent_and_records_audit(
    client: AsyncClient, db_session: AsyncSession
):
    clinic, headers = await create_workspace(db_session)
    product = await create_product(db_session)
    url = marketplace_url(f"/products/{product.slug}/install")

    first = await client.post(url, headers=headers)
    second = await client.post(url, headers=headers)

    assert first.status_code == second.status_code == 200
    count = await db_session.scalar(
        select(func.count())
        .select_from(WorkspaceProduct)
        .where(
            WorkspaceProduct.clinic_id == clinic.id,
            WorkspaceProduct.product_id == product.id,
        )
    )
    assert count == 1
    assert first.json()["data"]["status"] == "enabled"


async def test_concurrent_product_and_bundle_install_are_idempotent(
    db_session: AsyncSession, sessionmaker
):
    clinic, headers = await create_workspace(db_session)
    direct_product = await create_product(db_session)
    bundle_products = [await create_product(db_session) for _ in range(2)]
    bundle = PlatformBundle(slug=f"bundle-{uuid.uuid4().hex}", name="Concurrent Bundle")
    db_session.add(bundle)
    await db_session.flush()
    db_session.add_all(
        [
            PlatformBundleProduct(bundle_id=bundle.id, product_id=item.id)
            for item in bundle_products
        ]
    )
    await db_session.commit()

    async def request_session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = request_session
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as parallel_client:
        product_responses = await asyncio.gather(
            *[
                parallel_client.post(
                    marketplace_url(f"/products/{direct_product.slug}/install"),
                    headers=headers,
                )
                for _ in range(2)
            ]
        )
        bundle_responses = await asyncio.gather(
            *[
                parallel_client.post(
                    marketplace_url(f"/bundles/{bundle.slug}/install"),
                    headers=headers,
                )
                for _ in range(2)
            ]
        )

    assert [response.status_code for response in product_responses] == [200, 200]
    assert [response.status_code for response in bundle_responses] == [200, 200]
    counts = await db_session.execute(
        select(WorkspaceProduct.product_id, func.count())
        .where(WorkspaceProduct.clinic_id == clinic.id)
        .group_by(WorkspaceProduct.product_id)
    )
    assert dict(counts.all()) == {
        direct_product.id: 1,
        bundle_products[0].id: 1,
        bundle_products[1].id: 1,
    }


async def test_enable_disable_are_idempotent_and_require_ownership(
    client: AsyncClient, db_session: AsyncSession
):
    _, headers = await create_workspace(db_session)
    product = await create_product(db_session)
    base = marketplace_url(f"/products/{product.slug}")

    assert (await client.post(f"{base}/enable", headers=headers)).status_code == 404
    assert (await client.post(f"{base}/install", headers=headers)).status_code == 200
    assert (await client.post(f"{base}/disable", headers=headers)).status_code == 200
    disabled = await client.post(f"{base}/disable", headers=headers)
    enabled = await client.post(f"{base}/enable", headers=headers)
    assert disabled.json()["data"]["status"] == "disabled"
    assert enabled.json()["data"]["status"] == "enabled"


async def test_install_rejects_workspace_type_and_inactive_product(
    client: AsyncClient, db_session: AsyncSession
):
    _, headers = await create_workspace(db_session, workspace_type=ClinicType.SOLO)
    restricted = await create_product(
        db_session, allowed_types=[ClinicType.CLINIC.value]
    )
    inactive = await create_product(db_session, is_active=False)

    restricted_result = await client.post(
        marketplace_url(f"/products/{restricted.slug}/install"), headers=headers
    )
    inactive_result = await client.post(
        marketplace_url(f"/products/{inactive.slug}/install"), headers=headers
    )
    catalog = await client.get(marketplace_url("/products"), headers=headers)

    assert restricted_result.status_code == 403
    assert inactive_result.status_code == 409
    assert all(row["product_key"] != inactive.slug for row in catalog.json()["data"])


async def test_inactive_product_can_still_be_disabled(
    client: AsyncClient, db_session: AsyncSession
):
    clinic, headers = await create_workspace(db_session)
    product = await create_product(db_session, is_active=False)
    db_session.add(
        WorkspaceProduct(
            clinic_id=clinic.id,
            product_id=product.id,
            status=EntitlementStatus.ENABLED,
        )
    )
    await db_session.commit()

    response = await client.post(
        marketplace_url(f"/products/{product.slug}/disable"), headers=headers
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "disabled"


async def test_inactive_bundle_is_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    _, headers = await create_workspace(db_session)
    bundle = PlatformBundle(
        slug=f"bundle-{uuid.uuid4().hex}",
        name="Inactive Bundle",
        is_active=False,
    )
    db_session.add(bundle)
    await db_session.commit()

    response = await client.post(
        marketplace_url(f"/bundles/{bundle.slug}/install"), headers=headers
    )

    assert response.status_code == 409


async def test_bundle_install_is_atomic_idempotent_and_extends_validity(
    client: AsyncClient, db_session: AsyncSession
):
    clinic, headers = await create_workspace(db_session)
    first_product = await create_product(db_session)
    second_product = await create_product(db_session)
    bundle = PlatformBundle(slug=f"bundle-{uuid.uuid4().hex}", name="Test Bundle")
    db_session.add(bundle)
    await db_session.flush()
    later_until = datetime.now(timezone.utc) + timedelta(days=30)
    db_session.add_all(
        [
            PlatformBundleProduct(
                bundle_id=bundle.id,
                product_id=first_product.id,
                valid_until=later_until,
            ),
            PlatformBundleProduct(bundle_id=bundle.id, product_id=second_product.id),
            WorkspaceProduct(
                clinic_id=clinic.id,
                product_id=first_product.id,
                valid_until=datetime.now(timezone.utc) + timedelta(days=5),
            ),
        ]
    )
    await db_session.commit()

    url = marketplace_url(f"/bundles/{bundle.slug}/install")
    first = await client.post(url, headers=headers)
    second = await client.post(url, headers=headers)

    assert first.status_code == second.status_code == 200
    assert len(first.json()["data"]["installed_products"]) == 1
    assert len(second.json()["data"]["installed_products"]) == 0
    assert len(second.json()["data"]["existing_products"]) == 2
    rows = (
        await db_session.scalars(
            select(WorkspaceProduct).where(WorkspaceProduct.clinic_id == clinic.id)
        )
    ).all()
    assert len(rows) == 2
    extended = next(row for row in rows if row.product_id == first_product.id)
    assert extended.valid_until is not None
    assert extended.valid_until.replace(tzinfo=timezone.utc) >= later_until


async def test_bundle_restriction_creates_no_partial_entitlements(
    client: AsyncClient, db_session: AsyncSession
):
    clinic, headers = await create_workspace(db_session, workspace_type=ClinicType.SOLO)
    eligible = await create_product(db_session)
    restricted = await create_product(
        db_session, allowed_types=[ClinicType.CLINIC.value]
    )
    bundle = PlatformBundle(slug=f"bundle-{uuid.uuid4().hex}", name="Restricted Bundle")
    db_session.add(bundle)
    await db_session.flush()
    db_session.add_all(
        [
            PlatformBundleProduct(bundle_id=bundle.id, product_id=eligible.id),
            PlatformBundleProduct(bundle_id=bundle.id, product_id=restricted.id),
        ]
    )
    await db_session.commit()

    response = await client.post(
        marketplace_url(f"/bundles/{bundle.slug}/install"), headers=headers
    )

    assert response.status_code == 403
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(WorkspaceProduct)
            .where(WorkspaceProduct.clinic_id == clinic.id)
        )
        == 0
    )


async def test_marketplace_isolated_between_workspaces(
    client: AsyncClient, db_session: AsyncSession
):
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email=f"marketplace-shared-{uuid.uuid4()}@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Shared",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    clinic_a, headers_a = await create_workspace(db_session, existing_user=user)
    clinic_b, headers_b = await create_workspace(
        db_session, workspace_type=ClinicType.PERSONAL, existing_user=user
    )
    product = await create_product(db_session)

    installed = await client.post(
        marketplace_url(f"/products/{product.slug}/install"), headers=headers_a
    )
    other_workspace = await client.get(marketplace_url("/installed"), headers=headers_b)

    assert installed.status_code == 200
    assert all(
        row["product_key"] != product.slug for row in other_workspace.json()["data"]
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(WorkspaceProduct)
            .where(
                WorkspaceProduct.clinic_id == clinic_b.id,
                WorkspaceProduct.product_id == product.id,
            )
        )
        == 0
    )
    assert clinic_a.id != clinic_b.id


async def test_marketplace_audits_enable_disable_and_bundle_actions(
    client: AsyncClient, db_session: AsyncSession
):
    clinic, headers = await create_workspace(db_session)
    product = await create_product(db_session)
    bundle_product = await create_product(db_session)
    bundle = PlatformBundle(slug=f"bundle-{uuid.uuid4().hex}", name="Audited Bundle")
    db_session.add(bundle)
    await db_session.flush()
    db_session.add(
        PlatformBundleProduct(bundle_id=bundle.id, product_id=bundle_product.id)
    )
    await db_session.commit()

    for suffix in (
        f"/products/{product.slug}/install",
        f"/products/{product.slug}/disable",
        f"/products/{product.slug}/enable",
        f"/bundles/{bundle.slug}/install",
    ):
        response = await client.post(marketplace_url(suffix), headers=headers)
        assert response.status_code == 200

    actions = set(
        (
            await db_session.scalars(
                select(AuditLog.action).where(AuditLog.clinic_id == clinic.id)
            )
        ).all()
    )
    assert {
        "product_installed",
        "product_enabled",
        "product_disabled",
        "bundle_installed",
    }.issubset(actions)
