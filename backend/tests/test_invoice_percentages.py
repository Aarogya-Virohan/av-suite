from uuid import UUID

import pytest
from app.core.config import settings


async def _patient(client, auth_headers):
    result = await client.post(f"{settings.API_V1_PREFIX}/patients", json={"first_name": "Percent", "last_name": "Test", "phone": "9898765001"}, headers=auth_headers)
    assert result.status_code in (200, 201), result.text
    return result.json()["data"]["id"]


async def _invoice(client, auth_headers, patient_id, **fields):
    return await client.post(f"{settings.API_V1_PREFIX}/invoices", json={"patient_id": patient_id, "issue_date": "2026-10-20T10:00:00Z", "items": [{"description": "Care", "quantity": 1, "unit_price": "1000.00"}], **fields}, headers=auth_headers)


@pytest.mark.asyncio
async def test_percentage_calculation_rounding_and_legacy(client, auth_headers):
    patient_id = await _patient(client, auth_headers)
    result = await _invoice(client, auth_headers, patient_id, discount_percent="10", tax_percent="18")
    assert result.status_code == 201, result.text
    data = result.json()
    assert data["discount_amount"] == "100.00"
    assert data["tax_amount"] == "162.00"
    assert data["total_amount"] == "1062.00"
    assert data["discount_percent"] == "10.00"
    assert data["tax_percent"] == "18.00"

    rounded = await _invoice(client, auth_headers, patient_id, discount_percent="0.01")
    assert rounded.status_code == 201
    assert rounded.json()["discount_amount"] == "0.10"

    legacy = await _invoice(client, auth_headers, patient_id)
    assert legacy.status_code == 201
    assert legacy.json()["discount_percent"] is None
    assert legacy.json()["total_amount"] == "1000.00"


@pytest.mark.asyncio
async def test_percentage_amount_consistency_and_update(client, auth_headers):
    patient_id = await _patient(client, auth_headers)
    match = await _invoice(client, auth_headers, patient_id, discount_percent="10", discount_amount="100.00", tax_percent="18", tax_amount="162.00")
    assert match.status_code == 201, match.text
    mismatch = await _invoice(client, auth_headers, patient_id, discount_percent="10", discount_amount="99.00")
    assert mismatch.status_code == 422
    changed = await client.patch(f"{settings.API_V1_PREFIX}/invoices/{match.json()['id']}", json={"discount_percent": "20"}, headers=auth_headers)
    assert changed.status_code == 200, changed.text
    assert changed.json()["discount_amount"] == "200.00"
    assert changed.json()["total_amount"] == "944.00"

    invalid = await _invoice(client, auth_headers, patient_id, tax_percent="-1")
    precision = await _invoice(client, auth_headers, patient_id, discount_percent="1.234")
    assert invalid.status_code == 422
    assert precision.status_code == 422
