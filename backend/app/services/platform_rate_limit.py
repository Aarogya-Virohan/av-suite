from __future__ import annotations

import hashlib
import hmac
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.platform import PlatformAuthRateLimit

WINDOW = timedelta(minutes=5)
# Longest window any caller uses (public screener, 15 min). Rows are only
# deleted once they are older than this; a row's own window is decided by
# window_started_at, so shorter windows still expire on time.
PRUNE_AFTER = timedelta(minutes=15)
PRUNE_CHANCE = 0.05
MAX_ACCOUNT_ATTEMPTS = 8
MAX_IP_ATTEMPTS = 80
MAX_MFA_ACCOUNT_ATTEMPTS = 8
MAX_MFA_IP_ATTEMPTS = 80


def _key_hash(scope: str, value: str) -> str:
    material = f"{scope}:{value}".encode("utf-8")
    return hmac.new(settings.PLATFORM_MFA_KEY.encode("ascii"), material, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class LimitResult:
    allowed: bool
    retry_after: float = 0.0  # seconds until the blocking window ends (0 when allowed)


async def consume_limits(
    keys: Iterable[tuple[str, str, int, timedelta]], *, now: datetime | None = None
) -> LimitResult:
    """Atomically count one attempt per key in the shared limiter table.

    Each key is (scope, value, limit, window). The count lives in the database
    (one atomic upsert per key), so every worker and every replica sees the same
    number. This is what keeps a limit correct with `uvicorn --workers 2`: no
    counter is kept in process memory. Key material is HMACed so email
    addresses and client IPs are not stored. A window starts at the first
    attempt and ends `window` later (fixed window, so right at a boundary a
    client can get up to twice the limit across two windows).
    """
    current = now or datetime.now(timezone.utc)
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                if random.random() < PRUNE_CHANCE:
                    await session.execute(
                        delete(PlatformAuthRateLimit).where(
                            PlatformAuthRateLimit.updated_at < current - PRUNE_AFTER
                        )
                    )
                dialect = session.get_bind().dialect.name
                insert = pg_insert if dialect == "postgresql" else sqlite_insert
                table = PlatformAuthRateLimit.__table__
                allowed = True
                retry_after = 0.0
                for scope, value, limit, window in keys:
                    cutoff = current - window
                    expired = table.c.window_started_at <= cutoff
                    statement = insert(table).values(
                        key_hash=_key_hash(scope, value),
                        window_started_at=current,
                        attempt_count=1,
                        updated_at=current,
                    ).on_conflict_do_update(
                        index_elements=[table.c.key_hash],
                        set_={
                            "window_started_at": case(
                                (expired, current), else_=table.c.window_started_at
                            ),
                            "attempt_count": case(
                                (expired, 1), else_=table.c.attempt_count + 1
                            ),
                            "updated_at": current,
                        },
                    ).returning(table.c.attempt_count, table.c.window_started_at)
                    attempts, started = (await session.execute(statement)).one()
                    if attempts > limit:
                        allowed = False
                        if started.tzinfo is None:
                            started = started.replace(tzinfo=timezone.utc)
                        retry_after = max(
                            retry_after, (started + window - current).total_seconds()
                        )
                return LimitResult(allowed, retry_after if not allowed else 0.0)
    except SQLAlchemyError:
        # Do not fall back to per-process counters: that would silently weaken the
        # shared limit. Database unavailability therefore fails authentication closed.
        raise


async def consume_attempts(
    keys: Iterable[tuple[str, str, int]], *, now: datetime | None = None
) -> bool:
    """Platform login / MFA limiter (5 min window). Returns True when allowed."""
    result = await consume_limits(
        [(scope, value, limit, WINDOW) for scope, value, limit in keys], now=now
    )
    return result.allowed


async def clear_all_limits() -> None:
    """Delete every counter. For tests and for a manual reset by an operator."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(PlatformAuthRateLimit))
