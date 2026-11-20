"""EL structure, Rx modes and Self-Epley side (EL-D-012..EL-D-016).

- exercise_structure.py and the frozen data of revision e7c3a9f1b5d2 agree:
  9 domains, 51 categories, same parent for every category, fixed ids.
- New bank exercises: fixed ids, titles unique and not equal to an existing
  prod title, rx_mode values only PATIENT / CAREGIVER / BLOCKED, Self-Epley is
  the only row that needs a side.
- GET /exercises/categories lists Domain and Category first, and every
  category value carries its domain as parent_id.
- POST / PATCH /prescriptions: BLOCKED exercise -> 422 and nothing saved;
  requires_side without side -> 422; side saved for Self-Epley and dropped
  for any other exercise; CAREGIVER allowed.
- PDF: side and "Caregiver-assisted" print on the card; the stop-pain line
  closes the prescription.
"""

from __future__ import annotations

import importlib.util
import uuid
from collections import Counter
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.exercise_category import ExerciseCategory, exercise_category_links
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.prescription import Prescription, PrescriptionItem
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.services import exercise_categories as cats
from app.services import exercise_structure as st
from app.services.prescription_pdf import SAFETY_NOTE, RxDoc, RxItem, build_prescription_html

pytestmark = pytest.mark.asyncio
API = settings.API_V1_PREFIX
ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "alembic" / "versions" / "e7c3a9f1b5d2_el_structure_domains_categories_rx_mode.py"
DATA = ROOT / "alembic" / "data" / "el_structure_20nov.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------ data


async def test_structure_matches_migration_data() -> None:
    data = _load(DATA, "el_data")
    mig = _load(MIGRATION, "el_mig")
    assert mig.NAMESPACE == cats.CATEGORY_NAMESPACE
    assert tuple(data.DOMAINS) == st.DOMAIN_NAMES
    assert len(st.DOMAIN_NAMES) == 9 and len(st.CATEGORY_NAMES) == 51
    assert len(set(st.CATEGORY_NAMES)) == 51
    assert [tuple(x) for x in data.CATEGORIES] == [(d, c) for d, cs in st.DOMAINS for c in cs]
    for d, cs in st.DOMAINS:
        for c in cs:
            assert st.CATEGORY_PARENT[st.structure_id("category", c)] == st.structure_id("domain", d)
            assert 0 < len(c) <= 100
    assert st.structure_id("domain", "Strength & Power") == uuid.uuid5(
        cats.CATEGORY_NAMESPACE, "domain:Strength & Power"
    )
    # Panel order: structure groups first, then EL-D-005 groups unchanged.
    assert [k for k, _ in cats.PANEL_GROUPS][:3] == ["domain", "category", "joint_region"]
    assert cats.GROUP_KEYS[0] == "joint_region"


async def test_new_rows_and_prod_rows_are_consistent() -> None:
    data = _load(DATA, "el_data2")
    mig = _load(MIGRATION, "el_mig2")
    names = set(st.CATEGORY_NAMES)
    ids = [r[0] for r in data.NEW]
    assert len(ids) == len(set(ids)) == 1404
    for new_id, key, title, body, cat, mode, side in data.NEW:
        assert new_id == str(uuid.uuid5(mig.BANK_NS, key))
        assert cat in names
        assert mode in st.RX_MODES
        assert title and len(title) <= 255 and body
    titles = Counter(r[2].strip().lower() for r in data.NEW)
    assert max(titles.values()) == 1
    assert [r[1] for r in data.NEW if r[6]] == ["BAL-FAC-01072-v1"]
    modes = Counter(r[5] for r in data.NEW)
    assert modes["CAREGIVER"] == 45 and modes["BLOCKED"] == 208
    prod_ids = [r[0] for r in data.PROD]
    assert len(prod_ids) == len(set(prod_ids)) == 1467
    assert not set(prod_ids) & set(ids)
    assert all(r[1] in names for r in data.PROD)
    bank_keys = [r[2] for r in data.PROD if r[2]]
    assert len(bank_keys) == len(set(bank_keys))  # one-to-one SAME
    assert not set(bank_keys) & {r[1] for r in data.NEW}
    assert len(data.BLOGSPOT) == 8 and all("blogger" in u for _e, u in data.BLOGSPOT)


# ------------------------------------------------------------------ helpers


async def _seed_structure(db: AsyncSession) -> None:
    await db.execute(delete(exercise_category_links))
    await db.execute(delete(ExerciseCategory))
    db.add_all(
        ExerciseCategory(id=r.id, group_key=r.group_key, name=r.name, sort_order=r.sort_order, is_active=True)
        for r in cats.seed_rows()
    )
    db.add_all(
        ExerciseCategory(id=i, group_key=g, name=n, sort_order=s, is_active=True) for i, g, n, s in st.seed_rows()
    )
    await db.commit()


async def _clinic(db: AsyncSession):
    clinic = Clinic(name=f"EL Clinic {uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(), clinic_id=None, email=f"el-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=UserRole.ADMIN, first_name="Asha", last_name="Rao", is_active=True,
    )
    db.add_all([clinic, user])
    await db.flush()
    user.clinic_id = clinic.id
    db.add(Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN))
    for product in ("exercise-library", "exercise-prescription"):
        db.add(WorkspaceProduct(clinic_id=clinic.id, product_id=product, status=EntitlementStatus.ENABLED))
    patient = Patient(
        clinic_id=clinic.id, display_number=uuid.uuid4().int % 9_000_000_000 + 1,
        first_name="Ravi", last_name="Kumar", phone="9000000101",
    )
    db.add(patient)
    await db.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=UserRole.ADMIN.value)
    return clinic.id, patient.id, {"Authorization": f"Bearer {token}"}


async def _ex(db: AsyncSession, title: str, mode: str = "PATIENT", side: bool = False) -> uuid.UUID:
    ex = Exercise(clinic_id=None, title=title, is_free=True, rx_mode=mode, requires_side=side)
    db.add(ex)
    await db.commit()
    return ex.id


# ------------------------------------------------------------------ API


async def test_categories_endpoint_has_domain_and_parent(client: AsyncClient, db_session: AsyncSession) -> None:
    await _seed_structure(db_session)
    _clinic_id, _p, headers = await _clinic(db_session)
    ex = await _ex(db_session, f"Squat {uuid.uuid4().hex[:4]}")
    for cid in (st.structure_id("domain", "Strength & Power"), st.structure_id("category", "Bodyweight")):
        await db_session.execute(exercise_category_links.insert().values(exercise_id=ex, category_id=cid))
    await db_session.commit()

    r = await client.get(f"{API}/exercises/categories", headers=headers)
    assert r.status_code == 200, r.text
    groups = r.json()["data"]
    assert [g["key"] for g in groups][:3] == ["domain", "category", "joint_region"]
    assert [v["name"] for v in groups[0]["values"]] == list(st.DOMAIN_NAMES)
    cat_values = groups[1]["values"]
    assert len(cat_values) == 51
    body = next(v for v in cat_values if v["name"] == "Bodyweight")
    assert body["parent_id"] == str(st.structure_id("domain", "Strength & Power"))
    assert body["count"] >= 1
    assert all("parent_id" not in v for v in groups[2]["values"])

    # Filter by a domain works like any other group (EL-D-005 rule).
    r = await client.get(
        f"{API}/exercises", headers=headers,
        params={"category": str(st.structure_id("domain", "Strength & Power")), "page_size": 50},
    )
    assert r.status_code == 200, r.text
    assert str(ex) in {e["id"] for e in r.json()["data"]}
    item = next(e for e in r.json()["data"] if e["id"] == str(ex))
    assert item["rx_mode"] == "PATIENT" and item["requires_side"] is False
    assert [c["group_key"] for c in item["categories"]] == ["domain", "category"]


async def test_blocked_exercise_refused_and_nothing_saved(client: AsyncClient, db_session: AsyncSession) -> None:
    _c, patient, headers = await _clinic(db_session)
    ok = await _ex(db_session, "Bridge")
    blocked = await _ex(db_session, "Thoracic central PA mobilisation", "BLOCKED")
    before = await db_session.scalar(select(func.count()).select_from(Prescription))

    r = await client.post(
        f"{API}/prescriptions", headers=headers,
        json={"patient_id": str(patient), "items": [{"exercise_id": str(ok)}, {"exercise_id": str(blocked)}]},
    )
    assert r.status_code == 422, r.text
    assert "Thoracic central PA mobilisation" in r.text
    assert await db_session.scalar(select(func.count()).select_from(Prescription)) == before

    # PATCH with a blocked item is refused too; the saved items stay.
    r = await client.post(
        f"{API}/prescriptions", headers=headers,
        json={"patient_id": str(patient), "items": [{"exercise_id": str(ok)}]},
    )
    assert r.status_code == 201, r.text
    rx_id = r.json()["data"]["id"]
    r = await client.patch(
        f"{API}/prescriptions/{rx_id}", headers=headers, json={"items": [{"exercise_id": str(blocked)}]}
    )
    assert r.status_code == 422, r.text
    r = await client.get(f"{API}/prescriptions/{rx_id}", headers=headers)
    assert [i["exercise_id"] for i in r.json()["data"]["items"]] == [str(ok)]


async def test_side_rules_and_caregiver(client: AsyncClient, db_session: AsyncSession) -> None:
    _c, patient, headers = await _clinic(db_session)
    epley = await _ex(db_session, "Self-Epley manoeuvre (pillows, edge of bed)", side=True)
    plain = await _ex(db_session, "Heel raise")
    care = await _ex(db_session, "Assisted standing (caregiver)", "CAREGIVER")

    r = await client.post(
        f"{API}/prescriptions", headers=headers,
        json={"patient_id": str(patient), "items": [{"exercise_id": str(epley)}]},
    )
    assert r.status_code == 422 and "affected side" in r.text

    r = await client.post(
        f"{API}/prescriptions", headers=headers,
        json={"patient_id": str(patient), "items": [{"exercise_id": str(epley), "side": "middle"}]},
    )
    assert r.status_code == 422

    r = await client.post(
        f"{API}/prescriptions", headers=headers,
        json={"patient_id": str(patient), "items": [
            {"exercise_id": str(epley), "side": "right"},
            {"exercise_id": str(plain), "side": "left"},
            {"exercise_id": str(care)},
        ]},
    )
    assert r.status_code == 201, r.text
    items = {i["exercise_id"]: i for i in r.json()["data"]["items"]}
    assert items[str(epley)]["side"] == "right"
    assert items[str(plain)]["side"] is None
    stored = await db_session.scalar(
        select(PrescriptionItem.side).where(PrescriptionItem.exercise_id == plain)
    )
    assert stored is None

    rx_id = r.json()["data"]["id"]
    r = await client.patch(
        f"{API}/prescriptions/{rx_id}", headers=headers,
        json={"items": [{"exercise_id": str(epley), "side": "left"}]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["items"][0]["side"] == "left"


# ------------------------------------------------------------------ PDF


def _item(**kw) -> RxItem:
    base = dict(title="Self-Epley manoeuvre", body_part="Vestibular", instructions="Sit on the bed.",
                sets=1, reps=3, hold=30, frequency="Daily", note=None, image_url=None)
    base.update(kw)
    return RxItem(**base)


async def test_pdf_side_caregiver_and_stop_pain_line() -> None:
    doc = RxDoc(
        rx_id=str(uuid.uuid4()), clinic_name="Grove Physio", physio_name="Asha Rao", patient_name="Ravi Kumar",
        patient_phone=None, patient_dob=None, prescribed_on=None, physio_notes=None,
        items=[
            _item(side="left"),
            _item(title="Assisted standing", rx_mode="CAREGIVER"),
            _item(title="Heel raise"),
        ],
    )
    out = build_prescription_html(doc)
    assert out.count("Left side") == 1
    assert out.count("Caregiver-assisted") == 1
    assert SAFETY_NOTE == (
        "Stop and contact your physiotherapist if you feel sharp pain, dizziness, chest pain or numbness."
    )
    assert SAFETY_NOTE in out
    # Only the brief description prints.
    assert out.count("Sit on the bed.") == 3


# ------------------------------------------------------------------ Migration B (EL-D-016 / EL-D-017)

DESC = ROOT / "alembic" / "data" / "el_descriptions_20nov.py"


async def test_migration_b_data_qa() -> None:
    import re

    b = _load(DESC, "el_desc")
    a = _load(DATA, "el_data3")
    mode = {r[0]: r[5] for r in a.NEW}
    global_ids = {r[0] for r in a.PROD} | set(mode)
    ids = [r[0] for r in b.DESCRIPTIONS]
    assert len(ids) == len(set(ids)) == 2863 and set(ids) <= global_ids
    for ex_id, text, _old in b.DESCRIPTIONS:
        n = len(re.findall(r"[A-Za-z0-9'’-]+", text))
        assert 0 < n <= 30, (ex_id, n)
        assert "prescribed" not in text.lower()
        if mode.get(ex_id, "PATIENT") == "PATIENT":
            assert not re.search(r"\bthe therapist\b", text, re.I), ex_id
    assert len(b.HIDDEN) == 73 and set(b.HIDDEN) <= {r[0] for r in a.PROD}
    assert b.TITLE_FIX[1] == "Neck side-bend isometric (right)"
    assert len(b.BLOCKED) == 2 and {r[1] for r in a.NEW if r[0] in b.BLOCKED} == {
        "RES-THO-01340-v1", "RES-THO-01341-v1"}
    # every SR24 / Kapalbhati row is BLOCKED already in revision A
    assert next(r[5] for r in a.NEW if r[1] == "MBP-THO-01655-v1") == "BLOCKED"


async def test_hidden_not_listed_searched_counted_or_prescribed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_structure(db_session)
    _c, patient, headers = await _clinic(db_session)
    tag = uuid.uuid4().hex[:5]
    shown = await _ex(db_session, f"Prone press-up {tag}")
    hidden = await _ex(db_session, f"Prone press-up {tag} (seated)", "HIDDEN")
    cid = st.structure_id("category", "Range of motion")
    for ex in (shown, hidden):
        await db_session.execute(exercise_category_links.insert().values(exercise_id=ex, category_id=cid))
    await db_session.commit()

    r = await client.get(f"{API}/exercises", headers=headers, params={"search": tag, "page_size": 50})
    assert [e["id"] for e in r.json()["data"]] == [str(shown)]
    r = await client.get(f"{API}/exercises/categories", headers=headers)
    rom = next(v for g in r.json()["data"] if g["key"] == "category" for v in g["values"] if v["id"] == str(cid))
    assert rom["count"] == 1
    r = await client.post(
        f"{API}/prescriptions", headers=headers,
        json={"patient_id": str(patient), "items": [{"exercise_id": str(hidden)}]},
    )
    assert r.status_code == 422 and "no longer offered" in r.text
    # still readable by id (old prescriptions and templates point at it)
    r = await client.get(f"{API}/exercises/{hidden}", headers=headers)
    assert r.status_code == 200 and r.json()["data"]["rx_mode"] == "HIDDEN"
