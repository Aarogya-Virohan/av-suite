import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_billing_analytics_and_settings(client: AsyncClient, auth_headers: dict):
    # 1. Test Invoices List
    inv_res = await client.get(f"{settings.API_V1_PREFIX}/invoices", headers=auth_headers)
    assert inv_res.status_code == 200

    # 2. Test Payments List
    pay_res = await client.get(f"{settings.API_V1_PREFIX}/payments", headers=auth_headers)
    assert pay_res.status_code == 200

    # 3. Test Analytics Overview
    analytics_res = await client.get(f"{settings.API_V1_PREFIX}/analytics/overview", headers=auth_headers)
    assert analytics_res.status_code == 200

    # 4. Test Clinic Settings
    settings_res = await client.get(f"{settings.API_V1_PREFIX}/settings/clinic", headers=auth_headers)
    assert settings_res.status_code == 200

    # 5. Test Recycle Bin
    recycle_res = await client.get(f"{settings.API_V1_PREFIX}/recycle-bin", headers=auth_headers)
    assert recycle_res.status_code == 200

    # 6. Test Audit Logs
    audit_res = await client.get(f"{settings.API_V1_PREFIX}/audit-logs", headers=auth_headers)
    assert audit_res.status_code == 200
