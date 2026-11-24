"""Rate limiter for the public /screener/* routes.

The counters live in the database (shared limiter table, same as the CRM and
platform logins), not in process memory. With `uvicorn --workers 2`, or a
second replica, every worker sees the same count, so the limit does not double
and a redeploy does not reset it (S-L-001, pipeline report section C).

Two keys per request, both must pass:
- per link token: stops hammering one link;
- per client IP: stops one client walking many tokens.

Fixed 15 minute windows: a window starts at the first request of a key. Right
at a boundary a client can get up to twice the limit across two windows.

Limits are set well above real use. A patient doing all three instruments
on one link makes about 50 requests (one per answer, plus loads, consent
and three submits), so a reload loop or flaky network still fits.
"""

from __future__ import annotations

import hashlib
import math
from datetime import timedelta

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.services.platform_rate_limit import consume_limits

WINDOW_SECONDS = 15 * 60
TOKEN_LIMIT = 200
IP_LIMIT = 600


def screener_client_ip(request: Request) -> str:
    """Client IP for rate limiting.

    The shared get_client_ip() in core/dependencies.py trusts
    CF-Connecting-IP and the leftmost X-Forwarded-For entry from any caller,
    so it is not used here. Only a header named in SCREENER_CLIENT_IP_HEADER
    is read, and only because the deployment says the edge overwrites it.
    Otherwise request.client.host is used: uvicorn sets it from
    X-Forwarded-For (Dockerfile: --proxy-headers), and Railway's edge
    replaces any client-sent X-Forwarded-For.
    """
    header = settings.SCREENER_CLIENT_IP_HEADER
    if header:
        value = request.headers.get(header, "").split(",")[0].strip()
        if value:
            return value
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _too_many(retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "RATE_LIMITED",
            "message": "Too many requests. Please wait a few minutes and try again.",
        },
        headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
    )


async def enforce_screener_rate_limit(request: Request, token: str) -> None:
    """FastAPI dependency for every /screener/{token}... route."""
    token_key = hashlib.sha256(token.encode()).hexdigest()
    window = timedelta(seconds=WINDOW_SECONDS)
    result = await consume_limits(
        [
            ("screener-ip", screener_client_ip(request), IP_LIMIT, window),
            ("screener-token", token_key, TOKEN_LIMIT, window),
        ]
    )
    if not result.allowed:
        raise _too_many(result.retry_after)
