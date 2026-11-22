from __future__ import annotations

import secrets
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError
from sqlalchemy import func, select
from app.models.platform import PlatformAuthRateLimit
from app.services import platform_rate_limit
from app.services.platform_rate_limit import consume_attempts

from app.core.config import Settings

BASE_SETTINGS = {
    "_env_file": None,
    "ENVIRONMENT": "test",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "JWT_SECRET_KEY": secrets.token_hex(32),
    "PLATFORM_MFA_KEY": Fernet.generate_key().decode(),
    "SUPABASE_URL": "https://test.invalid",
    "SUPABASE_SECRET_KEY": "test-only",
}


def settings_with(**updates):
    values = {**BASE_SETTINGS, **updates}
    return Settings(**values)


def test_secret_settings_accept_generated_keys():
    jwt_secret = secrets.token_hex(32)
    mfa_key = Fernet.generate_key().decode()
    configured = settings_with(JWT_SECRET_KEY=jwt_secret, PLATFORM_MFA_KEY=mfa_key)
    assert configured.JWT_SECRET_KEY == jwt_secret
    assert configured.PLATFORM_MFA_KEY == mfa_key


def test_jwt_secret_accepts_long_non_hex_production_value():
    secret = "production-jwt-secret-with-compatible-format-123"
    configured = settings_with(ENVIRONMENT="production", JWT_SECRET_KEY=secret)
    assert configured.JWT_SECRET_KEY == secret


def test_jwt_secret_accepts_minimum_length_value():
    secret = "non-hex-jwt-secret-value-1234567"
    assert len(secret) == 32
    assert settings_with(JWT_SECRET_KEY=secret).JWT_SECRET_KEY == secret


def test_missing_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    values = {**BASE_SETTINGS}
    values.pop("JWT_SECRET_KEY")
    with pytest.raises(ValidationError):
        Settings(**values)


def test_missing_platform_mfa_key_is_rejected(monkeypatch):
    monkeypatch.delenv("PLATFORM_MFA_KEY", raising=False)
    values = {**BASE_SETTINGS}
    values.pop("PLATFORM_MFA_KEY")
    with pytest.raises(ValidationError):
        Settings(**values)


def test_jwt_placeholder_and_weak_key_are_rejected_without_echoing_value():
    placeholder = "GENERATE_WITH_openssl_rand_hex_32"
    with pytest.raises(ValidationError) as placeholder_error:
        settings_with(JWT_SECRET_KEY=placeholder)
    assert placeholder not in str(placeholder_error.value)
    with pytest.raises(ValidationError):
        settings_with(JWT_SECRET_KEY="a" * 64)


@pytest.mark.parametrize("secret", [
    "0123456789abcdef" * 3 + "fedcba9876543210",
    "a" * 64,
    "0123456789abcdef" * 4,
    "GENERATE_WITH_openssl_rand_hex_32",
])
def test_predictable_jwt_keys_are_rejected_without_leaking(secret):
    with pytest.raises(ValidationError) as error:
        settings_with(JWT_SECRET_KEY=secret)
    assert secret not in str(error.value)


def test_mfa_placeholder_and_weak_fernet_key_are_rejected():
    with pytest.raises(ValidationError):
        settings_with(PLATFORM_MFA_KEY="GENERATE_WITH_Fernet_generate_key")
    weak_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    with pytest.raises(ValidationError):
        settings_with(PLATFORM_MFA_KEY=weak_key)
    with pytest.raises(ValidationError) as error:
        settings_with(PLATFORM_MFA_KEY="not-a-fernet-key")
    assert "not-a-fernet-key" not in str(error.value)


def test_ci_dummy_keys_are_rejected_in_production():
    for secret in (
        "c1f230d789abce" * 4 + "c1f230d7",
        "ci-only-not-a-secret",
        "test-secret-key-at-least-32-chars-long-123456",
    ):
        with pytest.raises(ValidationError):
            settings_with(ENVIRONMENT="production", JWT_SECRET_KEY=secret)
    with pytest.raises(ValidationError):
        settings_with(
            ENVIRONMENT="production",
            PLATFORM_MFA_KEY="AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=",
        )


def test_cors_rejects_wildcard_with_credentials_enabled():
    with pytest.raises(ValidationError):
        settings_with(CORS_ORIGINS="*")
    assert settings_with(CORS_ORIGINS="https://console.example.test").cors_origins_list == ["https://console.example.test"]


@pytest.mark.asyncio
async def test_shared_rate_limiter_threshold_expiry_and_bounded_unique_keys(
    setup_db, sessionmaker, monkeypatch
):
    monkeypatch.setattr(platform_rate_limit, "AsyncSessionLocal", sessionmaker)
    now = datetime.now(timezone.utc)
    assert await consume_attempts([("test-account", "same", 2)], now=now)
    assert await consume_attempts([("test-account", "same", 2)], now=now + timedelta(seconds=1))
    assert not await consume_attempts([("test-account", "same", 2)], now=now + timedelta(seconds=2))
    assert await consume_attempts([("test-account", "same", 2)], now=now + timedelta(minutes=6))

    async def attempt(index):
        return await consume_attempts([("test-unique", f"key-{index}", 1)], now=now)
    await asyncio.gather(*(attempt(index) for index in range(40)))
    async with sessionmaker() as session:
        count = await session.scalar(select(func.count()).select_from(PlatformAuthRateLimit).where(PlatformAuthRateLimit.updated_at >= now - timedelta(minutes=5)))
    assert count <= 41


@pytest.mark.asyncio
async def test_shared_rate_limiter_concurrent_attempts_are_atomic(
    setup_db, sessionmaker, monkeypatch
):
    monkeypatch.setattr(platform_rate_limit, "AsyncSessionLocal", sessionmaker)
    now = datetime.now(timezone.utc)
    results = await asyncio.gather(*(
        consume_attempts([("test-concurrent", "one", 3)], now=now)
        for _ in range(12)
    ))
    assert sum(results) == 3
