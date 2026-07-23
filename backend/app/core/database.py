from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from app.core.config import settings

# Async engine create karte hain Supabase IPv4 pooler se
# Connection pooling configured for session reuse
# SQLite (used in tests) does not support pool_size/max_overflow (NullPool),
# so those args are only passed for real (Postgres) databases.
_engine_kwargs = {"echo": settings.DEBUG, "pool_pre_ping": True}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# SQLAlchemy 1.4.x compatible session factory
# AsyncSession ke saath work karta hai async operations ke liye
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Har request ke liye naya session create hota hai
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
