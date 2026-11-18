import uuid

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.clinic_fee_item import ClinicFeeItem
from app.models.membership import Membership
from app.models.user import User


@pytest.mark.asyncio
async def test_fee_item_crud_permissions_and_soft_delete(client, auth_headers, therapist_auth_headers, frontdesk_auth_headers):
    path = f"{settings.API_V1_PREFIX}/settings/fee-items"
    body = {"name": "Initial consultation", "category": "consultation", "default_price": "750.00", "price_editable": False}
    created = await client.post(path, json=body, headers=auth_headers)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["active"] is True
    assert (await client.get(path, headers=auth_headers)).json()[0]["id"] == item["id"]
    assert (await client.post(path, json=body, headers=therapist_auth_headers)).status_code == 403
    assert (await client.get(path, headers=frontdesk_auth_headers)).status_code == 403
    updated = await client.patch(f"{path}/{item['id']}", json={"default_price": "800.00"}, headers=auth_headers)
    assert updated.status_code == 200 and updated.json()["default_price"] == "800.00"
    deleted = await client.delete(f"{path}/{item['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert (await client.get(path, headers=auth_headers)).json() == []
    assert (await client.patch(f"{path}/{item['id']}", json={"name": "Reactivated?"}, headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ["consultation", "posture", "exercise_rx", "custom"])
async def test_fee_item_categories_and_validation(client, auth_headers, category):
    path = f"{settings.API_V1_PREFIX}/settings/fee-items"
    valid = await client.post(path, json={"name": category, "category": category, "default_price": "0"}, headers=auth_headers)
    assert valid.status_code == 201, valid.text
    invalid = await client.post(path, json={"name": "Bad", "category": "package", "default_price": -1}, headers=auth_headers)
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_fee_item_cross_clinic_isolation(client, auth_headers, db_session):
    other = Clinic(name="Fee item other clinic")
    user = User(id=uuid.uuid4(), email=f"fee-{uuid.uuid4()}@example.com", password_hash="unused", role=UserRole.ADMIN, first_name="Other", last_name="Admin", is_active=True)
    db_session.add_all([other, user])
    await db_session.flush()
    user.clinic_id = other.id
    db_session.add(Membership(user_id=user.id, clinic_id=other.id, role=UserRole.ADMIN))
    from app.services.product_entitlements import ensure_crm_entitlement
    await ensure_crm_entitlement(db_session, other.id)
    item = ClinicFeeItem(clinic_id=other.id, name="Other clinic item", category="custom", default_price=100)
    db_session.add(item)
    await db_session.commit()
    from app.core.security import create_access_token
    token = create_access_token(subject=user.id, clinic_id=other.id, role=UserRole.ADMIN.value)
    headers = {"Authorization": f"Bearer {token}"}
    # The seeded clinic cannot read or mutate an item belonging to another clinic.
    path = f"{settings.API_V1_PREFIX}/settings/fee-items/{item.id}"
    assert (await client.patch(path, json={"name": "Intrusion"}, headers=auth_headers)).status_code == 404
    assert (await client.delete(path, headers=auth_headers)).status_code == 404
    clinic_list = await client.get(
        f"{settings.API_V1_PREFIX}/settings/fee-items", headers=auth_headers
    )
    assert clinic_list.status_code == 200
    assert str(item.id) not in {record["id"] for record in clinic_list.json()}
    other_list = await client.get(f"{settings.API_V1_PREFIX}/settings/fee-items", headers=headers)
    assert other_list.status_code == 200, other_list.text
    assert other_list.json()[0]["id"] == str(item.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("client_type", ["clinic", "hospital", "home_care"])
async def test_client_type_profile_and_auth_me(client, auth_headers, db_session, client_type):
    prefix = settings.API_V1_PREFIX
    response = await client.patch(f"{prefix}/settings/clinic", json={"client_type": client_type}, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["client_type"] == client_type
    me = await client.get(f"{prefix}/auth/me", headers=auth_headers)
    assert me.status_code == 200 and me.json()["data"]["clinic"]["client_type"] == client_type
    clinic = await db_session.scalar(select(Clinic).where(Clinic.name == "Aarogya Seeded Test Clinic"))
    assert clinic.client_type == client_type
    assert clinic.type == "clinic"


@pytest.mark.asyncio
async def test_invalid_client_type_rejected(client, auth_headers):
    response = await client.patch(f"{settings.API_V1_PREFIX}/settings/clinic", json={"client_type": "lab"}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_fee_item_sort_order_is_bounded(client, auth_headers):
    api = settings.API_V1_PREFIX
    body = {"name": "Shockwave", "category": "custom", "default_price": "1500.00"}
    for value in (-1, 10_001, 3_000_000_000):
        response = await client.post(
            f"{api}/settings/fee-items", json={**body, "sort_order": value}, headers=auth_headers
        )
        assert response.status_code == 422, (value, response.text)
    created = await client.post(
        f"{api}/settings/fee-items", json={**body, "sort_order": 10_000}, headers=auth_headers
    )
    assert created.status_code == 201, created.text
    too_big = await client.patch(
        f"{api}/settings/fee-items/{created.json()['id']}",
        json={"sort_order": 3_000_000_000},
        headers=auth_headers,
    )
    assert too_big.status_code == 422


@pytest.mark.asyncio
async def test_fee_item_name_is_trimmed_and_not_blank(client, auth_headers):
    api = settings.API_V1_PREFIX
    blank = await client.post(
        f"{api}/settings/fee-items",
        json={"name": "   ", "category": "custom", "default_price": "10.00"},
        headers=auth_headers,
    )
    assert blank.status_code == 422
    created = await client.post(
        f"{api}/settings/fee-items",
        json={"name": "  Shockwave  ", "category": "custom", "default_price": "10.00"},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Shockwave"
    renamed = await client.patch(
        f"{api}/settings/fee-items/{created.json()['id']}", json={"name": "  "}, headers=auth_headers
    )
    assert renamed.status_code == 422
