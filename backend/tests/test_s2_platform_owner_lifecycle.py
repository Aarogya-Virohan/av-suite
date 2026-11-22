from __future__ import annotations

import asyncio
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import func, select, update

from app.core.platform_security import create_platform_access_token
from app.core.security import get_password_hash
from app.exceptions import BaseAppException
from app.main import app
from app.models.platform import PlatformOperator
from app.scripts import create_platform_operator as cli
from app.services.platform_operator_lifecycle import ensure_another_active_owner_remains


pytestmark = pytest.mark.asyncio
API = "/api/v1/platform/operators"


def make_operator(role: str = "owner", *, active: bool = True) -> PlatformOperator:
    return PlatformOperator(
        email=f"owner-lifecycle-{uuid.uuid4()}@example.com",
        password_hash=get_password_hash("LifecyclePass123!"),
        name="Lifecycle Operator",
        role=role,
        is_active=active,
        mfa_enabled=True,
        mfa_secret="encrypted-test-secret",
    )


async def test_api_owner_lifecycle_contract_and_error_envelopes(client, db_session):
    actor = make_operator()
    target = make_operator()
    inactive_owner = make_operator(active=False)
    db_session.add_all([actor, target, inactive_owner])
    await db_session.commit()
    token = create_platform_access_token(actor)
    headers = {"Authorization": f"Bearer {token}"}

    self_deactivation = await client.patch(
        f"{API}/{actor.id}",
        headers=headers,
        json={"is_active": False, "reason": "self test"},
    )
    assert self_deactivation.status_code == 422
    assert self_deactivation.json()["data"] is None
    assert self_deactivation.json()["meta"]["error"]["code"] == "VALIDATION_ERROR"

    owner_demotion = await client.patch(
        f"{API}/{target.id}",
        headers=headers,
        json={"role": "support", "reason": "role changes are CLI only"},
    )
    assert owner_demotion.status_code == 403
    assert owner_demotion.json()["meta"]["error"]["code"] == "FORBIDDEN"

    deactivated = await client.patch(
        f"{API}/{target.id}",
        headers=headers,
        json={"is_active": False, "reason": "lost credentials"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["is_active"] is False

    owner_reactivation = await client.patch(
        f"{API}/{inactive_owner.id}",
        headers=headers,
        json={"is_active": True, "reason": "reactivation is CLI only"},
    )
    assert owner_reactivation.status_code == 403
    assert owner_reactivation.json()["data"] is None
    assert owner_reactivation.json()["meta"]["error"]["code"] == "FORBIDDEN"

    await db_session.refresh(actor)
    await db_session.refresh(target)
    await db_session.refresh(inactive_owner)
    assert actor.is_active and actor.role == "owner"
    assert not target.is_active and target.role == "owner"
    assert not inactive_owner.is_active and inactive_owner.role == "owner"


async def test_only_active_owner_gets_last_owner_conflict_before_self_validation(
    client, db_session
):
    await db_session.execute(
        update(PlatformOperator)
        .where(
            PlatformOperator.role == "owner",
            PlatformOperator.is_active.is_(True),
        )
        .values(is_active=False)
    )
    sole_owner = make_operator()
    db_session.add(sole_owner)
    await db_session.commit()
    token_version_before = sole_owner.token_version
    headers = {
        "Authorization": f"Bearer {create_platform_access_token(sole_owner)}"
    }

    response = await client.patch(
        f"{API}/{sole_owner.id}",
        headers=headers,
        json={"is_active": False, "reason": "last owner regression"},
    )

    assert response.status_code == 409
    assert response.json()["data"] is None
    assert response.json()["meta"]["error"]["code"] == "CONFLICT"
    await db_session.refresh(sole_owner)
    assert sole_owner.is_active is True
    assert sole_owner.token_version == token_version_before


async def test_cli_can_demote_an_owner_when_another_active_owner_remains(
    client, db_session, sessionmaker, monkeypatch
):
    await db_session.execute(
        update(PlatformOperator)
        .where(PlatformOperator.role == "owner")
        .values(is_active=False)
    )
    demoted, remaining = make_operator(), make_operator()
    db_session.add_all([demoted, remaining])
    await db_session.commit()
    monkeypatch.setattr(cli, "AsyncSessionLocal", sessionmaker)

    await cli.run(
        SimpleNamespace(
            command="change-role", operator_id=str(demoted.id), role="support"
        )
    )

    await db_session.refresh(demoted)
    await db_session.refresh(remaining)
    assert demoted.role == "support" and demoted.is_active
    assert remaining.role == "owner" and remaining.is_active


async def test_cli_rejects_demotion_of_the_last_active_owner(
    client, db_session, sessionmaker, monkeypatch
):
    await db_session.execute(
        update(PlatformOperator)
        .where(PlatformOperator.role == "owner")
        .values(is_active=False)
    )
    sole_owner = make_operator()
    db_session.add(sole_owner)
    await db_session.commit()
    monkeypatch.setattr(cli, "AsyncSessionLocal", sessionmaker)

    with pytest.raises(BaseAppException) as rejected:
        await cli.run(
            SimpleNamespace(
                command="change-role", operator_id=str(sole_owner.id), role="support"
            )
        )
    assert rejected.value.status_code == 409
    assert rejected.value.code == "CONFLICT"
    assert rejected.value.message == "Cannot demote the last active Owner"

    await db_session.refresh(sole_owner)
    assert sole_owner.role == "owner" and sole_owner.is_active


async def test_concurrent_cli_owner_demotions_leave_one_active_owner(
    client, db_session, sessionmaker, monkeypatch
):
    await db_session.execute(
        update(PlatformOperator)
        .where(PlatformOperator.role == "owner")
        .values(is_active=False)
    )
    owners = [make_operator(), make_operator()]
    db_session.add_all(owners)
    await db_session.commit()
    monkeypatch.setattr(cli, "AsyncSessionLocal", sessionmaker)

    results = await asyncio.gather(
        *(
            cli.run(
                SimpleNamespace(
                    command="change-role",
                    operator_id=str(owner.id),
                    role="support",
                )
            )
            for owner in owners
        ),
        return_exceptions=True,
    )

    assert sum(result is None for result in results) == 1
    conflicts = [result for result in results if isinstance(result, BaseAppException)]
    assert len(conflicts) == 1
    assert conflicts[0].status_code == 409
    async with sessionmaker() as session:
        active_owners = await session.scalar(
            select(func.count())
            .select_from(PlatformOperator)
            .where(
                PlatformOperator.id.in_([owner.id for owner in owners]),
                PlatformOperator.role == "owner",
                PlatformOperator.is_active.is_(True),
            )
        )
    assert active_owners == 1
