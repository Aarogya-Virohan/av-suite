"""Exercise templates (EL-D-009).

A clinic makes its own templates (exercises with default dose), sees AV
templates (clinic_id NULL) read-only, and never sees another clinic's.
Every exercise must be visible to the clinic. A template only fills a
prescription; nothing here touches prescriptions.
"""

from __future__ import annotations

import pathlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.exercise_template import ExerciseTemplate, ExerciseTemplateItem
from tests.test_exercise_categories import KNEE, _clinic, _exercise, _seed

pytestmark = pytest.mark.asyncio
API = settings.API_V1_PREFIX
URL = f"{API}/exercise-templates"
VERSIONS = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _body(*exercise_ids, name="Knee week 1", **extra):
    return {
        "name": name,
        "description": "Early post-op knee",
        "items": [
            {"exercise_id": str(e), "sets": 3, "reps": 12, "hold": 5, "frequency": "Twice daily", "note": "Slow"}
            for e in exercise_ids
        ],
        **extra,
    }


async def _count(db: AsyncSession, model) -> int:
    db.expire_all()
    return (await db.execute(select(func.count()).select_from(model))).scalar_one()


async def test_create_list_get_keeps_order_and_dose(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic_id, headers = await _clinic(db_session)
    own = await _exercise(db_session, clinic_id, "Own quad set", KNEE)
    glob = await _exercise(db_session, None, f"Global SLR {uuid.uuid4().hex[:6]}", KNEE)

    res = await client.post(URL, json=_body(glob, own, name="  Knee week 1  "), headers=headers)
    assert res.status_code == 201, res.text
    t = res.json()["data"]
    assert t["name"] == "Knee week 1"
    assert t["is_global"] is False and t["clinic_id"] == str(clinic_id)
    assert [i["exercise_id"] for i in t["items"]] == [str(glob), str(own)]
    first = t["items"][0]
    assert (first["sets"], first["reps"], first["hold"], first["frequency"], first["note"]) == (3, 12, 5, "Twice daily", "Slow")
    assert first["exercise"]["title"].startswith("Global SLR")
    assert [c["id"] for c in first["exercise"]["categories"]] == [str(KNEE)]

    listed = (await client.get(URL, headers=headers)).json()["data"]
    assert [x["id"] for x in listed] == [t["id"]]

    got = await client.get(f"{URL}/{t['id']}", headers=headers)
    assert got.status_code == 200
    assert [i["exercise_id"] for i in got.json()["data"]["items"]] == [str(glob), str(own)]


async def test_update_replaces_items_and_delete_removes_all(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic_id, headers = await _clinic(db_session)
    a = await _exercise(db_session, clinic_id, "A")
    b = await _exercise(db_session, clinic_id, "B")
    c = await _exercise(db_session, clinic_id, "C")
    t = (await client.post(URL, json=_body(a, b), headers=headers)).json()["data"]

    res = await client.put(f"{URL}/{t['id']}", json=_body(c, a, name="Renamed", description="  "), headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["name"] == "Renamed" and data["description"] is None
    assert [i["exercise_id"] for i in data["items"]] == [str(c), str(a)]
    assert [i["position"] for i in data["items"]] == [0, 1]

    res = await client.delete(f"{URL}/{t['id']}", headers=headers)
    assert res.status_code == 200
    db_session.expire_all()
    left = await db_session.execute(
        select(func.count()).select_from(ExerciseTemplateItem).where(ExerciseTemplateItem.template_id == uuid.UUID(t["id"]))
    )
    assert left.scalar_one() == 0
    assert (await client.get(f"{URL}/{t['id']}", headers=headers)).status_code == 404


async def test_other_clinic_cannot_see_or_change(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    owner, owner_headers = await _clinic(db_session)
    _other, other_headers = await _clinic(db_session)
    ex = await _exercise(db_session, owner, "Owner only")
    t = (await client.post(URL, json=_body(ex), headers=owner_headers)).json()["data"]

    assert (await client.get(URL, headers=other_headers)).json()["data"] == []
    assert (await client.get(f"{URL}/{t['id']}", headers=other_headers)).status_code == 404
    assert (await client.put(f"{URL}/{t['id']}", json=_body(ex), headers=other_headers)).status_code == 404
    assert (await client.delete(f"{URL}/{t['id']}", headers=other_headers)).status_code == 404
    assert (await client.get(f"{URL}/{t['id']}", headers=owner_headers)).status_code == 200


async def test_exercise_from_another_clinic_is_rejected(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    other, _ = await _clinic(db_session)
    clinic_id, headers = await _clinic(db_session)
    mine = await _exercise(db_session, clinic_id, "Mine")
    theirs = await _exercise(db_session, other, "Theirs")
    before = await _count(db_session, ExerciseTemplate)

    res = await client.post(URL, json=_body(mine, theirs), headers=headers)
    assert res.status_code == 422, res.text
    assert "1 exercise(s) not found" in res.json()["detail"]

    res = await client.post(URL, json=_body(uuid.uuid4()), headers=headers)
    assert res.status_code == 422
    assert await _count(db_session, ExerciseTemplate) == before


@pytest.mark.parametrize(
    "change",
    [
        {"name": "   "},
        {"items": []},
        {"items": "repeat"},
        {"items": [{"sets": 0}]},
        {"items": [{"reps": 201}]},
        {"items": [{"hold": 601}]},
    ],
    ids=["blank-name", "no-items", "repeat-exercise", "sets-0", "reps-201", "hold-601"],
)
async def test_bad_input_gives_422_and_saves_nothing(client: AsyncClient, db_session: AsyncSession, change) -> None:
    await _seed(db_session)
    clinic_id, headers = await _clinic(db_session)
    ex = await _exercise(db_session, clinic_id, "Ex")
    body = _body(ex)
    if "name" in change:
        body["name"] = change["name"]
    elif change["items"] == "repeat":
        body["items"] = body["items"] * 2
    elif change["items"] == []:
        body["items"] = []
    else:
        body["items"][0].update(change["items"][0])
    before = await _count(db_session, ExerciseTemplate)

    res = await client.post(URL, json=body, headers=headers)

    assert res.status_code == 422, res.text
    assert await _count(db_session, ExerciseTemplate) == before


async def test_av_template_is_listed_but_read_only(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic_id, headers = await _clinic(db_session)
    glob = await _exercise(db_session, None, f"Global {uuid.uuid4().hex[:6]}")
    av = ExerciseTemplate(clinic_id=None, name=f"zz AV {uuid.uuid4().hex[:6]}")
    av.items = [ExerciseTemplateItem(exercise_id=glob, position=0)]
    db_session.add(av)
    await db_session.commit()
    av_id = av.id
    own = (await client.post(URL, json=_body(glob, name="aa Own"), headers=headers)).json()["data"]

    listed = (await client.get(URL, headers=headers)).json()["data"]
    ids = [x["id"] for x in listed]
    # Own first, then AV templates.
    assert ids.index(own["id"]) < ids.index(str(av_id))
    assert next(x for x in listed if x["id"] == str(av_id))["is_global"] is True

    res = await client.put(f"{URL}/{av_id}", json=_body(glob), headers=headers)
    assert res.status_code == 403 and "AV library" in res.json()["detail"]
    assert (await client.delete(f"{URL}/{av_id}", headers=headers)).status_code == 403
    assert (await client.get(f"{URL}/{av_id}", headers=headers)).status_code == 200


async def test_deleting_an_exercise_drops_it_from_templates(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic_id, headers = await _clinic(db_session)
    keep = await _exercise(db_session, clinic_id, "Keep")
    gone = await _exercise(db_session, clinic_id, "Gone")
    t = (await client.post(URL, json=_body(keep, gone), headers=headers)).json()["data"]

    assert (await client.delete(f"{API}/exercises/{gone}", headers=headers)).status_code == 200

    data = (await client.get(f"{URL}/{t['id']}", headers=headers)).json()["data"]
    assert [i["exercise_id"] for i in data["items"]] == [str(keep)]


async def test_migration_chains_from_master_import() -> None:
    text = (VERSIONS / "a3d8f1c5e7b2_exercise_templates.py").read_text()
    assert 'down_revision: Union[str, Sequence[str], None] = "f4a9c2e7b1d3"' in text
    # Only this migration builds on the master import, so there is one head.
    assert sum('None] = "f4a9c2e7b1d3"' in p.read_text() for p in VERSIONS.glob("*.py")) == 1
