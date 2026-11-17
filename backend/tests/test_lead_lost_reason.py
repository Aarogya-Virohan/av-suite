import pytest
import uuid

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.user import User
from app.services.product_entitlements import ensure_crm_entitlement


@pytest.mark.asyncio
async def test_lead_lost_reasons_and_clear_on_reopen(client, auth_headers):
    base = {"name": "Lost lead", "phone": "9000000000", "stage": "lost"}
    reasons = ["denied", "better_price", "asked_for_discount", "offer", "call_not_picked", "too_far", "timing_mismatch", "needs_home_visit", "cannot_afford", "went_to_competitor"]
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
    base = {"name": "Validation lead", "phone": "9000000001"}
    created = await client.post(f"{settings.API_V1_PREFIX}/leads", json=base, headers=auth_headers)
    missing = await client.patch(f"{settings.API_V1_PREFIX}/leads/{created.json()['id']}", json={"stage": "lost"}, headers=auth_headers)
    invalid = await client.post(f"{settings.API_V1_PREFIX}/leads", json={**base, "lost_reason": "unknown"}, headers=auth_headers)
    too_long = await client.post(f"{settings.API_V1_PREFIX}/leads", json={**base, "lost_reason": "other", "lost_remark": "x" * 501}, headers=auth_headers)
    assert missing.status_code == 422
    assert invalid.status_code == 422
    assert too_long.status_code == 422


@pytest.mark.asyncio
async def test_update_other_reason_requires_remark(client, auth_headers):
    result = await client.post(f"{settings.API_V1_PREFIX}/leads", json={"name": "Update validation", "phone": "9000000002"}, headers=auth_headers)
    assert result.status_code == 201
    updated = await client.patch(f"{settings.API_V1_PREFIX}/leads/{result.json()['id']}", json={"stage": "lost", "lost_reason": "other"}, headers=auth_headers)
    assert updated.status_code == 422


@pytest.mark.asyncio
async def test_transition_into_lost_requires_reason_and_persists_reason(client, auth_headers):
    base = {"name": "Transition lead", "phone": "9000000003"}
    created = await client.post(f"{settings.API_V1_PREFIX}/leads", json=base, headers=auth_headers)
    assert created.status_code == 201
    missing = await client.patch(
        f"{settings.API_V1_PREFIX}/leads/{created.json()['id']}",
        json={"stage": "lost"},
        headers=auth_headers,
    )
    assert missing.status_code == 422
    moved = await client.patch(
        f"{settings.API_V1_PREFIX}/leads/{created.json()['id']}",
        json={"stage": "lost", "lost_reason": "too_far"},
        headers=auth_headers,
    )
    assert moved.status_code == 200
    assert moved.json()["lost_reason"] == "too_far"


@pytest.mark.asyncio
async def test_converting_lost_lead_clears_lost_fields(client, db_session):
    clinic = Clinic(name="Lost lead conversion clinic")
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email=f"lost-conversion-{uuid.uuid4()}@example.com",
        password_hash="unused",
        role=UserRole.ADMIN,
        first_name="Conversion",
        last_name="Admin",
        is_active=True,
    )
    db_session.add_all([clinic, user])
    await db_session.flush()
    user.clinic_id = clinic.id
    db_session.add(Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN))
    await ensure_crm_entitlement(db_session, clinic.id)
    await db_session.commit()
    headers = {
        "Authorization": f"Bearer {create_access_token(subject=user.id, clinic_id=clinic.id, role=UserRole.ADMIN.value)}"
    }
    created = await client.post(
        f"{settings.API_V1_PREFIX}/leads",
        json={
            "name": "Convert lost lead",
            "phone": "9000000004",
            "stage": "lost",
            "lost_reason": "denied",
        },
        headers=headers,
    )
    assert created.status_code == 201
    converted = await client.post(
        f"{settings.API_V1_PREFIX}/leads/{created.json()['id']}/convert",
        headers=headers,
    )
    assert converted.status_code == 200, converted.text
    lead = converted.json().get("data", converted.json()).get("lead", {})
    assert lead["stage"] == "converted"
    assert lead["lost_reason"] is None
    assert lead["lost_remark"] is None
