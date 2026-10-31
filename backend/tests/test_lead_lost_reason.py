import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_lead_lost_reasons_and_clear_on_reopen(client, auth_headers):
    base = {"name": "Lost lead", "phone": "9000000000", "stage": "lost"}
    reasons = ["denied", "better_price", "asked_for_discount", "offer", "call_not_picked"]
    for reason in reasons:
        response = await client.post(f"{settings.API_V1_PREFIX}/leads", json={**base, "lost_reason": reason}, headers=auth_headers)
        assert response.status_code == 201, response.text
        assert response.json()["lost_reason"] == reason
        assert response.json()["lost_remark"] is None
    response = await client.post(f"{settings.API_V1_PREFIX}/leads", json={**base, "lost_reason": "other", "lost_remark": "Requested a later follow-up"}, headers=auth_headers)
    assert response.status_code == 201, response.text
    lead = response.json()
    assert lead["lost_reason"] == "other"
    assert len("x" * 500) == 500
    updated = await client.patch(f"{settings.API_V1_PREFIX}/leads/{lead['id']}", json={"lost_reason": "denied", "lost_remark": "x" * 500}, headers=auth_headers)
    assert updated.status_code == 200, updated.text
    assert len(updated.json()["lost_remark"]) == 500
    reopened = await client.patch(f"{settings.API_V1_PREFIX}/leads/{lead['id']}", json={"stage": "contacted"}, headers=auth_headers)
    assert reopened.status_code == 200
    assert reopened.json()["lost_reason"] is None
    assert reopened.json()["lost_remark"] is None


@pytest.mark.asyncio
async def test_lost_reason_validation(client, auth_headers):
    base = {"name": "Validation lead", "phone": "9000000001", "stage": "lost"}
    missing = await client.post(f"{settings.API_V1_PREFIX}/leads", json={**base, "lost_reason": "other"}, headers=auth_headers)
    invalid = await client.post(f"{settings.API_V1_PREFIX}/leads", json={**base, "lost_reason": "unknown"}, headers=auth_headers)
    too_long = await client.post(f"{settings.API_V1_PREFIX}/leads", json={**base, "lost_reason": "other", "lost_remark": "x" * 501}, headers=auth_headers)
    assert missing.status_code == 422
    assert invalid.status_code == 422
    assert too_long.status_code == 422


@pytest.mark.asyncio
async def test_update_other_reason_requires_remark(client, auth_headers):
    result = await client.post(f"{settings.API_V1_PREFIX}/leads", json={"name": "Update validation", "phone": "9000000002", "stage": "lost"}, headers=auth_headers)
    assert result.status_code == 201
    updated = await client.patch(f"{settings.API_V1_PREFIX}/leads/{result.json()['id']}", json={"lost_reason": "other"}, headers=auth_headers)
    assert updated.status_code == 422
