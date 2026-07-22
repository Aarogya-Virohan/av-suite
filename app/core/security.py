from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TypedDict, cast
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext  # pyright: ignore[reportMissingTypeStubs] - passlib does not ship usable stubs here.

from app.core.config import settings
from app.enums.user import UserRole, normalize_user_role


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenClaims(TypedDict):
    """JWT claims used by the CRM authentication layer."""

    sub: str
    user_id: str
    clinic_id: str
    role: str
    exp: int


def get_password_hash(password: str) -> str:
    """Return a bcrypt password hash for the provided password."""

    return pwd_context.hash(password)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType] - passlib types are unavailable.


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check whether a plain password matches a stored bcrypt hash."""

    verification_result = cast(
        bool,
        pwd_context.verify(plain_password, hashed_password),  # pyright: ignore[reportUnknownMemberType] - passlib types are unavailable.
    )
    return verification_result


def create_access_token(
    *,
    user_id: UUID | str | None = None,
    subject: UUID | str | None = None,
    clinic_id: UUID | str,
    role: UserRole | str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed access token containing the CRM identity claims."""

    token_user_id = user_id or subject
    if token_user_id is None:
        raise ValueError("user_id or subject is required")

    canonical_role = normalize_user_role(role)
    issued_at = datetime.now(UTC)
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: dict[str, str | int] = {
        "sub": str(token_user_id),
        "user_id": str(token_user_id),
        "clinic_id": str(clinic_id),
        "role": canonical_role.value,
        "iat": int(issued_at.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> TokenClaims:
    """Decode and validate a CRM access token."""

    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:  # pragma: no cover - library raises many token-specific subclasses
        raise ValueError("Invalid access token") from exc

    user_identifier = decoded_token.get("user_id") or decoded_token.get("sub")
    clinic_id = decoded_token.get("clinic_id")
    role = decoded_token.get("role")
    exp = decoded_token.get("exp")

    if not isinstance(user_identifier, str) or not isinstance(clinic_id, str) or not isinstance(role, str) or not isinstance(exp, int):
        raise ValueError("Invalid access token payload")

    try:
        canonical_role = normalize_user_role(role)
    except ValueError as exc:
        raise ValueError("Invalid access token payload") from exc

    return {
        "sub": user_identifier,
        "user_id": user_identifier,
        "clinic_id": clinic_id,
        "role": canonical_role.value,
        "exp": exp,
    }
