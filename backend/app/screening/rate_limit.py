"""In-process rate limiter for the public /screener/* routes.

v1 runs one Railway replica, so an in-memory sliding window is enough. With
more replicas each one keeps its own counters (S-L-001): scaling out needs a
shared store.

Two keys per request, both must pass:
- per link token: stops hammering one link;
- per client IP: stops one client walking many tokens.

Limits are set well above real use. A patient doing all three instruments
on one link makes about 50 requests (one per answer, plus loads, consent
and three submits), so a reload loop or flaky network still fits.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status

from app.core.config import settings

WINDOW_SECONDS = 15 * 60
TOKEN_LIMIT = 200
IP_LIMIT = 600
MAX_TRACKED_KEYS = 20_000


@dataclass
class SlidingWindowLimiter:
    limit: int
    window_seconds: float
    max_keys: int = MAX_TRACKED_KEYS
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    def hit(self, key: str, now: float | None = None) -> float:
        """Record one request. Return 0 if allowed, else seconds to wait."""
        now = time.monotonic() if now is None else now
        cutoff = now - self.window_seconds
        bucket = self._hits.get(key)
        if bucket is None:
            if len(self._hits) >= self.max_keys:
                self._prune(cutoff)
            bucket = self._hits[key] = deque()
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return max(0.0, bucket[0] + self.window_seconds - now)
        bucket.append(now)
        return 0.0

    def _prune(self, cutoff: float) -> None:
        stale = [k for k, b in self._hits.items() if not b or b[-1] <= cutoff]
        for key in stale:
            del self._hits[key]
        if len(self._hits) >= self.max_keys:
            # Still full of live keys: drop the half seen least recently so
            # memory stays bounded. Worst case a dropped key gets a fresh
            # window, which only ever errs towards letting a patient in.
            ordered = sorted(self._hits.items(), key=lambda kv: kv[1][-1])
            for key, _ in ordered[: len(ordered) // 2]:
                del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


token_limiter = SlidingWindowLimiter(limit=TOKEN_LIMIT, window_seconds=WINDOW_SECONDS)
ip_limiter = SlidingWindowLimiter(limit=IP_LIMIT, window_seconds=WINDOW_SECONDS)


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
    wait = ip_limiter.hit(f"ip:{screener_client_ip(request)}")
    if wait:
        raise _too_many(wait)
    wait = token_limiter.hit(f"tok:{token_key}")
    if wait:
        raise _too_many(wait)
