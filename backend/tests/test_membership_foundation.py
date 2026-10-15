import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import PermissionContext, get_authenticated_context
from app.core.security import create_access_token
from app.enums.clinic import ClinicType
from app.enums.permission import CapabilityScope
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.user import User


@pytest.mark.asyncio
async def test_workspace_types_are_supported(db_session):
    valid_types = {item.value for item in ClinicType}
    assert valid_types == {"clinic", "solo", "personal"}


@pytest.mark.asyncio
async def test_membership_creation_succeeds(db_session):
    clinic = Clinic(name="Test Clinic", type=ClinicType.CLINIC)
    db_session.add(clinic)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="member@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Member",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    membership = Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN)
    db_session.add(membership)
    await db_session.commit()

    assert membership.id is not None
    assert membership.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_duplicate_membership_is_rejected(db_session):
    clinic = Clinic(name="Duplicate Clinic", type=ClinicType.CLINIC)
    db_session.add(clinic)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="duplicate@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Dup",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN)
    )
    await db_session.commit()

    second_membership = Membership(
        user_id=user.id, clinic_id=clinic.id, role=UserRole.THERAPIST
    )
    db_session.add(second_membership)
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_can_belong_to_multiple_clinics(db_session):
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email="multi@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Multi",
        last_name="User",
        is_active=True,
    )
    clinic_a = Clinic(name="Clinic A", type=ClinicType.CLINIC)
    clinic_b = Clinic(name="Clinic B", type=ClinicType.SOLO)
    db_session.add_all([user, clinic_a, clinic_b])
    await db_session.flush()

    membership_a = Membership(
        user_id=user.id, clinic_id=clinic_a.id, role=UserRole.ADMIN
    )
    membership_b = Membership(
        user_id=user.id, clinic_id=clinic_b.id, role=UserRole.THERAPIST
    )
    db_session.add_all([membership_a, membership_b])
    await db_session.commit()

    memberships = (
        (
            await db_session.execute(
                select(Membership).where(Membership.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(memberships) == 2
    assert {m.clinic_id for m in memberships} == {clinic_a.id, clinic_b.id}


@pytest.mark.asyncio
async def test_same_user_can_have_different_roles_in_different_clinics(db_session):
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email="roles@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Role",
        last_name="User",
        is_active=True,
    )
    clinic_1 = Clinic(name="Clinic One", type=ClinicType.CLINIC)
    clinic_2 = Clinic(name="Clinic Two", type=ClinicType.PERSONAL)
    db_session.add_all([user, clinic_1, clinic_2])
    await db_session.flush()

    membership_1 = Membership(
        user_id=user.id, clinic_id=clinic_1.id, role=UserRole.ADMIN
    )
    membership_2 = Membership(
        user_id=user.id, clinic_id=clinic_2.id, role=UserRole.FRONT_DESK
    )
    db_session.add_all([membership_1, membership_2])
    await db_session.commit()

    assert membership_1.role == UserRole.ADMIN
    assert membership_2.role == UserRole.FRONT_DESK


@pytest.mark.asyncio
async def test_membership_role_is_authoritative_over_legacy_user_fields(db_session):
    clinic = Clinic(name="Legacy Clinic", type=ClinicType.CLINIC)
    db_session.add(clinic)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="legacy@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Legacy",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    membership = Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.THERAPIST)
    db_session.add(membership)
    await db_session.commit()

    token = create_access_token(
        subject=user.id, clinic_id=clinic.id, role=UserRole.ADMIN.value
    )
    ctx = await get_authenticated_context(token, db_session)

    assert ctx.membership_role == UserRole.THERAPIST


@pytest.mark.asyncio
async def test_authenticated_context_resolves_working_membership(db_session):
    clinic = Clinic(name="Membership Clinic", type=ClinicType.CLINIC)
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email="workspace@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Workspace",
        last_name="User",
        is_active=True,
    )
    db_session.add_all([clinic, user])
    await db_session.flush()

    membership = Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN)
    db_session.add(membership)
    await db_session.commit()

    token = create_access_token(
        subject=user.id, clinic_id=clinic.id, role=membership.role.value
    )
    ctx = await get_authenticated_context(token, db_session)

    assert ctx.user.id == user.id
    assert ctx.clinic.id == clinic.id
    assert ctx.membership.id == membership.id
    assert ctx.membership_role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_authenticated_context_rejects_legacy_user_without_membership(db_session):
    clinic = Clinic(name="Legacy-only Clinic", type=ClinicType.CLINIC)
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email="legacy-only@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Legacy",
        last_name="Only",
        is_active=True,
    )
    db_session.add_all([clinic, user])
    await db_session.commit()

    token = create_access_token(
        subject=user.id, clinic_id=clinic.id, role=UserRole.ADMIN.value
    )
    with pytest.raises(HTTPException) as error:
        await get_authenticated_context(token, db_session)

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_rbac_behaviour_still_uses_role_templates(db_session):
    clinic = Clinic(name="Rbac Clinic", type=ClinicType.CLINIC)
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email="rbac@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Rbac",
        last_name="User",
        is_active=True,
    )
    db_session.add_all([clinic, user])
    await db_session.flush()

    membership = Membership(
        user_id=user.id, clinic_id=clinic.id, role=UserRole.THERAPIST
    )
    db_session.add(membership)
    await db_session.commit()

    perm_ctx = PermissionContext(
        user=user, clinic=clinic, membership=membership, overrides={}
    )
    assert perm_ctx.effective_scope("patients.view") == CapabilityScope.NONE
    assert perm_ctx.effective_scope("posture.view") == CapabilityScope.NONE
