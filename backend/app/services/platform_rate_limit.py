from __future__ import annotations

import hashlib
import hmac
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
MAX_ACCOUNT_ATTEMPTS = 8
MAX_IP_ATTEMPTS = 80
MAX_MFA_ACCOUNT_ATTEMPTS = 8
MAX_MFA_IP_ATTEMPTS = 80


def _key_hash(scope: str, value: str) -> str:
    material = f"{scope}:{value}".encode("utf-8")
    return hmac.new(settings.PLATFORM_MFA_KEY.encode("ascii"), material, hashlib.sha256).hexdigest()


async def consume_attempts(
    keys: Iterable[tuple[str, str, int]], *, now: datetime | None = None
) -> bool:
    """Atomically consume shared, expiring limits in PostgreSQL/SQLite.

    Key material is HMACed so email addresses and client IPs are not stored in the
    limiter table. The table is pruned on each operation; state is shared by workers.
    """
    current = now or datetime.now(timezone.utc)
    cutoff = current - WINDOW
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    delete(PlatformAuthRateLimit).where(
                        PlatformAuthRateLimit.updated_at < cutoff
                    )
                )
                dialect = session.get_bind().dialect.name
                insert = pg_insert if dialect == "postgresql" else sqlite_insert
                allowed = True
                for scope, value, limit in keys:
                    table = PlatformAuthRateLimit.__table__
                    key_hash = _key_hash(scope, value)
                    expired = table.c.window_started_at <= cutoff
                    statement = insert(table).values(
                        key_hash=key_hash,
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
                    ).returning(table.c.attempt_count)
                    attempts = await session.scalar(statement)
                    if attempts > limit:
                        allowed = False
                return allowed
    except SQLAlchemyError:
        # Do not fall back to per-process counters: that would silently weaken the
        # shared limit. Database unavailability therefore fails authentication closed.
        raise
