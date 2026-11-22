from __future__ import annotations

import secrets
import hashlib
from datetime import datetime, timezone
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import SessionDep
from app.core.platform_security import (
    create_platform_access_token, create_platform_challenge, decode_platform_challenge, _login_marker,
    decrypt_mfa_secret, encrypt_mfa_secret, new_totp_secret, matching_totp_step,
)
from app.core.platform_rbac import require_platform_permission
from app.core.security import get_password_hash, verify_password
from app.exceptions import BaseAppException
from app.models.platform import PlatformOperator
from app.schemas.envelope import ResponseEnvelope
from app.services.platform_audit import record_platform_audit
from app.services.platform_operator_lifecycle import lock_operator_lifecycle, ensure_another_active_owner_remains
from app.services.platform_rate_limit import (
    consume_attempts, MAX_ACCOUNT_ATTEMPTS, MAX_IP_ATTEMPTS,
    MAX_MFA_ACCOUNT_ATTEMPTS, MAX_MFA_IP_ATTEMPTS,
)

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class MFARequest(BaseModel):
    challenge_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

class OperatorPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    reason: str | None = None

def _unauthorized():
    return BaseAppException("Invalid email or password", "UNAUTHORIZED", 401)

def _operator_view(operator: PlatformOperator):
    return {"id": str(operator.id), "email": operator.email, "name": operator.name,
            "role": operator.role, "is_active": operator.is_active,
            "mfa_enabled": operator.mfa_enabled,
            "last_login_at": operator.last_login_at.isoformat() if operator.last_login_at else None,
            "created_at": operator.created_at.isoformat() if operator.created_at else None,
            "updated_at": operator.updated_at.isoformat() if operator.updated_at else None}

@router.post("/auth/login", response_model=ResponseEnvelope[dict])
async def login(body: LoginRequest, request: Request, db: SessionDep):
    email = body.email.lower()
    if not await consume_attempts([
        ("login-account", email, MAX_ACCOUNT_ATTEMPTS),
        ("login-ip", request.client.host if request.client else "unknown", MAX_IP_ATTEMPTS),
    ]):
        raise BaseAppException("Too many authentication attempts", "RATE_LIMITED", 429)
    operator = await db.scalar(select(PlatformOperator).where(func.lower(PlatformOperator.email) == email))
    # Verify against a fixed dummy hash on unknown emails to reduce timing differences.
    if operator is None:
        verify_password(body.password, "$2b$12$C6UzMDM.H6dfI/f/IKcEe.3F7fHR6hW3J7kO1Kzt3l2R8uXJkmz3e")
        raise _unauthorized()
    if not operator.is_active or not verify_password(body.password, operator.password_hash):
        raise _unauthorized()

    enrollment_required = not operator.mfa_enabled
    if enrollment_required:
        secret = new_totp_secret()
        operator.mfa_secret = encrypt_mfa_secret(secret)
        operator.last_totp_step = None
        await db.flush()
        # The plaintext secret is returned only in the enrollment URI over the authenticated
        # password-verified challenge flow; it is never persisted or audited in plaintext.
        import urllib.parse
        uri = "otpauth://totp/AV%20Platform:" + urllib.parse.quote(operator.email) + "?" + urllib.parse.urlencode({"secret": secret, "issuer": "AV Platform", "algorithm": "SHA1", "digits": 6, "period": 30})
        record_platform_audit(db, action="auth.mfa_enrollment_started", target_type="operator", target_id=operator.id, ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    else:
        uri = None
    return {"data": {"challenge_token": create_platform_challenge(operator), "mfa_enrolment_required": enrollment_required, "otpauth_uri": uri}, "meta": {}}

@router.post("/auth/mfa", response_model=ResponseEnvelope[dict])
async def complete_mfa(body: MFARequest, request: Request, db: SessionDep):
    client_ip = request.client.host if request.client else "unknown"
    try:
        claims = decode_platform_challenge(body.challenge_token)
        operator_id = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
        if not await consume_attempts([("mfa-ip", client_ip, MAX_MFA_IP_ATTEMPTS)]):
            raise BaseAppException("Too many authentication attempts", "RATE_LIMITED", 429) from exc
        raise BaseAppException("Invalid or expired challenge", "UNAUTHORIZED", 401) from exc
    if not await consume_attempts([
        ("mfa-ip", client_ip, MAX_MFA_IP_ATTEMPTS),
        ("mfa-account", str(operator_id), MAX_MFA_ACCOUNT_ATTEMPTS),
    ]):
        raise BaseAppException("Too many authentication attempts", "RATE_LIMITED", 429)
    # Locking plus a version compare makes each challenge single-use, including concurrent submits.
    operator = await db.scalar(select(PlatformOperator).where(PlatformOperator.id == operator_id).with_for_update())
    if operator is None or not operator.is_active or claims["ver"] != operator.token_version or not operator.mfa_secret:
        raise BaseAppException("Invalid or expired challenge", "UNAUTHORIZED", 401)
    current_secret_marker = hashlib.sha256(operator.mfa_secret.encode()).hexdigest()
    if claims["ll"] != _login_marker(operator.last_login_at) or not secrets.compare_digest(claims["sv"], current_secret_marker):
        raise BaseAppException("Invalid or expired challenge", "UNAUTHORIZED", 401)
    try:
        secret = decrypt_mfa_secret(operator.mfa_secret)
    except ValueError as exc:
        raise BaseAppException("MFA configuration error", "UNAUTHORIZED", 401) from exc
    accepted_step = matching_totp_step(secret, body.code)
    if accepted_step is None or (
        operator.last_totp_step is not None and accepted_step <= operator.last_totp_step
    ):
        raise BaseAppException("Invalid verification code", "MFA_INVALID", 401)

    operator.mfa_enabled = True
    operator.last_totp_step = accepted_step
    # Updating this marker atomically consumes this and any concurrent login challenges,
    # without revoking already-issued access tokens.
    operator.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(operator)
    token = create_platform_access_token(operator)
    record_platform_audit(db, operator_id=operator.id, action="auth.mfa_verified", target_type="operator", target_id=operator.id, ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    return {"data": {"access_token": token, "token_type": "bearer", "expires_in": settings.PLATFORM_JWT_EXPIRE_MINUTES * 60, "operator": _operator_view(operator)}, "meta": {}}

@router.get("/operators")
async def list_operators(
    db: SessionDep,
    operator: PlatformOperator = Depends(require_platform_permission("platform.operators.manage")),
):
    # This endpoint exists only for S2 lifecycle safety tests; S3 owns the full list contract.
    rows = (await db.scalars(select(PlatformOperator).order_by(PlatformOperator.created_at))).all()
    return {"data": [_operator_view(row) for row in rows], "meta": {}}

@router.patch("/operators/{operator_id}")
async def update_operator(
    operator_id: UUID,
    body: OperatorPatch,
    request: Request,
    db: SessionDep,
    actor: PlatformOperator = Depends(require_platform_permission("platform.operators.manage")),
):
    if body.role is not None:
        raise BaseAppException("Role changes via CLI only", "FORBIDDEN", 403)
    if body.is_active is None:
        raise BaseAppException("No supported operator change supplied", "VALIDATION_ERROR", 422)
    if not body.reason or not body.reason.strip():
        raise BaseAppException("Reason is required", "VALIDATION_ERROR", 422)
    await lock_operator_lifecycle(db)
    expected_token_version = request.state.platform_operator_token_version
    actor = await db.scalar(
        select(PlatformOperator).where(PlatformOperator.id == actor.id).with_for_update()
        .execution_options(populate_existing=True)
    )
    if actor is None or not actor.is_active or actor.token_version != expected_token_version:
        raise BaseAppException("Unauthorized", "UNAUTHORIZED", 401)
    if actor.role != "owner":
        raise BaseAppException("Forbidden", "FORBIDDEN", 403)
    target = await db.scalar(select(PlatformOperator).where(PlatformOperator.id == operator_id).with_for_update())
    if target is None:
        raise BaseAppException("Operator not found", "NOT_FOUND", 404)
    if target.is_active and not body.is_active and target.role == "owner":
        owners = (await db.scalars(select(PlatformOperator).where(PlatformOperator.role == "owner", PlatformOperator.is_active.is_(True)).order_by(PlatformOperator.id).with_for_update())).all()
        ensure_another_active_owner_remains(len(owners))
    if actor.id == target.id and body.is_active is False:
        raise BaseAppException("Operators cannot deactivate themselves", "VALIDATION_ERROR", 422)
    if target.role == "owner" and body.is_active is True:
        raise BaseAppException("Owner reactivation via CLI only", "FORBIDDEN", 403)
    before = {"is_active": target.is_active, "role": target.role}
    target.is_active = body.is_active
    if before["is_active"] != target.is_active:
        target.token_version += 1
    await db.flush()
    await db.refresh(target)
    record_platform_audit(db, operator_id=actor.id, action="operator.deactivated" if not body.is_active else "operator.reactivated", target_type="operator", target_id=target.id, reason=body.reason.strip(), ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"), details={"before": before, "after": {"is_active": target.is_active, "role": target.role}})
    return {"data": _operator_view(target), "meta": {}}
