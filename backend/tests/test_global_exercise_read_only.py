"""Global exercises are read-only for clinics (EL-D-008).

A clinic may change or delete only its own exercises. PUT or DELETE on a
global exercise gives 403 and changes nothing, title, categories and row
included. Clinic photos of a global exercise stay allowed (EL-D-004).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.exercise import Exercise
from tests.test_exercise_categories import BAND, KNEE, STANDING, _clinic, _exercise, _links, _seed

pytestmark = pytest.mark.asyncio
API = settings.API_V1_PREFIX


async def _title(db: AsyncSession, ex_id) -> str | None:
    db.expire_all()
    return (await db.execute(select(Exercise.title).where(Exercise.id == ex_id))).scalar_one_or_none()


@pytest.mark.parametrize(
    "body",
    [
        {"title": "Renamed by a clinic"},
        {"category_ids": [str(STANDING)]},
        {"category_ids": []},
        {"title": "Renamed by a clinic", "category_ids": [str(BAND)]},
    ],
    ids=["title", "categories", "clear-categories", "title-and-categories"],
)
async def test_clinic_cannot_change_global(client: AsyncClient, db_session: AsyncSession, body) -> None:
    await _seed(db_session)
    _clinic_id, headers = await _clinic(db_session)
    global_id = await _exercise(db_session, None, f"Global {uuid.uuid4().hex[:6]}", KNEE)
    before = await _title(db_session, global_id)

    res = await client.put(f"{API}/exercises/{global_id}", json=body, headers=headers)

    assert res.status_code == 403, res.text
    assert "AV library" in res.json()["detail"]
    assert await _title(db_session, global_id) == before
    assert await _links(db_session, global_id) == {KNEE}


async def test_clinic_cannot_delete_global(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    _clinic_id, headers = await _clinic(db_session)
    global_id = await _exercise(db_session, None, f"Global {uuid.uuid4().hex[:6]}", KNEE)

    res = await client.delete(f"{API}/exercises/{global_id}", headers=headers)

    assert res.status_code == 403, res.text
    assert await _title(db_session, global_id) is not None
    assert await _links(db_session, global_id) == {KNEE}


async def test_clinic_still_changes_and_deletes_its_own(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic_id, headers = await _clinic(db_session)
    own_id = await _exercise(db_session, clinic_id, "Own exercise", KNEE)

    res = await client.put(
        f"{API}/exercises/{own_id}",
        json={"title": "Own exercise v2", "category_ids": [str(STANDING)]},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert await _title(db_session, own_id) == "Own exercise v2"
    assert await _links(db_session, own_id) == {STANDING}

    res = await client.delete(f"{API}/exercises/{own_id}", headers=headers)
    assert res.status_code == 200, res.text
    assert await _title(db_session, own_id) is None


async def test_other_clinic_exercise_still_404(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    other_clinic, _ = await _clinic(db_session)
    _mine, headers = await _clinic(db_session)
    other_id = await _exercise(db_session, other_clinic, "Other clinic exercise")

    assert (await client.put(f"{API}/exercises/{other_id}", json={"title": "x"}, headers=headers)).status_code == 404
    assert (await client.delete(f"{API}/exercises/{other_id}", headers=headers)).status_code == 404
    assert await _title(db_session, other_id) == "Other clinic exercise"
