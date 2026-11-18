"""Founders' answers of 7 Nov 2026 (S-D-031 to S-D-035).

- DASS-21 retired for new links, past results kept (F1 follow-up).
- Pilot consent text in force (F6 = 6B).
- Sent links tracker with status only (F3 = enhanced 3A).
- Priority review until a provider opens the risk result (F4 = 4A).
- Links stop when the clinic's screening product is not enabled.

Every write is checked in the database.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.enums.product import EntitlementStatus
from app.models.product import WorkspaceProduct
from app.models.psychosocial import (
    PsychosocialAssignment,
    PsychosocialConsent,
    PsychosocialSchedule,
    PsychosocialSession,
    PsychosocialSessionReview,
)
from app.screening import registry
from app.screening.consent import CONSENT_PARAGRAPHS, CONSENT_TEXT_VERSION
from app.services.psychosocial import utcnow
from app.services.psychosocial_schedule import schedule_state
from tests.screening.conftest import API, PRODUCT, make_patient
from tests.screening.test_api import answer, answer_all, assign, code_of, consent, submit, token_of

pytestmark = pytest.mark.asyncio

PHQ9_RISK = [0, 0, 0, 0, 0, 0, 0, 0, 1]  # total 1, item 9 above zero
PHQ9_CALM = [1, 1, 0, 0, 0, 0, 0, 0, 0]


async def count(db, model, *where) -> int:
    return await db.scalar(select(func.count()).select_from(model).where(*where)) or 0


# ---------------------------------------------------------------------------
# DASS-21 retired (S-D-031)
# ---------------------------------------------------------------------------
async def test_dass21_cannot_be_sent_and_is_not_offered(client, db_session, env, therapist_auth_headers, auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    for instruments in (["dass21"], ["phq9", "dass21"]):
        res = await assign(client, therapist_auth_headers, patient.id, instruments)
        assert res.status_code == 422, res.text
        assert code_of(res) == "INSTRUMENT_RETIRED"
    assert await count(db_session, PsychosocialAssignment, PsychosocialAssignment.patient_id == patient.id) == 0

    listed = await client.get(f"{API}/psychosocial/instruments", headers=therapist_auth_headers)
    assert [i["id"] for i in listed.json()["data"]] == ["phq9", "gad7"]

    res = await client.put(
        f"{API}/psychosocial/settings/dass21", json={"default_repeat_weeks": 4}, headers=auth_headers
    )
    assert res.status_code == 422 and code_of(res) == "INSTRUMENT_RETIRED"

    # PHQ-9 + GAD-7 still go out.
    ok = await assign(client, therapist_auth_headers, patient.id, ["phq9", "gad7"])
    assert ok.status_code == 201, ok.text


def test_retired_schedule_is_never_due():
    now = utcnow()
    common = dict(started_at=now - timedelta(days=90), interval_days=28, last_completed_at=None, open_link=False, now=now)
    assert schedule_state(**common, consent_withdrawn=False, retired=True) == ("retired", None)
    # Withdrawal still wins.
    assert schedule_state(**common, consent_withdrawn=True, retired=True) == ("consent_withdrawn", None)
    assert schedule_state(**common, consent_withdrawn=False)[0] == "due"


async def test_old_dass21_repeat_shows_retired_and_leaves_the_due_list(
    client, db_session, env, therapist_auth_headers, monkeypatch
):
    patient = await make_patient(db_session, env["clinic"].id)
    db_session.add(
        PsychosocialSchedule(
            id=uuid.uuid4(),
            clinic_id=env["clinic"].id,
            patient_id=patient.id,
            instrument_id="dass21",
            interval_days=28,
            created_by=env["therapist"].id,
        )
    )
    await db_session.commit()

    res = await client.get(f"{API}/patients/{patient.id}/psychosocial/schedules", headers=therapist_auth_headers)
    assert [s["state"] for s in res.json()["data"]] == ["retired"]
    due = await client.get(f"{API}/psychosocial/due", headers=therapist_auth_headers)
    assert str(patient.id) not in {d["patient_id"] for d in due.json()["data"]}

    # Same row is due when DASS-21 is not retired: the filter is the retirement.
    monkeypatch.setattr(registry, "RETIRED", frozenset())
    due = await client.get(f"{API}/psychosocial/due", headers=therapist_auth_headers)
    assert str(patient.id) in {d["patient_id"] for d in due.json()["data"]}


# ---------------------------------------------------------------------------
# pilot consent text (F6 = 6B)
# ---------------------------------------------------------------------------
async def test_pilot_consent_text_and_old_consent_asked_again(client, db_session, env, therapist_auth_headers):
    assert CONSENT_TEXT_VERSION == "2026-11-07.pilot1"
    text = " ".join(CONSENT_PARAGRAPHS)
    assert "physiotherapist" not in text.lower()
    assert "Administrative staff cannot see your answers or scores." in text

    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    db_session.add(
        PsychosocialConsent(
            id=uuid.uuid4(),
            clinic_id=env["clinic"].id,
            patient_id=patient.id,
            status="granted",
            text_version="2026-10-20.draft1",
            recorded_at=utcnow(),
        )
    )
    await db_session.commit()

    opened = (await client.get(f"{API}/screener/{token}")).json()["data"]
    assert opened["consent"]["required"] is True
    assert opened["consent"]["text_version"] == CONSENT_TEXT_VERSION
    assert opened["consent"]["paragraphs"] == list(CONSENT_PARAGRAPHS)
    blocked = await answer(client, token, "phq9", "phq9_1", 0)
    assert blocked.status_code == 403 and code_of(blocked) == "CONSENT_REQUIRED"

    await consent(client, token)
    latest = await db_session.scalar(
        select(PsychosocialConsent)
        .where(PsychosocialConsent.patient_id == patient.id)
        .order_by(PsychosocialConsent.recorded_at.desc())
        .limit(1)
    )
    assert (latest.status, latest.text_version) == ("granted", CONSENT_TEXT_VERSION)


# ---------------------------------------------------------------------------
# screening product not enabled (S-D-034)
# ---------------------------------------------------------------------------
async def _set_product(db, clinic_id, status: EntitlementStatus) -> None:
    await db.execute(
        update(WorkspaceProduct)
        .where(WorkspaceProduct.clinic_id == clinic_id, WorkspaceProduct.product_id == PRODUCT)
        .values(status=status)
    )
    await db.commit()


async def test_links_stop_when_screening_is_not_enabled(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    await consent(client, token)
    clinic_id = env["clinic"].id
    try:
        await _set_product(db_session, clinic_id, EntitlementStatus.DISABLED)
        for res in (
            await client.get(f"{API}/screener/{token}"),
            await answer(client, token, "phq9", "phq9_1", 3),
            await submit(client, token, "phq9"),
            await client.post(f"{API}/screener/{token}/withdraw"),
        ):
            assert res.status_code == 403, res.text
            assert code_of(res) == "SCREENING_UNAVAILABLE"
        session = await db_session.scalar(
            select(PsychosocialSession).where(PsychosocialSession.patient_id == patient.id)
        )
        await db_session.refresh(session)
        assert session.responses == {} and session.status == "pending"
    finally:
        await _set_product(db_session, clinic_id, EntitlementStatus.ENABLED)

    assert (await answer(client, token, "phq9", "phq9_1", 3)).status_code == 200


async def test_links_stop_when_screening_was_never_installed(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    clinic_id = env["clinic"].id
    row = await db_session.scalar(
        select(WorkspaceProduct).where(WorkspaceProduct.clinic_id == clinic_id, WorkspaceProduct.product_id == PRODUCT)
    )
    keep = dict(product_id=row.product_id, status=row.status, source=row.source)
    await db_session.delete(row)
    await db_session.commit()
    try:
        res = await client.get(f"{API}/screener/{token}")
        assert res.status_code == 403 and code_of(res) == "SCREENING_UNAVAILABLE"
    finally:
        db_session.add(WorkspaceProduct(clinic_id=clinic_id, **keep))
        await db_session.commit()
    assert (await client.get(f"{API}/screener/{token}")).status_code == 200


# ---------------------------------------------------------------------------
# priority review (F4 = 4A)
# ---------------------------------------------------------------------------
async def priority_ids(client, headers) -> list[str]:
    res = await client.get(f"{API}/psychosocial/priority", headers=headers)
    assert res.status_code == 200, res.text
    return [row["session_id"] for row in res.json()["data"]]


async def only_session(db, patient_id) -> PsychosocialSession:
    session = await db.scalar(select(PsychosocialSession).where(PsychosocialSession.patient_id == patient_id))
    await db.refresh(session)
    return session


async def test_risk_result_stays_pinned_until_a_provider_opens_it(client, db_session, env, therapist_auth_headers):
    risky = await make_patient(db_session, env["clinic"].id, first="Kabir")
    calm = await make_patient(db_session, env["clinic"].id, first="Meera")
    for patient, values in ((risky, PHQ9_RISK), (calm, PHQ9_CALM)):
        token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
        await consent(client, token)
        await answer_all(client, token, "phq9", values)
        assert (await submit(client, token, "phq9")).status_code == 200
    risk_session = await only_session(db_session, risky.id)
    calm_session = await only_session(db_session, calm.id)

    res = await client.get(f"{API}/psychosocial/priority", headers=therapist_auth_headers)
    rows = {r["session_id"]: r for r in res.json()["data"]}
    assert str(risk_session.id) in rows and str(calm_session.id) not in rows
    row = rows[str(risk_session.id)]
    assert set(row) == {"session_id", "patient_id", "patient_name", "short_name", "status", "activity_at"}
    assert (row["patient_name"].split()[0], row["short_name"], row["status"]) == ("Kabir", "PHQ-9", "completed")

    # Opening the calm result records nothing.
    await client.get(f"{API}/psychosocial/sessions/{calm_session.id}", headers=therapist_auth_headers)
    assert await count(db_session, PsychosocialSessionReview, PsychosocialSessionReview.session_id == calm_session.id) == 0

    opened = await client.get(f"{API}/psychosocial/sessions/{risk_session.id}", headers=therapist_auth_headers)
    assert opened.status_code == 200
    assert str(risk_session.id) not in await priority_ids(client, therapist_auth_headers)
    review = await db_session.scalar(
        select(PsychosocialSessionReview).where(PsychosocialSessionReview.session_id == risk_session.id)
    )
    assert review is not None and review.reviewed_by == env["therapist"].id

    # A second look adds no row.
    await client.get(f"{API}/psychosocial/sessions/{risk_session.id}", headers=therapist_auth_headers)
    assert await count(db_session, PsychosocialSessionReview, PsychosocialSessionReview.session_id == risk_session.id) == 1


async def test_admin_cannot_read_the_priority_list(client, env, auth_headers):
    res = await client.get(f"{API}/psychosocial/priority", headers=auth_headers)
    assert res.status_code == 403


async def test_unsubmitted_risk_answer_is_pinned_and_again_after_submit(
    client, db_session, env, therapist_auth_headers
):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    await consent(client, token)
    await answer_all(client, token, "phq9", PHQ9_RISK)  # answered, not submitted
    session = await only_session(db_session, patient.id)
    assert session.status == "in_progress"
    assert str(session.id) in await priority_ids(client, therapist_auth_headers)

    await client.get(f"{API}/psychosocial/sessions/{session.id}", headers=therapist_auth_headers)
    assert str(session.id) not in await priority_ids(client, therapist_auth_headers)

    # Submitted later: the result itself has not been opened yet.
    assert (await submit(client, token, "phq9")).status_code == 200
    assert str(session.id) in await priority_ids(client, therapist_auth_headers)
    await client.get(f"{API}/psychosocial/sessions/{session.id}", headers=therapist_auth_headers)
    assert str(session.id) not in await priority_ids(client, therapist_auth_headers)


async def test_risk_answer_then_withdrawal_is_still_pinned(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    await consent(client, token)
    await answer_all(client, token, "phq9", PHQ9_RISK)
    assert (await client.post(f"{API}/screener/{token}/withdraw")).status_code == 200
    session = await only_session(db_session, patient.id)
    assert session.status == "cancelled"
    rows = (await client.get(f"{API}/psychosocial/priority", headers=therapist_auth_headers)).json()["data"]
    assert {"session_id": str(session.id), "status": "cancelled"}.items() <= next(
        r for r in rows if r["session_id"] == str(session.id)
    ).items()


async def test_deletion_removes_review_marks(client, db_session, env, therapist_auth_headers, auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    await consent(client, token)
    await answer_all(client, token, "phq9", PHQ9_RISK)
    await submit(client, token, "phq9")
    session = await only_session(db_session, patient.id)
    await client.get(f"{API}/psychosocial/sessions/{session.id}", headers=therapist_auth_headers)
    assert await count(db_session, PsychosocialSessionReview, PsychosocialSessionReview.patient_id == patient.id) == 1

    res = await client.post(
        f"{API}/patients/{patient.id}/psychosocial/data/delete", json={"confirm": "DELETE"}, headers=auth_headers
    )
    assert res.status_code == 200, res.text
    assert await count(db_session, PsychosocialSessionReview, PsychosocialSessionReview.patient_id == patient.id) == 0


# ---------------------------------------------------------------------------
# sent links tracker (F3 = enhanced 3A)
# ---------------------------------------------------------------------------
TRACKER_KEYS = {
    "id", "patient_id", "patient_name", "screeners", "status", "sent_at", "expires_at", "sent_by_name", "can_cancel",
}


async def tracker(client, headers, status=None) -> dict[str, dict]:
    params = {"page_size": 100}
    if status:
        params["status"] = status
    res = await client.get(f"{API}/psychosocial/assignments", params=params, headers=headers)
    assert res.status_code == 200, res.text
    return {row["id"]: row for row in res.json()["data"]}


async def test_admin_tracker_shows_status_and_never_clinical_data(
    client, db_session, env, therapist_auth_headers, auth_headers
):
    clinic_id = env["clinic"].id
    pending_p = await make_patient(db_session, clinic_id, first="Anil")
    started_p = await make_patient(db_session, clinic_id, first="Ritu")
    done_p = await make_patient(db_session, clinic_id, first="Kabir")
    expired_p = await make_patient(db_session, clinic_id, first="Sita")

    def aid(res) -> str:
        return res.json()["data"]["assignment"]["id"]

    pending_id = aid(await assign(client, auth_headers, pending_p.id, ["phq9", "gad7"]))
    started_res = await assign(client, therapist_auth_headers, started_p.id, ["phq9"])
    started_id, started_token = aid(started_res), token_of(started_res)
    done_res = await assign(client, therapist_auth_headers, done_p.id, ["phq9"])
    done_id, done_token = aid(done_res), token_of(done_res)
    expired_id = aid(await assign(client, therapist_auth_headers, expired_p.id, ["gad7"]))

    await consent(client, started_token)
    await answer(client, started_token, "phq9", "phq9_1", 2)
    await consent(client, done_token)
    await answer_all(client, done_token, "phq9", PHQ9_RISK)
    await submit(client, done_token, "phq9")
    await db_session.execute(
        update(PsychosocialAssignment)
        .where(PsychosocialAssignment.id == uuid.UUID(expired_id))
        .values(expires_at=utcnow() - timedelta(hours=1))
    )
    await db_session.commit()

    rows = await tracker(client, auth_headers)
    for row in rows.values():
        assert set(row) == TRACKER_KEYS
    assert rows[pending_id]["status"] == "pending" and rows[pending_id]["can_cancel"] is True
    assert rows[pending_id]["screeners"] == ["PHQ-9", "GAD-7"]
    assert rows[started_id]["status"] == "pending" and rows[started_id]["can_cancel"] is False
    # The risk answer is invisible here: just "completed".
    assert rows[done_id]["status"] == "completed" and rows[done_id]["can_cancel"] is False
    assert rows[expired_id]["status"] == "expired"
    assert rows[done_id]["sent_by_name"]

    assert set(await tracker(client, auth_headers, "expired")) & {pending_id, started_id, done_id, expired_id} == {expired_id}
    assert set(await tracker(client, auth_headers, "pending")) & {pending_id, started_id, done_id, expired_id} == {
        pending_id,
        started_id,
    }
    assert done_id in await tracker(client, auth_headers, "completed")

    # Admin cancels a link nobody opened (S-L-007).
    res = await client.post(f"{API}/psychosocial/assignments/{pending_id}/cancel", headers=auth_headers)
    assert res.status_code == 200, res.text
    row = await db_session.get(PsychosocialAssignment, uuid.UUID(pending_id))
    await db_session.refresh(row)
    assert row.status == "cancelled"
    assert (await tracker(client, auth_headers))[pending_id]["status"] == "cancelled"


async def test_tracker_needs_send_permission(client, db_session, env, therapist_auth_headers):
    from tests.screening.conftest import set_overrides

    await set_overrides(db_session, env["clinic"].id, env["therapist"].id, {"screening.view": "own"})
    res = await client.get(f"{API}/psychosocial/assignments", headers=therapist_auth_headers)
    assert res.status_code == 403
    bad = await client.get(f"{API}/psychosocial/assignments", params={"status": "flagged"}, headers=therapist_auth_headers)
    assert bad.status_code in (403, 422)
