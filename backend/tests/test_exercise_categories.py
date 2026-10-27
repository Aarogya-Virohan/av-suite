"""Exercise categories (EL-D-005).

- The category list in app/services/exercise_categories.py and the frozen
  copy in the seeding migration are the same, with the same ids.
- GET /exercises/categories: groups in panel order, counts only over
  exercises the clinic can see.
- GET /exercises?category=...: OR inside a group, AND across groups.
- Create and update set, keep or clear categories; unknown or inactive ids
  are refused with 422 and nothing is saved.
"""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.exercise_category import ExerciseCategory, exercise_category_links
from app.models.membership import Membership
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.services import exercise_categories as cats
from app.services.exercise_categories import category_id

pytestmark = pytest.mark.asyncio
API = settings.API_V1_PREFIX
MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "d2f6a8c0e4b1_exercise_categories.py"

KNEE = category_id("joint_region", "Knee")
HIPS = category_id("joint_region", "Hips")
STANDING = category_id("position", "Standing")
SUPINE = category_id("position", "Supine")
BAND = category_id("equipment", "Resistance band")


async def _seed(db: AsyncSession) -> None:
    """Tests build tables with create_all, so seed the list like the migration."""
    await db.execute(delete(exercise_category_links))
    await db.execute(delete(ExerciseCategory))
    db.add_all(
        ExerciseCategory(id=r.id, group_key=r.group_key, name=r.name, sort_order=r.sort_order, is_active=True)
        for r in cats.seed_rows()
    )
    await db.commit()


async def _clinic(db: AsyncSession, role: UserRole = UserRole.ADMIN):
    clinic = Clinic(name=f"Cat Clinic {uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(), clinic_id=None, email=f"cat-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=role, first_name="Asha", last_name="Rao", is_active=True,
    )
    db.add_all([clinic, user])
    await db.flush()
    user.clinic_id = clinic.id
    db.add(Membership(user_id=user.id, clinic_id=clinic.id, role=role))
    for product in ("exercise-library", "exercise-prescription"):
        db.add(WorkspaceProduct(clinic_id=clinic.id, product_id=product, status=EntitlementStatus.ENABLED))
    await db.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=role.value)
    return clinic.id, {"Authorization": f"Bearer {token}"}


async def _exercise(db: AsyncSession, clinic_id, title: str, *category_ids) -> uuid.UUID:
    ex = Exercise(clinic_id=clinic_id, title=title, body_part=None)
    db.add(ex)
    await db.flush()
    ex_id = ex.id
    for cid in category_ids:
        await db.execute(exercise_category_links.insert().values(exercise_id=ex_id, category_id=cid))
    await db.commit()
    return ex_id


async def _links(db: AsyncSession, exercise_id) -> set[uuid.UUID]:
    rows = await db.execute(
        select(exercise_category_links.c.category_id).where(exercise_category_links.c.exercise_id == exercise_id)
    )
    return set(rows.scalars().all())


# ------------------------------------------------------------------ list data


async def test_list_matches_migration_seed() -> None:
    spec = importlib.util.spec_from_file_location("cat_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.NAMESPACE == cats.CATEGORY_NAMESPACE
    assert tuple(k for k, _ in module.SEED) == cats.GROUP_KEYS
    for key, names in module.SEED:
        assert tuple(names) == cats.VALUES[key], key


async def test_list_shape() -> None:
    sizes = {k: len(v) for k, v in cats.VALUES.items()}
    assert sizes == {
        "joint_region": 25, "position": 11, "movement": 22, "equipment": 73,
        "difficulty": 3, "specialty": 18, "objective": 37, "condition": 12,
        "water_property": 8, "assistance": 2, "age_group": 5,
    }
    for key, names in cats.VALUES.items():
        assert len(set(names)) == len(names), key
        assert all(n == n.strip() and 0 < len(n) <= 100 for n in names), key
    ids = [r.id for r in cats.seed_rows()]
    assert len(set(ids)) == len(ids) == 216
    # Fixed ids: the same group and name always give the same id.
    assert category_id("joint_region", "Knee") == uuid.uuid5(cats.CATEGORY_NAMESPACE, "joint_region:Knee")
    assert cats.VALUES["joint_region"][:4] == ("Facial", "TMJ", "Vestibular", "Cervical")
    assert cats.VALUES["difficulty"] == ("Beginner", "Intermediate", "Advanced")


# ------------------------------------------------------------------ API


async def test_categories_endpoint_groups_and_scoped_counts(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic_a, headers_a = await _clinic(db_session)
    clinic_b, _ = await _clinic(db_session)
    await _exercise(db_session, None, "Global knee", KNEE, STANDING)
    await _exercise(db_session, clinic_a, "A knee", KNEE)
    await _exercise(db_session, clinic_b, "B knee", KNEE, HIPS)

    res = await client.get(f"{API}/exercises/categories", headers=headers_a)
    assert res.status_code == 200, res.text
    groups = res.json()["data"]
    assert [g["key"] for g in groups] == list(cats.GROUP_KEYS)
    assert groups[0]["label"] == "Joint/Region"
    region = {v["name"]: v for v in groups[0]["values"]}
    assert [v["name"] for v in groups[0]["values"]] == list(cats.VALUES["joint_region"])
    assert region["Knee"]["count"] == 2  # global + own, not clinic B's
    assert region["Knee"]["id"] == str(KNEE)
    assert region["Hips"]["count"] == 0  # only clinic B has it
    position = {v["name"]: v["count"] for v in groups[1]["values"]}
    assert position["Standing"] == 1


async def test_filter_or_inside_group_and_across_groups(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic, headers = await _clinic(db_session)
    other, _ = await _clinic(db_session)
    knee_standing = await _exercise(db_session, clinic, "Knee standing", KNEE, STANDING)
    knee_supine = await _exercise(db_session, clinic, "Knee supine", KNEE, SUPINE)
    hips_standing = await _exercise(db_session, None, "Hips standing", HIPS, STANDING)
    await _exercise(db_session, clinic, "No tags")
    await _exercise(db_session, other, "Other clinic knee", KNEE, STANDING)

    async def titles(*ids, **params):
        res = await client.get(
            f"{API}/exercises", headers=headers,
            params=[("category", str(i)) for i in ids] + [("page_size", "100")] + list(params.items()),
        )
        assert res.status_code == 200, res.text
        return {e["title"] for e in res.json()["data"]}, res.json()["meta"]["total"]

    assert await titles(KNEE) == ({"Knee standing", "Knee supine"}, 2)
    assert await titles(KNEE, HIPS) == ({"Knee standing", "Knee supine", "Hips standing"}, 3)
    assert await titles(KNEE, STANDING) == ({"Knee standing"}, 1)
    assert await titles(KNEE, HIPS, STANDING) == ({"Knee standing", "Hips standing"}, 2)
    assert await titles(KNEE, BAND) == (set(), 0)
    assert await titles(KNEE, search="supine") == ({"Knee supine"}, 1)
    # Comma separated works too.
    res = await client.get(f"{API}/exercises", headers=headers, params={"category": f"{KNEE},{STANDING}"})
    assert {e["title"] for e in res.json()["data"]} == {"Knee standing"}
    # Rows carry their categories in panel order.
    row = next(e for e in res.json()["data"])
    assert [c["id"] for c in row["categories"]] == [str(KNEE), str(STANDING)]
    assert row["categories"][0] == {"id": str(KNEE), "group_key": "joint_region", "name": "Knee"}


async def test_filter_rejects_bad_and_unknown_ids(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    _, headers = await _clinic(db_session)
    res = await client.get(f"{API}/exercises", headers=headers, params={"category": "not-a-uuid"})
    assert res.status_code == 422
    res = await client.get(f"{API}/exercises", headers=headers, params={"category": str(uuid.uuid4())})
    assert res.status_code == 422


async def test_create_update_set_keep_and_clear(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    _, headers = await _clinic(db_session)

    res = await client.post(
        f"{API}/exercises", headers=headers,
        json={"title": "Mini squat", "category_ids": [str(STANDING), str(KNEE), str(KNEE)]},
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    ex_id = uuid.UUID(body["id"])
    assert [c["name"] for c in body["categories"]] == ["Knee", "Standing"]
    assert await _links(db_session, ex_id) == {KNEE, STANDING}

    # Omitted: unchanged.
    res = await client.put(f"{API}/exercises/{ex_id}", headers=headers, json={"title": "Mini squat 2"})
    assert res.status_code == 200, res.text
    assert await _links(db_session, ex_id) == {KNEE, STANDING}
    assert [c["name"] for c in res.json()["data"]["categories"]] == ["Knee", "Standing"]

    # A list replaces.
    res = await client.put(f"{API}/exercises/{ex_id}", headers=headers, json={"category_ids": [str(BAND)]})
    assert res.status_code == 200, res.text
    assert await _links(db_session, ex_id) == {BAND}

    # Empty list clears.
    res = await client.put(f"{API}/exercises/{ex_id}", headers=headers, json={"category_ids": []})
    assert res.status_code == 200, res.text
    assert await _links(db_session, ex_id) == set()
    assert res.json()["data"]["categories"] == []

    # Detail shows categories too.
    await client.put(f"{API}/exercises/{ex_id}", headers=headers, json={"category_ids": [str(HIPS)]})
    res = await client.get(f"{API}/exercises/{ex_id}", headers=headers)
    assert [c["name"] for c in res.json()["data"]["categories"]] == ["Hips"]


async def test_unknown_or_inactive_ids_save_nothing(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed(db_session)
    clinic, headers = await _clinic(db_session)

    res = await client.post(
        f"{API}/exercises", headers=headers,
        json={"title": "Ghost tag", "category_ids": [str(KNEE), str(uuid.uuid4())]},
    )
    assert res.status_code == 422
    count = await db_session.execute(select(Exercise).where(Exercise.title == "Ghost tag"))
    assert count.scalars().first() is None

    ex_id = await _exercise(db_session, clinic, "Tagged", KNEE)
    await db_session.execute(
        update(ExerciseCategory).where(ExerciseCategory.id == HIPS).values(is_active=False)
    )
    await db_session.commit()
    res = await client.put(f"{API}/exercises/{ex_id}", headers=headers, json={"category_ids": [str(HIPS)]})
    assert res.status_code == 422
    assert await _links(db_session, ex_id) == {KNEE}

    # An inactive category is hidden from the panel.
    res = await client.get(f"{API}/exercises/categories", headers=headers)
    names = [v["name"] for v in res.json()["data"][0]["values"]]
    assert "Hips" not in names and "Knee" in names
