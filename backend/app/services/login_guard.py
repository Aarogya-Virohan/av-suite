"""Login protection for the CRM sign-in (pipeline report E2, P0).

Two shared counters, kept in the database so they stay correct with several
uvicorn workers or replicas (same table and pattern as the platform login):

- per account (lower-cased email): 8 attempts per 5 minutes
- per client IP: 80 attempts per 5 minutes

Every attempt counts, successful or not, because each one costs a bcrypt
check. Failed password checks also leave an audit row in the clinic's audit
log (email only, never the password).
"""

from __future__ import annotations

import logging
import math
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, Request, status

from app.core.database import AsyncSessionLocal
from app.services.audit import log_event_safely
from app.services.platform_rate_limit import consume_limits

logger = logging.getLogger(__name__)

LOGIN_WINDOW = timedelta(minutes=5)
LOGIN_ACCOUNT_LIMIT = 8
LOGIN_IP_LIMIT = 80


def client_ip(request: Request) -> str:
    """Caller IP. uvicorn --proxy-headers sets request.client from the edge's
    X-Forwarded-For; headers are never read here (same as the platform login)."""
    return request.client.host if request.client and request.client.host else "unknown"


def _too_many(retry_after: float) -> HTTPException:
    seconds = max(1, math.ceil(retry_after))
    minutes = max(1, math.ceil(seconds / 60))
    unit = "minute" if minutes == 1 else "minutes"
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "RATE_LIMITED",
            "message": f"Too many sign-in attempts. Please wait {minutes} {unit} and try again.",
        },
        headers={"Retry-After": str(seconds)},
    )


async def enforce_login_limit(email: str, ip: str) -> None:
    """Count this attempt; raise 429 with a clear message when over the limit."""
    result = await consume_limits(
        [
            ("crm-login-account", email.strip().lower(), LOGIN_ACCOUNT_LIMIT, LOGIN_WINDOW),
            ("crm-login-ip", ip, LOGIN_IP_LIMIT, LOGIN_WINDOW),
        ]
    )
    if not result.allowed:
        raise _too_many(result.retry_after)


async def record_failed_login(user_id: UUID, email: str, clinic_ids: list[UUID]) -> None:
    """Audit a wrong password for an existing account, in its own session.

    The request session is rolled back when login answers 401, so a row added
    there would be lost. Unknown emails belong to no clinic and get no row (the
    limiter above already bounds them). Details hold the email only.
    """
    try:
        async with AsyncSessionLocal() as session:
            for clinic_id in clinic_ids[:5]:
                await log_event_safely(
                    session, clinic_id, user_id, "login_failed", "user", user_id,
                    {"email": email.strip().lower(), "reason": "bad_password"},
                )
    except Exception as exc:  # never let auditing change the login answer
        logger.warning("Could not audit failed login: %s", exc)
