from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from app.core.config import settings

# Async engine create karte hain Supabase IPv4 pooler se
# Connection pooling configured for session reuse
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

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
