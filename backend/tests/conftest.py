import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool, StaticPool
import asyncio
from typing import AsyncGenerator
import os
import uuid
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from app.models.product import (
    Product,
    PlatformBundle,
    PlatformBundleProduct,
    WorkspaceProduct,
)

if "DATABASE_URL" not in os.environ:
    if "TEST_DATABASE_URL" in os.environ:
        os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
    elif not os.path.isfile(".env"):
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-chars-long-123456")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CLINIC_DOCUMENTS_BUCKET", "test-bucket")

from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.user import User
from app.enums.user import UserRole
from app.core.security import create_access_token
from app.services.product_entitlements import ensure_crm_entitlement

TEST_DATABASE_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL


def assert_safe_test_database_url(database_url: str) -> None:
    """Refuse test database URLs that could target a non-local database."""
    try:
        url = make_url(database_url)
    except (ArgumentError, TypeError, ValueError) as exc:
        raise ValueError(
            "Unsafe test database URL: could not parse database URL."
        ) from exc

    if url.get_backend_name() == "sqlite" and url.host is None:
        return
    if url.host and url.host.lower().rstrip(".") in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        return

    host = url.host or "<unspecified>"
    raise ValueError(
        "Unsafe test database URL: destructive test setup is restricted to "
        "local SQLite or PostgreSQL on localhost/127.0.0.1; "
        f"refusing database host {host!r}."
    )


@pytest.fixture
def test_database_url_safety_check():
    return assert_safe_test_database_url


@pytest.fixture(scope="session")
def engine():
    assert_safe_test_database_url(TEST_DATABASE_URL)
    url = make_url(TEST_DATABASE_URL)
    if url.get_backend_name() == "sqlite" and url.database == ":memory:":
        poolclass = StaticPool
    else:
        poolclass = NullPool
    debug_file = f"/tmp/engine_debug_{os.getpid()}.txt"
    with open(debug_file, "a") as f:
        f.write(f"DEBUG: engine: TEST_DATABASE_URL={TEST_DATABASE_URL!r}\n")
        f.write(f"DEBUG: engine: url.get_backend_name()={url.get_backend_name()!r}\n")
        f.write(f"DEBUG: engine: url.database={url.database!r}\n")
        f.write(
            f"DEBUG: engine: url.get_backend_name() == 'sqlite': {url.get_backend_name() == 'sqlite'!r}\n"
        )
        f.write(
            f"DEBUG: engine: url.database == ':memory:': {url.database == ':memory:'!r}\n"
        )
        f.write(
            f"DEBUG: engine: condition={url.get_backend_name() == 'sqlite' and url.database == ':memory:'!r}\n"
        )
        f.write(f"DEBUG: engine: poolclass variable={poolclass}\n")
    engine_obj = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=poolclass)
    with open(debug_file, "a") as f:
        f.write(f"DEBUG: engine: poolclass={engine_obj.pool.__class__.__name__}\n")
        f.write(f"DEBUG: engine: engine id={id(engine_obj)}\n")
    return engine_obj


@pytest.fixture(scope="session")
def sessionmaker(engine):
    return async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


@pytest.fixture(scope="session")
async def setup_db(engine, sessionmaker):
    assert_safe_test_database_url(TEST_DATABASE_URL)
    with open("/tmp/setup_db_debug.txt", "a") as f:
        f.write(f"DEBUG: setup_db: called\n")
        f.write(f"DEBUG: setup_db: engine poolclass={engine.pool.__class__.__name__}\n")
        f.write(f"DEBUG: setup_db: engine id={id(engine)}\n")
    async with engine.begin() as conn:
        with open("/tmp/setup_db_debug.txt", "a") as f:
            f.write(f"DEBUG: setup_db: dropping all tables\n")
        await conn.run_sync(Base.metadata.drop_all)
        with open("/tmp/setup_db_debug.txt", "a") as f:
            f.write(f"DEBUG: setup_db: creating all tables\n")
        await conn.run_sync(Base.metadata.create_all)
        with open("/tmp/setup_db_debug.txt", "a") as f:
            f.write(f"DEBUG: setup_db: tables created\n")

    # Seed initial test clinic and users for test suite
    async with sessionmaker() as session:
        clinic_id = uuid.uuid4()
        clinic = Clinic(
            id=clinic_id,
            name="Aarogya Seeded Test Clinic",
            branding_color="#008080",
            plan_tier="clinical_pro",
            is_partner_clinic=True,
        )
        session.add(clinic)

        password_hash = get_password_hash("Password123!")

        admin_user = User(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            email="admin@avtest.com",
            password_hash=password_hash,
            role=UserRole.ADMIN,
            first_name="Admin",
            last_name="User",
            phone="9876543211",
            is_active=True,
        )

        frontdesk_user = User(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            email="frontdesk@avtest.com",
            password_hash=password_hash,
            role=UserRole.FRONT_DESK,
            first_name="Front",
            last_name="Desk",
            phone="9876543212",
            is_active=True,
        )

        therapist_user = User(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            email="therapist@avtest.com",
            password_hash=password_hash,
            role=UserRole.THERAPIST,
            first_name="Main",
            last_name="Therapist",
            phone="9876543213",
            is_active=True,
        )

        memberships = [
            Membership(user_id=admin_user.id, clinic_id=clinic_id, role=UserRole.ADMIN),
            Membership(
                user_id=frontdesk_user.id, clinic_id=clinic_id, role=UserRole.FRONT_DESK
            ),
            Membership(
                user_id=therapist_user.id, clinic_id=clinic_id, role=UserRole.THERAPIST
            ),
        ]

        session.add_all([admin_user, frontdesk_user, therapist_user, *memberships])
        await ensure_crm_entitlement(session, clinic_id)
        await session.commit()

    yield

    assert_safe_test_database_url(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(sessionmaker, setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker() as session:
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


@pytest.fixture
async def auth_headers(client: AsyncClient):
    login_res = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": "admin@avtest.com", "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
async def therapist_auth_headers(client: AsyncClient):
    login_res = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": "therapist@avtest.com", "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
async def frontdesk_auth_headers(client: AsyncClient):
    login_res = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": "frontdesk@avtest.com", "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
