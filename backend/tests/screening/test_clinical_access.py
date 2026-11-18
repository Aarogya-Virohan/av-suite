"""Who may be given screening.view / screening.refer (S-D-036, closes S-L-008).

Goes through the real permissions endpoint the CRM and the Tool 03 Access
page use, and checks the database after every call.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select, update

from app.core.config import settings
from app.core.security import get_password_hash
from app.enums.user import UserRole
from app.models.membership import Membership
from app.models.user import User
from app.models.user_permission import UserPermission
from app.screening.access import clinical_grants
from tests.screening.conftest import set_overrides, user_by_email

pytestmark = pytest.mark.asyncio

USERS = f"{settings.API_V1_PREFIX}/users"


def code_of(res) -> str:
    return res.json()["detail"]["code"]


async def overrides(db, clinic_id, user_id) -> dict[str, str]:
    rows = await db.execute(
        select(UserPermission.capability_key, UserPermission.scope).where(
            UserPermission.clinic_id == clinic_id,
            UserPermission.user_id == user_id,
            UserPermission.capability_key.like("screening.%"),
        )
    )
    return {k: str(getattr(s, "value", s)) for k, s in rows}


async def put(client, headers, user_id, grants: dict[str, str]):
    body = [{"capability_key": k, "scope": v} for k, v in grants.items()]
    return await client.put(f"{USERS}/{user_id}/permissions", json=body, headers=headers)


@pytest.fixture
async def frontdesk(db_session, env):
    user = await user_by_email(db_session, "frontdesk@avtest.com")
    yield user
    await set_overrides(db_session, env["clinic"].id, user.id, {})


# ---------------------------------------------------------------------------
# pure rule
# ---------------------------------------------------------------------------
def p(key, scope):
    return SimpleNamespace(capability_key=key, scope=scope)


def test_only_new_or_widened_clinical_grants_count():
    existing = [p("screening.view", "own")]
    assert clinical_grants([p("screening.view", "own")], existing) == []  # unchanged
    assert clinical_grants([p("screening.view", "all")], existing) == ["screening.view"]  # widened
    assert clinical_grants([p("screening.view", "none"), p("screening.refer", "none")], existing) == []
    assert clinical_grants([p("screening.assign", "all"), p("patients.view", "all")], []) == []
    assert clinical_grants([p("screening.refer", "own")], []) == ["screening.refer"]


# ---------------------------------------------------------------------------
# through the endpoint
# ---------------------------------------------------------------------------
async def test_admin_can_give_a_therapist_results(client, db_session, env, auth_headers):
    therapist = env["therapist"]
    res = await put(client, auth_headers, therapist.id, {"screening.view": "all", "screening.refer": "all"})
    assert res.status_code == 200, res.text
    assert await overrides(db_session, env["clinic"].id, therapist.id) == {
        "screening.view": "all",
        "screening.refer": "all",
    }


@pytest.mark.parametrize("key", ["screening.view", "screening.refer"])
async def test_front_desk_can_never_get_results(client, db_session, env, auth_headers, frontdesk, key):
    res = await put(client, auth_headers, frontdesk.id, {key: "own"})
    assert res.status_code == 403
    assert code_of(res) == "SCREENING_CLINICAL_ROLE"
    assert await overrides(db_session, env["clinic"].id, frontdesk.id) == {}


async def test_front_desk_can_still_send_links(client, db_session, env, auth_headers, frontdesk):
    res = await put(client, auth_headers, frontdesk.id, {"screening.assign": "all", "screening.view": "none"})
    assert res.status_code == 200, res.text
    assert await overrides(db_session, env["clinic"].id, frontdesk.id) == {
        "screening.assign": "all",
        "screening.view": "none",
    }


async def test_admin_cannot_give_themselves_results(client, db_session, env, auth_headers):
    admin = env["admin"]
    for key in ("screening.view", "screening.refer"):
        res = await put(client, auth_headers, admin.id, {key: "all"})
        assert res.status_code == 403
        assert code_of(res) == "SCREENING_SELF_GRANT"
    assert await overrides(db_session, env["clinic"].id, admin.id) == {}
    # Revoking is always fine.
    ok = await put(client, auth_headers, admin.id, {"screening.view": "none"})
    assert ok.status_code == 200, ok.text


async def test_solo_owner_can_give_themselves_results(client, db_session, env, auth_headers):
    """The only active staff member treats the patients too."""
    clinic_id, admin = env["clinic"].id, env["admin"]
    others = (
        await db_session.scalars(
            select(Membership.user_id).where(Membership.clinic_id == clinic_id, Membership.user_id != admin.id)
        )
    ).all()
    await db_session.execute(update(User).where(User.id.in_(others)).values(is_active=False))
    await db_session.commit()
    try:
        res = await put(client, auth_headers, admin.id, {"screening.view": "all", "screening.refer": "all"})
        assert res.status_code == 200, res.text
        assert (await overrides(db_session, clinic_id, admin.id))["screening.view"] == "all"
    finally:
        await db_session.execute(update(User).where(User.id.in_(others)).values(is_active=True))
        await db_session.commit()
        await set_overrides(db_session, clinic_id, admin.id, {})

    # A second staff member is back: the same request is refused again.
    res = await put(client, auth_headers, admin.id, {"screening.view": "all"})
    assert res.status_code == 403 and code_of(res) == "SCREENING_SELF_GRANT"


async def test_second_admin_can_give_an_admin_results(client, db_session, env):
    clinic_id, admin = env["clinic"].id, env["admin"]
    second = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin2-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash=get_password_hash("Password123!"),
        role=UserRole.ADMIN,
        first_name="Second",
        last_name="Admin",
        phone="9876543299",
        is_active=True,
    )
    db_session.add_all([second, Membership(user_id=second.id, clinic_id=clinic_id, role=UserRole.ADMIN)])
    await db_session.commit()
    try:
        login = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login", json={"email": second.email, "password": "Password123!"}
        )
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        res = await put(client, headers, admin.id, {"screening.view": "own"})
        assert res.status_code == 200, res.text
        assert (await overrides(db_session, clinic_id, admin.id))["screening.view"] == "own"
    finally:
        await set_overrides(db_session, clinic_id, admin.id, {})
        await db_session.execute(delete(UserPermission).where(UserPermission.user_id == second.id))
        await db_session.execute(delete(Membership).where(Membership.user_id == second.id))
        # Audit rows keep the user id, so the user stays, switched off.
        await db_session.execute(update(User).where(User.id == second.id).values(is_active=False))
        await db_session.commit()


async def test_unchanged_old_grant_does_not_block_other_changes(
    client, db_session, env, auth_headers, frontdesk
):
    """Saving a user's other permissions must not fail on an override set before this rule."""
    clinic_id = env["clinic"].id
    await set_overrides(db_session, clinic_id, frontdesk.id, {"screening.view": "own"})
    res = await put(client, auth_headers, frontdesk.id, {"screening.view": "own", "screening.assign": "all"})
    assert res.status_code == 200, res.text
    # Widening it is a new grant and is refused.
    res = await put(client, auth_headers, frontdesk.id, {"screening.view": "all", "screening.assign": "all"})
    assert res.status_code == 403 and code_of(res) == "SCREENING_CLINICAL_ROLE"
