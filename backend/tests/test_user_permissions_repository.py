from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.permission import CapabilityScope
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.user import User
from app.repositories.user_permission import UserPermissionRepository

pytestmark = pytest.mark.asyncio


async def _create_user(session: AsyncSession, *, clinic_id: UUID | None = None) -> User:
    clinic = Clinic(
        id=clinic_id or uuid4(),
        name=f"Permission Test Clinic {uuid4()}",
        branding_color="#008080",
        plan_tier="clinical_pro",
        is_partner_clinic=True,
    )
    user = User(
        id=uuid4(),
        clinic_id=clinic.id,
        email=f"user-{uuid4()}@avtest.com",
        password_hash="test-hash",
        role=UserRole.THERAPIST,
        first_name="Permission",
        last_name="User",
        is_active=True,
    )
    session.add_all([clinic, user])
    await session.flush()
    return user


async def test_create_user_permission_override(db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    repo = UserPermissionRepository(db_session)

    override = await repo.set_override(
        clinic_id=user.clinic_id,
        user_id=user.id,
        capability_key=f"permissions.test.{uuid4()}",
        scope=CapabilityScope.OWN,
        granted_by=None,
    )

    assert override.id is not None
    assert override.scope == CapabilityScope.OWN
    assert override.user_id == user.id
    assert override.clinic_id == user.clinic_id


async def test_retrieve_user_permission_overrides(db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    repo = UserPermissionRepository(db_session)
    capability_key = f"permissions.test.{uuid4()}"
    await repo.set_override(
        clinic_id=user.clinic_id,
        user_id=user.id,
        capability_key=capability_key,
        scope=CapabilityScope.ALL,
        granted_by=None,
    )

    overrides = await repo.list_for_user(user.id)
    clinic_overrides = await repo.list_for_user_in_clinic(user.clinic_id, user.id)

    assert [override.capability_key for override in overrides] == [capability_key]
    assert [override.capability_key for override in clinic_overrides] == [capability_key]


async def test_update_user_permission_override(db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    repo = UserPermissionRepository(db_session)
    capability_key = f"permissions.test.{uuid4()}"
    created = await repo.set_override(
        clinic_id=user.clinic_id,
        user_id=user.id,
        capability_key=capability_key,
        scope=CapabilityScope.OWN,
        granted_by=None,
    )

    updated = await repo.set_override(
        clinic_id=user.clinic_id,
        user_id=user.id,
        capability_key=capability_key,
        scope=CapabilityScope.NONE,
        granted_by=None,
    )

    assert updated.id == created.id
    assert updated.scope == CapabilityScope.NONE


async def test_delete_user_permission_override(db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    repo = UserPermissionRepository(db_session)
    capability_key = f"permissions.test.{uuid4()}"
    await repo.set_override(
        clinic_id=user.clinic_id,
        user_id=user.id,
        capability_key=capability_key,
        scope=CapabilityScope.OWN,
        granted_by=None,
    )

    deleted = await repo.delete_for_user_capability(
        clinic_id=user.clinic_id,
        user_id=user.id,
        capability_key=capability_key,
    )

    assert deleted is True
    assert await repo.get_for_user_capability(user.id, capability_key, clinic_id=user.clinic_id) is None


async def test_unique_user_capability_constraint(db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    repo = UserPermissionRepository(db_session)
    capability_key = f"permissions.test.{uuid4()}"
    payload = {
        "clinic_id": user.clinic_id,
        "user_id": user.id,
        "capability_key": capability_key,
        "scope": CapabilityScope.OWN,
        "granted_by": None,
    }

    await repo.create(payload)
    with pytest.raises(IntegrityError):
        await repo.create(payload)

    await db_session.rollback()


async def test_user_permission_clinic_isolation(db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    other_user = await _create_user(db_session)
    repo = UserPermissionRepository(db_session)
    capability_key = f"permissions.test.{uuid4()}"
    await repo.set_override(
        clinic_id=user.clinic_id,
        user_id=user.id,
        capability_key=capability_key,
        scope=CapabilityScope.OWN,
        granted_by=None,
    )
    await repo.set_override(
        clinic_id=other_user.clinic_id,
        user_id=other_user.id,
        capability_key=capability_key,
        scope=CapabilityScope.ALL,
        granted_by=None,
    )

    same_clinic = await repo.list_for_user_in_clinic(user.clinic_id, user.id)
    wrong_clinic = await repo.list_for_user_in_clinic(other_user.clinic_id, user.id)

    assert [override.user_id for override in same_clinic] == [user.id]
    assert wrong_clinic == []
