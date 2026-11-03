from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementSource, EntitlementStatus
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission
from app.screening import rate_limit
from app.services.product_entitlements import ensure_canonical_products

API = settings.API_V1_PREFIX
PRODUCT = "psycho-social-screening"
# Patients made here are removed after each test (FK cascade removes their
# screening rows) so shared-DB tests elsewhere that read page 1 of the
# patient list are not pushed off it.
TEST_SURNAME_PREFIX = "ScrTest"


@pytest.fixture(autouse=True)
def _reset_limiters():
    rate_limit.token_limiter.reset()
    rate_limit.ip_limiter.reset()
    yield
    rate_limit.token_limiter.reset()
    rate_limit.ip_limiter.reset()


async def entitle(db: AsyncSession, clinic_id: uuid.UUID) -> None:
    await ensure_canonical_products(db)
    existing = await db.scalar(
        select(WorkspaceProduct).where(
            WorkspaceProduct.clinic_id == clinic_id, WorkspaceProduct.product_id == PRODUCT
        )
    )
    if existing is None:
        db.add(
            WorkspaceProduct(
                clinic_id=clinic_id,
                product_id=PRODUCT,
                status=EntitlementStatus.ENABLED,
                source=EntitlementSource.DIRECT,
            )
        )
    await db.commit()


async def set_overrides(
    db: AsyncSession, clinic_id: uuid.UUID, user_id: uuid.UUID, grants: dict[str, str]
) -> None:
    await db.execute(
        delete(UserPermission).where(
            UserPermission.clinic_id == clinic_id,
            UserPermission.user_id == user_id,
            UserPermission.capability_key.like("screening.%"),
        )
    )
    for key, scope in grants.items():
        db.add(
            UserPermission(
                clinic_id=clinic_id,
                user_id=user_id,
                capability_key=key,
                scope=CapabilityScope(scope),
            )
        )
    await db.commit()


async def user_by_email(db: AsyncSession, email: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


async def make_patient(db: AsyncSession, clinic_id: uuid.UUID, first: str = "Asha") -> Patient:
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        first_name=first,
        last_name=f"{TEST_SURNAME_PREFIX}{uuid.uuid4().hex[:6]}",
    )
    db.add(patient)
    await db.commit()
    return patient


@pytest.fixture
async def env(db_session: AsyncSession):
    admin = await user_by_email(db_session, "admin@avtest.com")
    therapist = await user_by_email(db_session, "therapist@avtest.com")
    clinic = await db_session.get(Clinic, admin.clinic_id)
    await entitle(db_session, clinic.id)
    await set_overrides(
        db_session,
        clinic.id,
        therapist.id,
        {"screening.assign": "all", "screening.view": "own", "screening.refer": "own"},
    )
    await set_overrides(db_session, clinic.id, admin.id, {})
    clinic_id, therapist_id = clinic.id, therapist.id
    yield {"clinic": clinic, "admin": admin, "therapist": therapist}
    await db_session.rollback()
    await db_session.execute(
        delete(Patient).where(Patient.last_name.like(f"{TEST_SURNAME_PREFIX}%"))
    )
    await db_session.commit()
    await set_overrides(db_session, clinic_id, therapist_id, {})
