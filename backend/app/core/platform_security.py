from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.models.platform import PlatformOperator


def _fernet() -> Fernet:
    key = settings.PLATFORM_MFA_KEY
    return Fernet(key.encode("ascii"))


def encrypt_mfa_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_mfa_secret(secret: str) -> str:
    try:
        return _fernet().decrypt(secret.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored MFA secret cannot be decrypted") from exc


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def matching_totp_step(secret: str, code: str, now: int | None = None) -> int | None:
    if len(code) != 6 or not code.isdigit():
        return None
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
    tick = (int(time.time()) if now is None else now) // 30
    matches: list[int] = []
    for offset in (-1, 0, 1):
        step = tick + offset
        if step < 0:
            continue
        digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
        index = digest[-1] & 0x0F
        value = (struct.unpack(">I", digest[index:index + 4])[0] & 0x7fffffff) % 1_000_000
        if hmac.compare_digest(f"{value:06d}", code):
            matches.append(step)
    return max(matches) if matches else None


def verify_totp(secret: str, code: str, now: int | None = None) -> bool:
    return matching_totp_step(secret, code, now) is not None


def _login_marker(value: datetime | None) -> int:
    if value is None:
        return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return round(value.timestamp() * 1_000_000)


def create_platform_challenge(operator: PlatformOperator) -> str:
    now = datetime.now(timezone.utc)
    secret_marker = hashlib.sha256((operator.mfa_secret or "").encode()).hexdigest()
    return jwt.encode({"sub": str(operator.id), "aud": "av-platform", "typ": "platform_challenge", "ver": operator.token_version, "ll": _login_marker(operator.last_login_at), "sv": secret_marker, "jti": secrets.token_urlsafe(24), "iat": now, "exp": now + timedelta(minutes=5)}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_platform_challenge(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], audience="av-platform", options={"require": ["sub", "aud", "typ", "ver", "ll", "sv", "jti", "exp"]})


def create_platform_access_token(operator: PlatformOperator) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(operator.id), "aud": "av-platform", "typ": "platform", "ver": operator.token_version, "iat": now, "exp": now + timedelta(minutes=settings.PLATFORM_JWT_EXPIRE_MINUTES)}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
