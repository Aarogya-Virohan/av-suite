import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import asyncio
from typing import AsyncGenerator
import os
import uuid

from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.clinic import Clinic
from app.models.user import User
from app.enums.user import UserRole
from app.core.security import create_access_token

TEST_DATABASE_URL = settings.TEST_DATABASE_URL or settings.DATABASE_URL

@pytest.fixture(scope="session")
def engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

@pytest.fixture(scope="session")
def sessionmaker(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)

@pytest.fixture(scope="session")
async def setup_db(engine, sessionmaker):
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(sync_conn, checkfirst=True))
        if engine.dialect.name == "postgresql":
            from sqlalchemy import text
            for enum_name in ["clinicplantier", "patientstatus", "payment_status", "gender_type", "specialty_type", "lead_source_type", "appointment_request_status", "lead_stage"]:
                await conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE;"))
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial test clinic and users for test suite
    async with sessionmaker() as session:
        clinic_id = uuid.uuid4()
        clinic = Clinic(
            id=clinic_id,
            name="Aarogya Seeded Test Clinic",
            branding_color="#008080",
            plan_tier="clinical_pro",
            is_partner_clinic=True
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
            is_active=True
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
            is_active=True
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
            is_active=True
        )

        session.add_all([admin_user, frontdesk_user, therapist_user])
        await session.commit()

    yield

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
    login_res = await client.post(f"{settings.API_V1_PREFIX}/auth/login", json={
        "email": "admin@avtest.com",
        "password": "Password123!"
    })
    token = login_res.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

@pytest.fixture
async def therapist_auth_headers(client: AsyncClient):
    login_res = await client.post(f"{settings.API_V1_PREFIX}/auth/login", json={
        "email": "therapist@avtest.com",
        "password": "Password123!"
    })
    token = login_res.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

@pytest.fixture
async def frontdesk_auth_headers(client: AsyncClient):
    login_res = await client.post(f"{settings.API_V1_PREFIX}/auth/login", json={
        "email": "frontdesk@avtest.com",
        "password": "Password123!"
    })
    token = login_res.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
