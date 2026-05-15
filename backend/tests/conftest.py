import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import asyncio
from typing import AsyncGenerator

from app.main import app
from app.core.database import get_db
from app.models.base import Base

# Use an in-memory SQLite database for testing, but since the app uses Postgres UUID, 
# it's best if we point to a test postgres DB or just configure the engine.
# We'll assume TEST_DATABASE_URL is provided, fallback to standard sqlite for simplicity.
# NOTE: async sqlite requires aiosqlite, if not installed, this will fail. We'll rely on the real DB for now if needed.
# For demonstration in this test, we assume the environment has a valid DB for testing.
from app.core.config import settings

# Since asyncpg is the only driver, we must use a postgres URL.
TEST_DATABASE_URL = settings.DATABASE_URL + "_test" if not settings.DATABASE_URL.endswith("_test") else settings.DATABASE_URL

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    
    app.dependency_overrides.clear()
