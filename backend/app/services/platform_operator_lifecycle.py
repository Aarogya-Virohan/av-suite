from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.exceptions.base import BaseAppException

# A transaction-scoped PostgreSQL advisory lock serializes operator lifecycle writes.
# It is acquired before any operator row lock, so competing API and CLI changes use
# one lock order while locking overlapping operator sets.
_OPERATOR_LIFECYCLE_LOCK = 0x41565332504C4154


async def lock_operator_lifecycle(session: AsyncSession) -> None:
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _OPERATOR_LIFECYCLE_LOCK},
        )


def ensure_another_active_owner_remains(
    active_owner_count: int, *, action: str = "deactivate"
) -> None:
    """Enforce the active-Owner invariant after lifecycle and row locks are held."""
    if active_owner_count <= 1:
        message = f"Cannot {action} the last active Owner"
        raise BaseAppException(message, "CONFLICT", 409)
