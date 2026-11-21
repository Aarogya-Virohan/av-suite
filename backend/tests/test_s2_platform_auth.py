from datetime import datetime, timezone
import base64, hashlib, hmac, struct, time, uuid
from datetime import timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.platform_security import encrypt_mfa_secret, new_totp_secret, create_platform_access_token
from app.core.security import get_password_hash
from app.models.platform import PlatformOperator, PlatformAuditLog
from app.services.platform_operator_lifecycle import ensure_another_active_owner_remains
from app.exceptions import BaseAppException


def current_code(secret):
    return current_code_at(secret, int(time.time()) // 30)


def current_code_at(secret, counter):
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff) % 1_000_000
    return f"{value:06d}"


@pytest.mark.asyncio
async def test_platform_login_enrollment_and_challenge_single_use(client, db_session):
    op = PlatformOperator(email="owner@example.com", password_hash=get_password_hash("Passw0rd!"), name="Owner", role="owner")
    db_session.add(op)
    await db_session.commit()
    unknown = await client.post("/api/v1/platform/auth/login", json={"email": "missing@example.com", "password": "Passw0rd!"})
    wrong = await client.post("/api/v1/platform/auth/login", json={"email": "owner@example.com", "password": "wrong"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()
    login = await client.post("/api/v1/platform/auth/login", json={"email": "owner@example.com", "password": "Passw0rd!"})
    data = login.json()["data"]
    assert data["mfa_enrolment_required"] is True
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert "access_token" not in str(login.json())
    secret = (await db_session.get(PlatformOperator, op.id)).mfa_secret
    assert secret != data["otpauth_uri"].split("secret=")[1].split("&")[0]
    invalid = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": data["challenge_token"], "code": "000000"})
    assert invalid.status_code == 401
    assert invalid.json()["meta"]["error"]["code"] == "MFA_INVALID"
    secret = __import__("app.core.platform_security", fromlist=["decrypt_mfa_secret"]).decrypt_mfa_secret(secret)
    success = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": data["challenge_token"], "code": current_code(secret)})
    assert success.status_code == 200
    result = success.json()["data"]
    assert result["expires_in"] == 28800
    assert result["operator"]["mfa_enabled"] is True
    assert not ({"mfa_secret", "password_hash", "password", "recovery_codes"} & result["operator"].keys())
    claims = jwt.decode(result["access_token"], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], audience="av-platform")
    assert claims["sub"] == str(op.id)
    assert claims["aud"] == "av-platform" and claims["typ"] == "platform" and claims["ver"] == 0
    assert claims["exp"] > int(time.time())
    reuse = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": data["challenge_token"], "code": current_code(secret)})
    assert reuse.status_code == 401
    second_login = await client.post("/api/v1/platform/auth/login", json={"email": "owner@example.com", "password": "Passw0rd!"})
    assert second_login.json()["data"]["mfa_enrolment_required"] is False
    assert second_login.json()["data"]["otpauth_uri"] is None
    replay = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": second_login.json()["data"]["challenge_token"], "code": current_code(secret)})
    assert replay.status_code == 401
    assert replay.json()["meta"]["error"]["code"] == "MFA_INVALID"
    current_step = int(time.time()) // 30
    second_mfa = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": second_login.json()["data"]["challenge_token"], "code": current_code_at(secret, current_step + 1)})
    assert second_mfa.status_code == 200
    first_token_still_valid = await client.get("/api/v1/platform/operators", headers={"Authorization": f"Bearer {result['access_token']}"})
    assert first_token_still_valid.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_mfa_submissions_accept_same_step_once(client, db_session, sessionmaker):
    import asyncio
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.database import get_db
    from app.core.platform_security import create_platform_challenge

    secret = new_totp_secret()
    op = PlatformOperator(email="race@example.com", password_hash=get_password_hash("Passw0rd!"), name="Race", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(secret))
    db_session.add(op)
    await db_session.commit()
    payload = {"challenge_token": create_platform_challenge(op), "code": current_code(secret)}

    async def committed_session():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = committed_session
    try:
        async def submit():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as isolated_client:
                return await isolated_client.post("/api/v1/platform/auth/mfa", json=payload)
        responses = await asyncio.gather(submit(), submit())
    finally:
        app.dependency_overrides.clear()
    assert sorted(response.status_code for response in responses) == [200, 401]
    loser = next(response for response in responses if response.status_code == 401)
    assert loser.json()["meta"]["error"]["code"] in {"MFA_INVALID", "UNAUTHORIZED"}


@pytest.mark.asyncio
async def test_concurrent_owner_deactivation_preserves_active_owner(client, db_session, sessionmaker):
    import asyncio
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.database import get_db

    owners = [PlatformOperator(email=f"race-owner-{n}@example.com", password_hash=get_password_hash("Passw0rd!"), name="Owner", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret())) for n in range(2)]
    db_session.add_all(owners)
    await db_session.commit()
    tokens = [create_platform_access_token(owner) for owner in owners]

    async def committed_session():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = committed_session
    try:
        async def deactivate(actor_index):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as isolated_client:
                return await isolated_client.patch(
                    f"/api/v1/platform/operators/{owners[1-actor_index].id}",
                    headers={"Authorization": f"Bearer {tokens[actor_index]}"},
                    json={"is_active": False, "reason": "concurrent lifecycle test"},
                )
        responses = await asyncio.gather(deactivate(0), deactivate(1))
    finally:
        app.dependency_overrides.clear()
    assert sorted(response.status_code for response in responses) == [200, 401]
    async with sessionmaker() as session:
        active_count = await session.scalar(select(__import__("sqlalchemy").func.count()).select_from(PlatformOperator).where(PlatformOperator.id.in_([owner.id for owner in owners]), PlatformOperator.role == "owner", PlatformOperator.is_active.is_(True)))
    assert active_count == 1


@pytest.mark.asyncio
async def test_audit_write_failure_rolls_back_operator_change(client, db_session, sessionmaker, monkeypatch):
    import uuid
    import pytest
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.database import get_db
    from app.models.platform import PlatformAuditLog
    import app.api.v1.platform_auth as platform_auth

    owner = PlatformOperator(email="rollback-owner@example.com", password_hash=get_password_hash("Passw0rd!"), name="Owner", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    target = PlatformOperator(email="rollback-target@example.com", password_hash=get_password_hash("Passw0rd!"), name="Support", role="support", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    db_session.add_all([owner, target])
    await db_session.commit()
    token = create_platform_access_token(owner)

    def fail_audit(session, **kwargs):
        session.add(PlatformAuditLog(operator_id=uuid.uuid4(), action="forced.failure", target_type="operator", details={}))
    monkeypatch.setattr(platform_auth, "record_platform_audit", fail_audit)

    async def committed_session():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = committed_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as isolated_client:
            with pytest.raises(Exception):
                await isolated_client.patch(f"/api/v1/platform/operators/{target.id}", headers={"Authorization": f"Bearer {token}"}, json={"is_active": False, "reason": "rollback"})
    finally:
        app.dependency_overrides.clear()
    async with sessionmaker() as session:
        persisted = await session.get(PlatformOperator, target.id)
        assert persisted.is_active is True and persisted.token_version == 0


@pytest.mark.asyncio
async def test_platform_token_isolation_and_operator_deactivation(client, db_session, auth_headers):
    owner = PlatformOperator(email="owner2@example.com", password_hash=get_password_hash("Passw0rd!"), name="Owner", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    support = PlatformOperator(email="support@example.com", password_hash=get_password_hash("Passw0rd!"), name="Support", role="support", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    db_session.add_all([owner, support])
    await db_session.commit()
    owner_token = create_platform_access_token(owner)
    support_token_before_deactivation = create_platform_access_token(support)
    headers = {"Authorization": f"Bearer {owner_token}"}
    clinic_to_platform = await client.get("/api/v1/platform/operators", headers=auth_headers)
    clinic_to_platform_login = await client.post("/api/v1/platform/auth/login", headers=auth_headers, json={"email": "owner2@example.com", "password": "Passw0rd!"})
    platform_to_clinic = await client.get("/api/v1/patients", headers=headers)
    assert clinic_to_platform.status_code == 401
    assert clinic_to_platform_login.status_code == 401
    assert platform_to_clinic.status_code == 401
    response = await client.patch(f"/api/v1/platform/operators/{support.id}", headers=headers, json={"is_active": False, "reason": "Access removed"})
    assert response.status_code == 200
    await db_session.flush()
    audit = await db_session.scalar(select(PlatformAuditLog).where(PlatformAuditLog.target_id == str(support.id)))
    assert audit.action == "operator.deactivated" and audit.reason == "Access removed"
    denied = await client.get("/api/v1/platform/operators", headers={"Authorization": f"Bearer {support_token_before_deactivation}"})
    assert denied.status_code == 401
    assert denied.json()["meta"]["error"]["code"] == "UNAUTHORIZED"
    assert audit.details == {"before": {"is_active": True, "role": "support"}, "after": {"is_active": False, "role": "support"}}


@pytest.mark.asyncio
async def test_platform_operator_lifecycle_safety(client, db_session):
    owner = PlatformOperator(email="last@example.com", password_hash=get_password_hash("Passw0rd!"), name="Owner", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    another_owner = PlatformOperator(email="another-last@example.com", password_hash=get_password_hash("Passw0rd!"), name="Another Owner", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    db_session.add_all([owner, another_owner])
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    self_deactivate = await client.patch(f"/api/v1/platform/operators/{owner.id}", headers=headers, json={"is_active": False, "reason": "self"})
    assert self_deactivate.status_code == 422
    assert self_deactivate.json()["data"] is None
    assert self_deactivate.json()["meta"]["error"]["code"] == "VALIDATION_ERROR"
    # This helper remains the service-level invariant used by API and CLI paths.
    with pytest.raises(BaseAppException) as last_owner:
        ensure_another_active_owner_remains(1)
    assert last_owner.value.status_code == 409
    assert last_owner.value.code == "CONFLICT"


@pytest.mark.asyncio
async def test_platform_challenge_expiration_and_invalid_audience(client, db_session):
    op = PlatformOperator(email="expiry@example.com", password_hash=get_password_hash("Passw0rd!"), name="Expiry", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    db_session.add(op)
    await db_session.commit()
    from app.core.platform_security import create_platform_challenge
    valid_claims = jwt.decode(create_platform_challenge(op), options={"verify_signature": False, "verify_exp": False})
    valid_claims["exp"] = 1
    expired = jwt.encode(valid_claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    response = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": expired, "code": "123456"})
    assert response.status_code == 401
    assert response.json()["meta"]["error"]["code"] == "UNAUTHORIZED"
    assert set(response.json()) == {"data", "meta"}
    wrong_audience = jwt.encode({"sub": str(op.id), "aud": "clinic", "typ": "platform", "ver": 0, "exp": int(time.time()) + 300}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    denied = await client.get("/api/v1/platform/operators", headers={"Authorization": f"Bearer {wrong_audience}"})
    assert denied.status_code == 401
    assert denied.json()["meta"]["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_platform_role_and_reason_rules(client, db_session):
    owner = PlatformOperator(email="rules-owner@example.com", password_hash=get_password_hash("Passw0rd!"), name="Owner", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    support = PlatformOperator(email="rules-support@example.com", password_hash=get_password_hash("Passw0rd!"), name="Support", role="support", is_active=False, mfa_enabled=False)
    inactive_owner = PlatformOperator(email="rules-inactive-owner@example.com", password_hash=get_password_hash("Passw0rd!"), name="Owner 2", role="owner", is_active=False, mfa_enabled=False)
    db_session.add_all([owner, support, inactive_owner])
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    role_change = await client.patch(f"/api/v1/platform/operators/{support.id}", headers=headers, json={"role": "owner", "reason": "promotion"})
    assert role_change.status_code == 403
    missing_reason = await client.patch(f"/api/v1/platform/operators/{support.id}", headers=headers, json={"is_active": True})
    assert missing_reason.status_code == 422
    reactivate = await client.patch(f"/api/v1/platform/operators/{support.id}", headers=headers, json={"is_active": True, "reason": "restore support"})
    assert reactivate.status_code == 200
    owner_restore = await client.patch(f"/api/v1/platform/operators/{inactive_owner.id}", headers=headers, json={"is_active": True, "reason": "restore owner"})
    assert owner_restore.status_code == 403
    support.is_active = True
    support.token_version += 1
    await db_session.flush()
    stale = await client.get("/api/v1/platform/operators", headers={"Authorization": f"Bearer {create_platform_access_token(support)}"})
    # A support token is authenticated but cannot use the owner-only operator management permission.
    assert stale.status_code == 403
    assert stale.json()["meta"]["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_cli_operator_actions_are_audited_and_reset_mfa_forces_enrollment(client, db_session, sessionmaker, monkeypatch):
    from types import SimpleNamespace
    from app.scripts import create_platform_operator as cli
    monkeypatch.setattr(cli, "AsyncSessionLocal", sessionmaker)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "CliPassw0rd!")
    await cli.run(SimpleNamespace(command="create", email="cli-owner@example.com", name="CLI Owner", role="support"))
    operator = await db_session.scalar(select(PlatformOperator).where(PlatformOperator.email == "cli-owner@example.com"))
    assert operator is not None and operator.mfa_secret is None and operator.mfa_enabled is False
    operator_id = str(operator.id)
    await cli.run(SimpleNamespace(command="change-role", operator_id=operator_id, role="owner"))
    await db_session.refresh(operator)
    assert operator.role == "owner" and operator.token_version == 1
    operator.is_active = False
    operator.mfa_secret = encrypt_mfa_secret(new_totp_secret())
    operator.mfa_enabled = True
    operator.last_totp_step = int(time.time()) // 30
    enrolled_secret = operator.mfa_secret
    old_plaintext_secret = __import__("app.core.platform_security", fromlist=["decrypt_mfa_secret"]).decrypt_mfa_secret(enrolled_secret)
    await db_session.commit()
    await cli.run(SimpleNamespace(command="reactivate-owner", operator_id=operator_id))
    await cli.run(SimpleNamespace(command="reset-mfa", operator_id=operator_id))
    await db_session.refresh(operator)
    assert operator.is_active and not operator.mfa_enabled and operator.mfa_secret is None
    assert operator.last_totp_step is None
    records = (await db_session.scalars(select(PlatformAuditLog).where(PlatformAuditLog.target_id == operator_id).order_by(PlatformAuditLog.created_at))).all()
    assert len(records) == 4
    assert all(row.operator_id is None and row.action.startswith("cli.") for row in records)
    assert [row.action for row in records] == ["cli.operator.created", "cli.operator.role_changed", "cli.operator.owner_reactivated", "cli.operator.mfa_reset"]
    assert all(not ({"password", "password_hash", "mfa_secret", "totp_secret", "token", "challenge_token"} & set(row.details)) for row in records)
    audit_text = " ".join(str({"action": row.action, "reason": row.reason, "details": row.details, "user_agent": row.user_agent}) for row in records)
    assert "CliPassw0rd!" not in audit_text
    assert enrolled_secret not in audit_text
    assert "access_token" not in audit_text and "challenge_token" not in audit_text
    login = await client.post("/api/v1/platform/auth/login", json={"email": "cli-owner@example.com", "password": "CliPassw0rd!"})
    assert login.status_code == 200 and login.json()["data"]["mfa_enrolment_required"] is True
    challenge = login.json()["data"]
    assert challenge["otpauth_uri"]
    new_secret = __import__("urllib.parse", fromlist=["parse_qs", "urlparse"])
    new_secret = new_secret.parse_qs(new_secret.urlparse(challenge["otpauth_uri"]).query)["secret"][0]
    assert new_secret != old_plaintext_secret
    old_code = current_code(old_plaintext_secret)
    rejected_old = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": challenge["challenge_token"], "code": old_code})
    assert rejected_old.status_code == 401
    assert rejected_old.json()["meta"]["error"]["code"] == "MFA_INVALID"
    verified = await client.post("/api/v1/platform/auth/mfa", json={"challenge_token": challenge["challenge_token"], "code": current_code(new_secret)})
    assert verified.status_code == 200
    assert verified.json()["data"]["operator"]["mfa_enabled"] is True
    await db_session.refresh(operator)
    assert operator.last_totp_step is not None


@pytest.mark.asyncio
async def test_platform_token_version_mismatch_is_rejected(client, db_session):
    op = PlatformOperator(email="version@example.com", password_hash=get_password_hash("Passw0rd!"), name="Version", role="owner", mfa_enabled=True, mfa_secret=encrypt_mfa_secret(new_totp_secret()))
    db_session.add(op)
    await db_session.commit()
    stale_token = create_platform_access_token(op)
    op.token_version += 1
    await db_session.commit()
    response = await client.get("/api/v1/platform/operators", headers={"Authorization": f"Bearer {stale_token}"})
    assert response.status_code == 401
    assert response.json()["meta"]["error"]["code"] == "UNAUTHORIZED"
