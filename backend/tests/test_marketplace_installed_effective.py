"""U4: GET /marketplace/installed exposes is_effective using the shared
active_entitlement_clause (status enabled + inside valid window)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.product import EntitlementStatus
from app.models.product import WorkspaceProduct
from tests.test_marketplace_api import create_product, create_workspace, marketplace_url

pytestmark = pytest.mark.asyncio


async def test_installed_is_effective_flags(client: AsyncClient, db_session: AsyncSession):
    clinic, headers = await create_workspace(db_session)
    now = datetime.now(timezone.utc)
    cases = {
        "disabled": dict(status=EntitlementStatus.DISABLED),
        "expired": dict(status=EntitlementStatus.ENABLED, valid_until=now - timedelta(days=1)),
        "future": dict(status=EntitlementStatus.ENABLED, valid_from=now + timedelta(days=1)),
        "valid": dict(status=EntitlementStatus.ENABLED, valid_from=now - timedelta(days=1),
                      valid_until=now + timedelta(days=30)),
        "open": dict(status=EntitlementStatus.ENABLED),
    }
    keys = {}
    for label, fields in cases.items():
        product = await create_product(db_session)
        keys[product.slug] = label
        db_session.add(WorkspaceProduct(clinic_id=clinic.id, product_id=product.id, **fields))
    await db_session.commit()

    res = await client.get(marketplace_url("/installed"), headers=headers)
    assert res.status_code == 200, res.text
    rows = {keys[r["product_key"]]: r for r in res.json()["data"] if r["product_key"] in keys}
    assert {k: rows[k]["is_effective"] for k in rows} == {
        "disabled": False, "expired": False, "future": False, "valid": True, "open": True,
    }
    # additive: old fields still present
    for r in rows.values():
        for f in ("product_key", "name", "status", "source", "valid_from", "valid_until"):
            assert f in r
