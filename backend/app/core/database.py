from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from fastapi import Request
from app.core.config import settings

# Async engine create karte hain Supabase IPv4 pooler se
# Connection pooling configured for session reuse
# SQLite (used in tests) does not support pool_size/max_overflow (NullPool),
# so those args are only passed for real (Postgres) databases.
_engine_kwargs: dict[str, object] = {"echo": settings.DEBUG, "pool_pre_ping": True}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    # A request that cannot get a connection in this time fails fast with a
    # 503 (see app.main) instead of hanging for 30 s and ending in a 500.
    _engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    # Supabase's pooler drops idle connections; recycle before that.
    _engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# SQLAlchemy 2.0 async session factory
# async_sessionmaker provides proper typing for async context manager usage
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db(request: Request = None) -> AsyncGenerator[AsyncSession, None]:  # type: ignore[assignment]
    # Har request ke liye naya session create hota hai
    # Transaction boundary: successful request commits, exception rolls back
    async with AsyncSessionLocal() as session:
        # CommitBeforeResponseMiddleware commits this session right before the
        # response starts, so a client never sees a 2xx for a write that is not
        # in the database yet. FastAPI only runs the code after `yield` once the
        # response has been sent.
        if request is not None:
            request.scope.setdefault("state", {})["db_session"] = session
        try:
            yield session
            # Safe even if the middleware or the service already committed
            # (nothing left to flush: no-op).
            await session.commit()
        except Exception:
            # Rollback on any exception
            await session.rollback()
            raise
        finally:
            await session.close()
