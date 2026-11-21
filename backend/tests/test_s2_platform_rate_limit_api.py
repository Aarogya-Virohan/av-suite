from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import get_password_hash
from app.api.v1 import platform_auth
from app.main import app
from app.models.platform import PlatformAuthRateLimit, PlatformOperator
from app.services import platform_rate_limit


pytestmark = pytest.mark.asyncio

LOGIN_URL = "/api/v1/platform/auth/login"
MFA_URL = "/api/v1/platform/auth/mfa"


def unique_ip() -> str:
    suffix = uuid.uuid4().int
    return f"198.18.{(suffix >> 8) & 255}.{suffix & 255}"


async def post_login(
    peer_ip: str,
    email: str,
    *,
    forwarded_ip: str | None = None,
) -> tuple[int, dict]:
    headers = {"X-Forwarded-For": forwarded_ip} if forwarded_ip else None
    transport = ASGITransport(app=app, client=(peer_ip, 54321))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            LOGIN_URL,
            headers=headers,
            json={"email": email, "password": "RateLimitPass123!"},
        )
    return response.status_code, response.json()


async def post_mfa(peer_ip: str, forwarded_ip: str) -> tuple[int, dict]:
    transport = ASGITransport(app=app, client=(peer_ip, 54321))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            MFA_URL,
            headers={"X-Forwarded-For": forwarded_ip},
            json={"challenge_token": "invalid-challenge", "code": "123456"},
        )
    return response.status_code, response.json()


async def create_operator(db_session, email: str) -> PlatformOperator:
    operator = PlatformOperator(
        email=email,
        password_hash=get_password_hash("RateLimitPass123!"),
        name="Rate Limit Test",
        role="support",
    )
    db_session.add(operator)
    await db_session.commit()
    return operator


def assert_rate_limited(response: tuple[int, dict]) -> None:
    status_code, body = response
    assert status_code == 429
    assert body["data"] is None
    assert body["meta"]["error"]["code"] == "RATE_LIMITED"
    assert body["meta"]["error"]["message"] == "Too many authentication attempts"


async def test_login_limit_and_persistence_across_independent_session_factories(
    client: AsyncClient, db_session, monkeypatch
):
    email = f"rate-limit-shared-{uuid.uuid4()}@example.com"
    await create_operator(db_session, email)
    monkeypatch.setattr(platform_auth, "MAX_ACCOUNT_ATTEMPTS", 2)
    monkeypatch.setattr(platform_auth, "MAX_IP_ATTEMPTS", 100)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8")
    proxy_peer = "10.0.0.1"
    client_ip = unique_ip()

    first = await post_login(proxy_peer, email, forwarded_ip=client_ip)
    assert first[0] == 200
    assert first[1]["data"]["challenge_token"]

    # A separate engine/sessionmaker represents another API worker sharing the DB.
    independent_engine = create_async_engine(settings.DATABASE_URL)
    independent_sessions = async_sessionmaker(
        independent_engine, expire_on_commit=False, autoflush=False
    )
    try:
        monkeypatch.setattr(
            platform_rate_limit, "AsyncSessionLocal", independent_sessions
        )
        second = await post_login(proxy_peer, email, forwarded_ip=client_ip)
        third = await post_login(proxy_peer, email, forwarded_ip=client_ip)
        assert second[0] == 200
        assert_rate_limited(third)

        async with independent_sessions() as session:
            key_hash = platform_rate_limit._key_hash("login-account", email)
            row = await session.scalar(
                select(PlatformAuthRateLimit).where(
                    PlatformAuthRateLimit.key_hash == key_hash
                )
            )
            assert row is not None and row.attempt_count == 3
    finally:
        await independent_engine.dispose()


async def test_login_account_identifiers_are_isolated(
    client: AsyncClient, db_session, monkeypatch
):
    email_a = f"rate-limit-account-a-{uuid.uuid4()}@example.com"
    email_b = f"rate-limit-account-b-{uuid.uuid4()}@example.com"
    await create_operator(db_session, email_a)
    await create_operator(db_session, email_b)
    monkeypatch.setattr(platform_auth, "MAX_ACCOUNT_ATTEMPTS", 1)
    monkeypatch.setattr(platform_auth, "MAX_IP_ATTEMPTS", 100)
    peer_a, peer_b = unique_ip(), unique_ip()

    assert (await post_login(peer_a, email_a))[0] == 200
    assert_rate_limited(await post_login(peer_b, email_a))
    # A different account at that same peer has an independent account counter.
    assert (await post_login(peer_b, email_b))[0] == 200


async def test_mfa_ip_limit_uses_resolved_client_ip_and_isolates_clients(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(platform_auth, "MAX_MFA_IP_ATTEMPTS", 1)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8")
    client_ip_a, client_ip_b = unique_ip(), unique_ip()

    first = await post_mfa("10.0.0.8", client_ip_a)
    same_client = await post_mfa("10.0.0.8", client_ip_a)
    other_client = await post_mfa("10.0.0.8", client_ip_b)
    assert first[0] == 401
    assert first[1]["meta"]["error"]["code"] == "UNAUTHORIZED"
    assert_rate_limited(same_client)
    assert other_client[0] == 401
    assert other_client[1]["meta"]["error"]["code"] == "UNAUTHORIZED"

    untrusted_peer = unique_ip()
    first_untrusted = await post_mfa(untrusted_peer, unique_ip())
    second_untrusted = await post_mfa(untrusted_peer, unique_ip())
    assert first_untrusted[0] == 401
    assert_rate_limited(second_untrusted)


async def test_login_counter_expires_and_resets(
    client: AsyncClient, db_session, monkeypatch
):
    email = f"rate-limit-expiry-{uuid.uuid4()}@example.com"
    await create_operator(db_session, email)
    monkeypatch.setattr(platform_auth, "MAX_ACCOUNT_ATTEMPTS", 1)
    monkeypatch.setattr(platform_auth, "MAX_IP_ATTEMPTS", 100)
    client_ip = unique_ip()

    assert (await post_login(client_ip, email))[0] == 200
    key_hash = platform_rate_limit._key_hash("login-account", email)
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=6)
    async with platform_rate_limit.AsyncSessionLocal() as session:
        await session.execute(
            update(PlatformAuthRateLimit)
            .where(PlatformAuthRateLimit.key_hash == key_hash)
            .values(window_started_at=expired_at, updated_at=expired_at)
        )
        await session.commit()

    reset = await post_login(client_ip, email)
    assert reset[0] == 200
    assert (await post_login(client_ip, email))[0] == 429
