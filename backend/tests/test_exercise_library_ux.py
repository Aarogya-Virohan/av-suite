"""Exercise Library UX batch (founders' feedback, 23 Oct 2026).

- Exercise list is ordered head to toe, and offset paging is stable (no
  duplicates, no gaps across pages).
- GET /exercises/body-parts: every visible body part, head to toe, with
  counts; other clinics' exercises are not counted; empty body part is
  "Other", and filtering by "Other" returns those exercises.
- GET /prescriptions/note-suggestions: phrases from this clinic's own notes,
  ranked by use, OWN scope sees only own prescriptions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.prescription import Prescription, PrescriptionItem
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission
from app.services.body_regions import OTHER_RANK, UNKNOWN_RANK, region_rank
from app.services.prescription_suggestions import _NOTE_SPLIT, rank_phrases

pytestmark = pytest.mark.asyncio
API = settings.API_V1_PREFIX


async def _clinic(db: AsyncSession, role: UserRole = UserRole.ADMIN):
    clinic = Clinic(name=f"EL Clinic {uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(), clinic_id=None, email=f"el-{uuid.uuid4().hex[:8]}@avtest.com",
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
    return clinic, user, {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------ unit


async def test_region_rank_head_to_toe() -> None:
    order = ["Neck", "Shoulder", "Elbow", "Wrist", "Upper Back", "Lower Back", "Hip", "Knee", "Ankle", "Foot"]
    ranks = [region_rank(p) for p in order]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks)
    assert region_rank("neck") == region_rank("Cervical") == region_rank("  NECK ")
    assert region_rank("Something new") == UNKNOWN_RANK
    assert region_rank("Other") == region_rank(None) == region_rank("") == OTHER_RANK
    assert UNKNOWN_RANK < OTHER_RANK


async def test_rank_phrases_split_group_and_order() -> None:
    t0 = datetime(2026, 10, 20, tzinfo=timezone.utc)
    rows = [
        ("avoid in case of pain, measure BP before exercise", t0),
        ("Avoid in case of pain", t0 + timedelta(hours=1)),
        ("Measure BP before exercise.;  slow and controlled", t0 + timedelta(hours=2)),
        ("ok", t0),  # too short
        (None, t0),
    ]
    out = rank_phrases(rows, _NOTE_SPLIT)
    # Both seen twice; "Measure BP..." is more recent, so first.
    assert out[:2] == ["Measure BP before exercise", "Avoid in case of pain"]
    assert out[2] == "Slow and controlled"
    assert "Ok" not in out and len(out) == 3


# ------------------------------------------------------------------ API


async def test_list_is_head_to_toe_and_paging_is_stable(client: AsyncClient, db_session: AsyncSession) -> None:
    clinic, _user, headers = await _clinic(db_session)
    parts = ["Knee", "Neck", "Ankle", "Shoulder", "Hip", "Zeta Region", None, "Other", "Elbow", "Knee"]
    for i, part in enumerate(parts):
        db_session.add(Exercise(clinic_id=clinic.id, title=f"ex {i:02d}", body_part=part, is_free=True))
    await db_session.commit()

    seen: list[dict] = []
    page = 1
    while True:
        r = await client.get(f"{API}/exercises", params={"page": page, "page_size": 4}, headers=headers)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        seen.extend(data)
        if len(seen) >= r.json()["meta"]["total"] or not data:
            break
        page += 1

    ids = [e["id"] for e in seen]
    assert len(ids) == len(set(ids)) == r.json()["meta"]["total"]
    ranks = [region_rank(e["body_part"]) for e in seen]
    assert ranks == sorted(ranks), [e["body_part"] for e in seen]


async def test_body_parts_endpoint(client: AsyncClient, db_session: AsyncSession) -> None:
    clinic, _user, headers = await _clinic(db_session)
    other_clinic, _u2, _h2 = await _clinic(db_session)
    marker = f"Zz{uuid.uuid4().hex[:4]}"
    db_session.add_all([
        Exercise(clinic_id=clinic.id, title="a", body_part="Knee", is_free=True),
        Exercise(clinic_id=clinic.id, title="b", body_part=marker, is_free=True),
        Exercise(clinic_id=clinic.id, title="c", body_part=marker, is_free=True),
        Exercise(clinic_id=clinic.id, title="no part", body_part=None, is_free=True),
        Exercise(clinic_id=other_clinic.id, title="hidden", body_part=f"{marker}x", is_free=True),
    ])
    await db_session.commit()

    r = await client.get(f"{API}/exercises/body-parts", headers=headers)
    assert r.status_code == 200, r.text
    rows = r.json()["data"]
    names = [row["body_part"] for row in rows]
    counts = {row["body_part"]: row["count"] for row in rows}

    assert counts[marker] == 2
    assert f"{marker}x" not in names  # other clinic
    assert names[-1] == "Other" and counts["Other"] >= 1
    assert [region_rank(n) for n in names] == sorted(region_rank(n) for n in names)
    assert len(names) == len(set(names))

    # Filter by "Other" returns the exercise with no body part.
    r = await client.get(f"{API}/exercises", params={"body_part": "Other", "page_size": 100}, headers=headers)
    titles = {e["title"] for e in r.json()["data"]}
    assert "no part" in titles and "a" not in titles

    # The counts match what the list returns for that body part.
    r = await client.get(f"{API}/exercises", params={"body_part": f"Knee,{marker}", "page_size": 100}, headers=headers)
    got = r.json()["data"]
    assert sum(1 for e in got if e["body_part"] == marker) == 2


async def test_note_suggestions_scope_and_isolation(client: AsyncClient, db_session: AsyncSession) -> None:
    clinic, admin, headers = await _clinic(db_session)
    other_clinic, other_admin, _h = await _clinic(db_session)
    therapist = User(
        id=uuid.uuid4(), clinic_id=clinic.id, email=f"th-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=UserRole.THERAPIST, first_name="T", last_name="One", is_active=True,
    )
    db_session.add(therapist)
    await db_session.flush()
    db_session.add(Membership(user_id=therapist.id, clinic_id=clinic.id, role=UserRole.THERAPIST))
    db_session.add(UserPermission(user_id=therapist.id, clinic_id=clinic.id,
                                  capability_key="prescriptions.view", scope=CapabilityScope.OWN))
    patient = Patient(clinic_id=clinic.id, first_name="P", last_name="One")
    other_patient = Patient(clinic_id=other_clinic.id, first_name="P", last_name="Two")
    ex = Exercise(clinic_id=None, title=f"g {uuid.uuid4().hex[:4]}", body_part="Neck", is_free=True)
    db_session.add_all([patient, other_patient, ex])
    await db_session.flush()

    def rx(clinic_id, physio_id, patient_id, notes, guidance):
        p = Prescription(clinic_id=clinic_id, physio_id=physio_id, patient_id=patient_id, physio_notes=guidance)
        p.items = [PrescriptionItem(exercise_id=ex.id, sets=3, reps=10, hold=0, frequency="Daily", note=n) for n in notes]
        return p

    db_session.add_all([
        rx(clinic.id, admin.id, patient.id, ["Avoid in case of pain, measure BP first", "Avoid in case of pain"],
           "Walk daily. Drink water."),
        rx(clinic.id, therapist.id, patient.id, ["Therapist only phrase"], "Therapist guidance line."),
        rx(other_clinic.id, other_admin.id, other_patient.id, ["Other clinic secret"], "Other clinic guidance."),
    ])
    await db_session.commit()

    r = await client.get(f"{API}/prescriptions/note-suggestions", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["notes"][0] == "Avoid in case of pain"
    assert {"Measure BP first", "Therapist only phrase"} <= set(data["notes"])
    assert "Other clinic secret" not in data["notes"]
    assert {"Walk daily", "Drink water", "Therapist guidance line"} <= set(data["guidance"])
    assert not any("Other clinic" in g for g in data["guidance"])

    token = create_access_token(subject=therapist.id, clinic_id=clinic.id, role=UserRole.THERAPIST.value)
    r = await client.get(f"{API}/prescriptions/note-suggestions",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    own = r.json()["data"]
    assert own["notes"] == ["Therapist only phrase"]
    assert own["guidance"] == ["Therapist guidance line"]
