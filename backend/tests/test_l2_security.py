"""L2 backend core: regression tests for BE-1, BE-3, BE-4 and audit fixes
AUD-01, AUD-02, AUD-04, AUD-06, AUD-07 (claude/ref/audit.md)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.enums.product import EntitlementSource, EntitlementStatus
from app.models.membership import Membership
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission
from app.services.product_entitlements import ensure_canonical_products

API = settings.API_V1_PREFIX
TOOLS = ["psycho-social-screening", "exercise-library", "posture-tool"]


async def register(client: AsyncClient, name: str = "L2 Clinic") -> tuple[uuid.UUID, dict, str]:
    email = f"l2-{uuid.uuid4()}@avtest.com"
    res = await client.post(
        f"{API}/auth/register",
        json={
            "clinic_name": name,
            "email": email,
            "password": "Password123!",
            "first_name": "Owner",
            "last_name": "Admin",
        },
    )
    assert res.status_code == 201, res.text
    token = res.json()["data"]["access_token"]
    return uuid.UUID(decode_token(token)["clinic_id"]), {"Authorization": f"Bearer {token}"}, email


async def entitle(db: AsyncSession, clinic_id: uuid.UUID, *product_ids: str) -> None:
    await ensure_canonical_products(db)
    for pid in product_ids:
        db.add(
            WorkspaceProduct(
                clinic_id=clinic_id,
                product_id=pid,
                status=EntitlementStatus.ENABLED,
                source=EntitlementSource.DIRECT,
            )
        )
    await db.commit()


ALL_TOOL_PRODUCTS = ("exercise-library", "exercise-prescription", "posture-tool", "psycho-social-screening")


async def staff(client, headers, *, role="therapist", tools=None, email=None):
    body = {
        "email": email or f"staff-{uuid.uuid4()}@avtest.com",
        "password": "Password123!",
        "first_name": "Staff",
        "last_name": "Member",
        "role": role,
    }
    if tools is not None:
        body["tools"] = tools
    return await client.post(f"{API}/users", json=body, headers=headers)


async def login(client, email, password="Password123!"):
    return await client.post(f"{API}/auth/login", json={"email": email, "password": password})


# --- AUD-04: self-signup closed -------------------------------------------

@pytest.mark.asyncio
async def test_register_is_404_when_signup_disabled(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "SELF_SIGNUP_ENABLED", False)
    res = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "x", "email": "admin@avtest.com", "password": "Password123!",
              "first_name": "a", "last_name": "b"},
    )
    # existing email must not leak as 409 either (enumeration)
    assert res.status_code == 404
    res = await client.post(f"{API}/auth/register", json={})
    assert res.status_code in (404, 422)


def test_register_hidden_from_openapi_and_default_off():
    from app.core.config import Settings
    from app.main import app

    assert "/api/v1/auth/register" not in app.openapi()["paths"]
    assert Settings.model_fields["SELF_SIGNUP_ENABLED"].default is False


# --- AUD-02 / BE-4: bad tokens are 401 ---------------------------------------

def _token(**over):
    claims = {"sub": str(uuid.uuid4()), "clinic_id": str(uuid.uuid4()),
              "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    claims.update(over)
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.parametrize("path,method", [("/auth/me", "get"), ("/auth/switch-workspace", "post"), ("/patients", "get"), ("/users", "get")])
@pytest.mark.asyncio
async def test_bad_tokens_are_401(client: AsyncClient, path, method):
    expired = _token(exp=datetime.now(timezone.utc) - timedelta(minutes=1))
    bad_sig = jwt.encode({"sub": str(uuid.uuid4()), "clinic_id": str(uuid.uuid4()),
                          "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                         "wrong-secret-wrong-secret-wrong-secret", algorithm="HS256")
    no_sub = _token(sub=None)
    for value in (f"Bearer {expired}", f"Bearer {bad_sig}", "Bearer abc", "Bearer ", f"Bearer {no_sub}"):
        kwargs = {"headers": {"Authorization": value}}
        if method == "post":
            kwargs["json"] = {"clinic_id": str(uuid.uuid4())}
        res = await getattr(client, method)(f"{API}{path}", **kwargs)
        assert res.status_code == 401, (path, value[:20], res.status_code, res.text)


# --- AUD-01: POST /users never attaches an existing account -----------------

@pytest.mark.asyncio
async def test_existing_email_other_clinic_is_409_without_pii(client: AsyncClient, db_session: AsyncSession):
    victim_clinic, victim_headers, victim_email = await register(client, "Victim")
    _, attacker_headers, _ = await register(client, "Attacker")

    res = await staff(client, attacker_headers, email=victim_email.upper())
    assert res.status_code == 409
    body = res.text
    assert "Owner" not in body and "Admin" not in body and victim_email not in body
    assert res.json()["detail"]["code"] == "EMAIL_TAKEN"

    victim = await db_session.scalar(select(User).where(User.email == victim_email))
    memberships = (await db_session.scalars(select(Membership).where(Membership.user_id == victim.id))).all()
    assert [m.clinic_id for m in memberships] == [victim_clinic]
    assert (await login(client, victim_email)).status_code == 200


@pytest.mark.asyncio
async def test_existing_email_same_clinic_is_409(client: AsyncClient):
    _, headers, _ = await register(client)
    email = f"dup-{uuid.uuid4()}@avtest.com"
    assert (await staff(client, headers, email=email)).status_code == 201
    assert (await staff(client, headers, email=email)).status_code == 409


# --- BE-1: tool checkboxes ---------------------------------------------------

@pytest.mark.asyncio
async def test_create_with_tools_grants_bundle_and_reads_back(client: AsyncClient, db_session: AsyncSession):
    clinic_id, headers, _ = await register(client)
    await entitle(db_session, clinic_id, *ALL_TOOL_PRODUCTS)

    res = await staff(client, headers, tools=["exercise-library", "posture-tool"])
    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert data["tools"] == {"psycho-social-screening": False, "exercise-library": True, "posture-tool": True}

    uid = uuid.UUID(data["id"])
    rows = {p.capability_key: p.scope.value for p in (await db_session.scalars(
        select(UserPermission).where(UserPermission.user_id == uid))).all()}
    assert rows == {"exercises.view": "all", "prescriptions.view": "all", "prescriptions.create": "all",
                    "prescriptions.edit": "own", "posture.view": "all", "posture.create": "all"}

    listed = (await client.get(f"{API}/users", headers=headers)).json()["data"]
    me = next(u for u in listed if u["id"] == data["id"])
    assert me["tools"]["posture-tool"] is True
    owner = next(u for u in listed if u["role"] == "admin")
    # admin template has all tools except screening answers
    assert owner["tools"]["exercise-library"] is True

    got = (await client.get(f"{API}/users/{uid}/tools", headers=headers)).json()["data"]
    assert got["available"] == {t: True for t in TOOLS}
    assert got["labels"]["psycho-social-screening"] == "Psychosocial"


@pytest.mark.asyncio
async def test_put_tools_replaces_and_unchecks(client: AsyncClient, db_session: AsyncSession):
    clinic_id, headers, _ = await register(client)
    await entitle(db_session, clinic_id, *ALL_TOOL_PRODUCTS)
    uid = (await staff(client, headers, tools=["posture-tool"])).json()["data"]["id"]

    res = await client.put(f"{API}/users/{uid}/tools", json={"tools": ["psycho-social-screening"]}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["tools"] == {"psycho-social-screening": True, "exercise-library": False, "posture-tool": False}

    res = await client.put(f"{API}/users/{uid}/tools", json={"tools": []}, headers=headers)
    assert res.json()["data"]["tools"] == {t: False for t in TOOLS}


@pytest.mark.asyncio
async def test_tool_not_in_plan_is_400_and_unknown_is_422(client: AsyncClient):
    _, headers, _ = await register(client)  # CRM only
    res = await staff(client, headers, tools=["posture-tool"])
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "TOOL_NOT_IN_PLAN"
    res = await staff(client, headers, tools=["chatbot"])
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_front_desk_psychosocial_is_assign_only(client: AsyncClient, db_session: AsyncSession):
    clinic_id, headers, _ = await register(client)
    await entitle(db_session, clinic_id, *ALL_TOOL_PRODUCTS)
    res = await staff(client, headers, role="front_desk", tools=["psycho-social-screening"])
    assert res.status_code == 201, res.text
    uid = uuid.UUID(res.json()["data"]["id"])
    keys = {p.capability_key for p in (await db_session.scalars(
        select(UserPermission).where(UserPermission.user_id == uid))).all()}
    assert keys == {"screening.assign"}
    assert res.json()["data"]["tools"]["psycho-social-screening"] is True


@pytest.mark.asyncio
async def test_tools_need_permissions_edit(client: AsyncClient, db_session: AsyncSession):
    clinic_id, headers, _ = await register(client)
    await entitle(db_session, clinic_id, *ALL_TOOL_PRODUCTS)
    # a front desk user who may create users but not edit permissions
    fd_email = f"fd-{uuid.uuid4()}@avtest.com"
    fd_id = (await staff(client, headers, role="front_desk", email=fd_email)).json()["data"]["id"]
    put = await client.put(f"{API}/users/{fd_id}/permissions",
                           json=[{"capability_key": "users.create", "scope": "all"}], headers=headers)
    assert put.status_code == 200, put.text
    token = (await login(client, fd_email)).json()["data"]["access_token"]
    fd_headers = {"Authorization": f"Bearer {token}"}
    assert (await staff(client, fd_headers, tools=["posture-tool"])).status_code == 403
    assert (await staff(client, fd_headers)).status_code == 201
    assert (await client.put(f"{API}/users/{fd_id}/tools", json={"tools": []}, headers=fd_headers)).status_code == 403


@pytest.mark.asyncio
async def test_tools_on_other_clinic_user_is_404(client: AsyncClient):
    _, a, _ = await register(client, "A")
    _, b, _ = await register(client, "B")
    uid = (await staff(client, b)).json()["data"]["id"]
    assert (await client.put(f"{API}/users/{uid}/tools", json={"tools": []}, headers=a)).status_code == 404
    assert (await client.get(f"{API}/users/{uid}/tools", headers=a)).status_code == 404


# --- AUD-07: same override in two clinics -----------------------------------

@pytest.mark.asyncio
async def test_same_override_in_two_clinics(client: AsyncClient, db_session: AsyncSession):
    clinic_a, headers_a, _ = await register(client, "A")
    clinic_b, _, _ = await register(client, "B")
    uid = uuid.UUID((await staff(client, headers_a)).json()["data"]["id"])
    # platform-made second membership (console / script), same capability in B
    db_session.add(Membership(user_id=uid, clinic_id=clinic_b, role="therapist"))
    db_session.add(UserPermission(clinic_id=clinic_b, user_id=uid, capability_key="patients.view", scope="all"))
    await db_session.commit()
    res = await client.put(f"{API}/users/{uid}/permissions",
                           json=[{"capability_key": "patients.view", "scope": "all"}], headers=headers_a)
    assert res.status_code == 200, res.text
    rows = (await db_session.scalars(select(UserPermission).where(
        UserPermission.user_id == uid, UserPermission.capability_key == "patients.view"))).all()
    assert {r.clinic_id for r in rows} == {clinic_a, clinic_b}


# --- BE-3: marketplace writes closed ----------------------------------------

@pytest.mark.parametrize("path", ["/products/posture-tool/install", "/products/posture-tool/enable",
                                  "/products/posture-tool/disable", "/bundles/any/install"])
@pytest.mark.asyncio
async def test_marketplace_writes_closed(client: AsyncClient, path):
    _, headers, _ = await register(client)
    res = await client.post(f"{API}/marketplace{path}", headers=headers)
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "MARKETPLACE_CLOSED"
    assert (await client.get(f"{API}/marketplace/installed", headers=headers)).status_code == 200


# --- AUD-06: booking approve -------------------------------------------------

async def _booking_request(client, clinic_id):
    res = await client.post(
        f"{API}/booking/request",
        params={"clinic_id": str(clinic_id)},
        json={"name": "Walk In", "phone": f"9{uuid.uuid4().int % 10**9:09d}", "age": 30,
              "gender": "male", "chief_complaint": "neck"},
    )
    assert res.status_code == 201, res.text
    data = res.json().get("data", res.json())
    return data["id"]


@pytest.mark.asyncio
async def test_approve_without_or_foreign_therapist_is_400(client: AsyncClient, db_session: AsyncSession):
    clinic_a, headers_a, _ = await register(client, "A")
    _, headers_b, _ = await register(client, "B")
    foreign = (await staff(client, headers_b)).json()["data"]["id"]
    own = (await staff(client, headers_a)).json()["data"]["id"]
    req_id = await _booking_request(client, clinic_a)

    url = f"{API}/appointment-requests/{req_id}/approve"
    assert (await client.post(url, json={}, headers=headers_a)).status_code == 400
    assert (await client.post(url, json={"therapist_id": foreign}, headers=headers_a)).status_code == 400
    assert (await client.post(url, json={"therapist_id": str(uuid.uuid4())}, headers=headers_a)).status_code == 400
    ok = await client.post(url, json={"therapist_id": own}, headers=headers_a)
    assert ok.status_code == 200, ok.text


# --- AUD-03: no real connection string in the setup guide ---------------------

def test_supabase_guide_has_no_real_connection_string():
    import pathlib
    import re

    text = (pathlib.Path(__file__).resolve().parents[1] / "SUPABASE_SETUP_GUIDE.md").read_text()
    for m in re.finditer(r"postgres(?:ql)?(?:\+asyncpg)?://([^:\s]+):([^@\s]+)@", text):
        user, password = m.groups()
        assert "<" in password or password.upper() in {"PASSWORD", "YOUR-PASSWORD", "[YOUR-PASSWORD]"}, m.group(0)[:40]
