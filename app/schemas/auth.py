from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.enums.user import UserRole


class LoginRequest(BaseModel):
    """Credentials required to issue a CRM access token."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Bearer token response compatible with AV Suite clients."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload exposed to internal callers."""

    user_id: UUID
    clinic_id: UUID
    role: UserRole
