import pytest
import uuid
from app.core.config import settings
from app.core.security import create_access_token
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.user import User


@pytest.mark.asyncio
async def test_clinic_profile_update_and_auth_me_for_staff(client, auth_headers, frontdesk_auth_headers):
    payload = {
        "address_line": "12 Clinic Road", "city": "Pune", "state": "Maharashtra",
        "pincode": "411001", "phone": "02012345678", "email": "clinic@example.com",
        "registration_number": "REG-1", "gstin": "22AAAAA0000A1Z5", "authorised_person": "Dr. Rao",
    }
    updated = await client.patch(f"{settings.API_V1_PREFIX}/settings/clinic", json=payload, headers=auth_headers)
    assert updated.status_code == 200, updated.text
    assert {key: updated.json()[key] for key in payload} == payload
    me = await client.get(f"{settings.API_V1_PREFIX}/auth/me", headers=frontdesk_auth_headers)
    assert me.status_code == 200, me.text
    assert {key: me.json()["data"]["clinic"][key] for key in payload} == payload
    cleared = await client.patch(f"{settings.API_V1_PREFIX}/settings/clinic", json={"address_line": None, "email": None}, headers=auth_headers)
    assert cleared.status_code == 200
    assert cleared.json()["address_line"] is None


@pytest.mark.asyncio
async def test_auth_me_clinic_profile_is_workspace_scoped(client, auth_headers, db_session):
    await client.patch(f"{settings.API_V1_PREFIX}/settings/clinic", json={"city": "First clinic"}, headers=auth_headers)
    clinic = Clinic(name="Second profile workspace", city="Second clinic")
    user = User(id=uuid.uuid4(), clinic_id=None, email=f"profile-{uuid.uuid4()}@example.com", password_hash="unused", role=UserRole.FRONT_DESK, first_name="Front", last_name="Desk", is_active=True)
    db_session.add_all([clinic, user])
    await db_session.flush()
    user.clinic_id = clinic.id
    db_session.add(Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.FRONT_DESK))
    await db_session.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=UserRole.FRONT_DESK.value)
    response = await client.get(f"{settings.API_V1_PREFIX}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["data"]["clinic"]["city"] == "Second clinic"


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("pincode", "12345"), ("pincode", "12A456"), ("gstin", "short"), ("email", "bad-email")])
async def test_clinic_profile_validation(client, auth_headers, field, value):
    response = await client.patch(f"{settings.API_V1_PREFIX}/settings/clinic", json={field: value}, headers=auth_headers)
    assert response.status_code == 422
