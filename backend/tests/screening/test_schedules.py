"""Repeat schedules and the Due list (SRS 4.1.1 recurring, S-D-026)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.audit import AuditLog
from app.models.patient import Patient
from app.models.psychosocial import PsychosocialAssignment, PsychosocialSchedule
from app.services.psychosocial import utcnow
from app.services.psychosocial_schedule import schedule_state
from tests.screening.conftest import API, entitle, make_patient, set_overrides
from tests.screening.test_api import code_of, token_of
from tests.screening.test_trend_report import insert_completed

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# pure state
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "kwargs,expected",
    [
        # Withdrawn wins over everything.
        (dict(last=NOW - timedelta(days=60), open_link=True, withdrawn=True), ("consent_withdrawn", None)),
        # An open link means we are waiting for the patient.
        (dict(last=NOW - timedelta(days=60), open_link=True, withdrawn=False), ("waiting", None)),
        # Last result + interval reached: due. Exactly on the day counts as due.
        (dict(last=NOW - timedelta(days=28), open_link=False, withdrawn=False), ("due", NOW)),
        (dict(last=NOW - timedelta(days=40), open_link=False, withdrawn=False), ("due", NOW - timedelta(days=12))),
        # Not yet.
        (dict(last=NOW - timedelta(days=27), open_link=False, withdrawn=False), ("upcoming", NOW + timedelta(days=1))),
        # Never answered and no open link (cancelled or expired): due from the start date.
        (dict(last=None, open_link=False, withdrawn=False), ("due", NOW - timedelta(days=3))),
    ],
)
def test_schedule_state(kwargs, expected):
    state = schedule_state(
        started_at=NOW - timedelta(days=3),
        interval_days=28,
        last_completed_at=kwargs["last"],
        open_link=kwargs["open_link"],
        consent_withdrawn=kwargs["withdrawn"],
        now=NOW,
    )
    assert state == expected


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
async def send(client, headers, patient_id, instruments, weeks=None, days=7):
    body = {"instruments": instruments, "expires_in_days": days}
    if weeks is not None:
        body["repeat_every_weeks"] = weeks
    return await client.post(f"{API}/patients/{patient_id}/psychosocial/sessions", json=body, headers=headers)


async def schedules_of(client, headers, patient_id):
    res = await client.get(f"{API}/patients/{patient_id}/psychosocial/schedules", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()["data"]


async def due_ids(client, headers):
    res = await client.get(f"{API}/psychosocial/due", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()["data"]


async def add_schedule(db, clinic_id, patient_id, instrument_id, interval_days, created_at):
    schedule = PsychosocialSchedule(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        instrument_id=instrument_id,
        interval_days=interval_days,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(schedule)
    await db.commit()
    return schedule.id


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
async def test_send_with_repeat_creates_one_schedule_per_screener(
    client, db_session, env, therapist_auth_headers
):
    patient = await make_patient(db_session, env["clinic"].id)
    assert (await send(client, therapist_auth_headers, patient.id, ["phq9"], weeks=0)).status_code == 422
    assert (await send(client, therapist_auth_headers, patient.id, ["phq9"], weeks=53)).status_code == 422
    assert (await send(client, therapist_auth_headers, patient.id, ["phq9"])).status_code == 201
    assert await schedules_of(client, therapist_auth_headers, patient.id) == []

    res = await send(client, therapist_auth_headers, patient.id, ["phq9", "gad7"], weeks=4)
    assert res.status_code == 201, res.text
    rows = await schedules_of(client, therapist_auth_headers, patient.id)
    assert [(r["instrument_id"], r["interval_days"], r["state"]) for r in rows] == [
        ("phq9", 28, "waiting"),
        ("gad7", 28, "waiting"),
    ]
    assert rows[0]["created_by_name"] and rows[0]["next_due_at"] is None

    # Sending again with another interval changes it, still one active row each.
    assert (await send(client, therapist_auth_headers, patient.id, ["phq9"], weeks=8)).status_code == 201
    active = (
        await db_session.scalars(
            select(PsychosocialSchedule).where(
                PsychosocialSchedule.patient_id == patient.id, PsychosocialSchedule.stopped_at.is_(None)
            )
        )
    ).all()
    assert sorted((s.instrument_id, s.interval_days) for s in active) == [("gad7", 28), ("phq9", 56)]

    events = (
        await db_session.scalars(
            select(AuditLog).where(AuditLog.action == "psychosocial.schedule_set", AuditLog.entity_id == patient.id)
        )
    ).all()
    assert [e.details["interval_days"] for e in events] == [28, 56]
    for e in events:
        for word in ("score", "band", "risk", "referral"):
            assert word not in str(e.details).lower()


async def test_due_after_interval_and_upcoming_before(client, db_session, env, therapist_auth_headers):
    clinic_id, therapist_id = env["clinic"].id, env["therapist"].id
    overdue = await make_patient(db_session, clinic_id, first="Overdue")
    soon = await make_patient(db_session, clinic_id, first="Soon")
    now = utcnow()
    for patient, days_ago in ((overdue, 40), (soon, 10)):
        await insert_completed(db_session, clinic_id, patient.id, therapist_id, "phq9", 6, now - timedelta(days=days_ago))
        await add_schedule(db_session, clinic_id, patient.id, "phq9", 28, now - timedelta(days=days_ago + 1))

    [over_row] = await schedules_of(client, therapist_auth_headers, overdue.id)
    assert over_row["state"] == "due"
    [soon_row] = await schedules_of(client, therapist_auth_headers, soon.id)
    assert soon_row["state"] == "upcoming"
    next_due = datetime.fromisoformat(soon_row["next_due_at"])
    assert abs(next_due - (now + timedelta(days=18))) < timedelta(seconds=5)

    due = await due_ids(client, therapist_auth_headers)
    mine = [d for d in due if d["patient_id"] in {str(overdue.id), str(soon.id)}]
    assert [(d["patient_name"], d["instrument_id"]) for d in mine] == [(f"Overdue {overdue.last_name}", "phq9")]


async def test_cancelled_or_expired_link_makes_it_due_and_a_new_link_waits(
    client, db_session, env, therapist_auth_headers
):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await send(client, therapist_auth_headers, patient.id, ["gad7"], weeks=4)
    assignment_id = res.json()["data"]["assignment"]["id"]
    assert [d for d in await due_ids(client, therapist_auth_headers) if d["patient_id"] == str(patient.id)] == []

    cancelled = await client.post(
        f"{API}/psychosocial/assignments/{assignment_id}/cancel", headers=therapist_auth_headers
    )
    assert cancelled.status_code == 200
    [row] = await schedules_of(client, therapist_auth_headers, patient.id)
    assert row["state"] == "due"
    assert str(patient.id) in {d["patient_id"] for d in await due_ids(client, therapist_auth_headers)}

    # Sending the due screener moves it back to waiting.
    again = await send(client, therapist_auth_headers, patient.id, ["gad7"])
    [row] = await schedules_of(client, therapist_auth_headers, patient.id)
    assert row["state"] == "waiting"

    # An expired link counts as no link.
    await db_session.execute(
        update(PsychosocialAssignment)
        .where(PsychosocialAssignment.id == uuid.UUID(again.json()["data"]["assignment"]["id"]))
        .values(expires_at=utcnow() - timedelta(minutes=1))
    )
    await db_session.commit()
    [row] = await schedules_of(client, therapist_auth_headers, patient.id)
    assert row["state"] == "due"


async def test_withdrawn_and_removed_patients_are_never_due(client, db_session, env, therapist_auth_headers):
    withdrawn = await make_patient(db_session, env["clinic"].id)
    token = token_of(await send(client, therapist_auth_headers, withdrawn.id, ["phq9"], weeks=2))
    assert (await client.post(f"{API}/screener/{token}/withdraw")).status_code == 200
    [row] = await schedules_of(client, therapist_auth_headers, withdrawn.id)
    assert row["state"] == "consent_withdrawn" and row["next_due_at"] is None

    removed = await make_patient(db_session, env["clinic"].id)
    res = await send(client, therapist_auth_headers, removed.id, ["phq9"], weeks=2)
    await client.post(
        f"{API}/psychosocial/assignments/{res.json()['data']['assignment']['id']}/cancel",
        headers=therapist_auth_headers,
    )
    assert str(removed.id) in {d["patient_id"] for d in await due_ids(client, therapist_auth_headers)}
    await db_session.execute(update(Patient).where(Patient.id == removed.id).values(deleted_at=utcnow()))
    await db_session.commit()

    ids = {d["patient_id"] for d in await due_ids(client, therapist_auth_headers)}
    assert str(withdrawn.id) not in ids and str(removed.id) not in ids


async def test_stop_schedule(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await send(client, therapist_auth_headers, patient.id, ["phq9"], weeks=4)
    await client.post(
        f"{API}/psychosocial/assignments/{res.json()['data']['assignment']['id']}/cancel",
        headers=therapist_auth_headers,
    )
    [row] = await schedules_of(client, therapist_auth_headers, patient.id)

    stopped = await client.post(f"{API}/psychosocial/schedules/{row['id']}/stop", headers=therapist_auth_headers)
    assert stopped.status_code == 200, stopped.text
    assert await schedules_of(client, therapist_auth_headers, patient.id) == []
    assert str(patient.id) not in {d["patient_id"] for d in await due_ids(client, therapist_auth_headers)}
    db_row = await db_session.get(PsychosocialSchedule, uuid.UUID(row["id"]))
    await db_session.refresh(db_row)
    assert db_row.stopped_at is not None and db_row.stopped_by == env["therapist"].id

    again = await client.post(f"{API}/psychosocial/schedules/{row['id']}/stop", headers=therapist_auth_headers)
    assert again.status_code == 409 and code_of(again) == "SCHEDULE_STOPPED"
    missing = await client.post(f"{API}/psychosocial/schedules/{uuid.uuid4()}/stop", headers=therapist_auth_headers)
    assert missing.status_code == 404

    # A new repeat can start after a stop (the unique index covers active rows only).
    assert (await send(client, therapist_auth_headers, patient.id, ["phq9"], weeks=2)).status_code == 201
    assert len(await schedules_of(client, therapist_auth_headers, patient.id)) == 1


async def test_access_and_clinic_isolation(client, db_session, env, auth_headers, therapist_auth_headers):
    from app.models.user import User

    patient = await make_patient(db_session, env["clinic"].id)
    res = await send(client, therapist_auth_headers, patient.id, ["phq9"], weeks=4)
    await client.post(
        f"{API}/psychosocial/assignments/{res.json()['data']['assignment']['id']}/cancel",
        headers=therapist_auth_headers,
    )
    [row] = await schedules_of(client, therapist_auth_headers, patient.id)

    # The admin can send links, so the admin sees what is due (no results in it).
    assert str(patient.id) in {d["patient_id"] for d in await due_ids(client, auth_headers)}

    # Without screening.assign there is no Due list.
    await set_overrides(db_session, env["clinic"].id, env["therapist"].id, {"screening.view": "own"})
    assert (await client.get(f"{API}/psychosocial/due", headers=therapist_auth_headers)).status_code == 403
    assert (
        await client.post(f"{API}/psychosocial/schedules/{row['id']}/stop", headers=therapist_auth_headers)
    ).status_code == 403

    email = f"sch_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Other", "email": email, "password": "password123", "first_name": "O", "last_name": "C"},
    )
    other_headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    other = await db_session.scalar(select(User).where(User.email == email))
    await entitle(db_session, other.clinic_id)
    assert await due_ids(client, other_headers) == []
    assert (
        await client.get(f"{API}/patients/{patient.id}/psychosocial/schedules", headers=other_headers)
    ).status_code == 404
    assert (
        await client.post(f"{API}/psychosocial/schedules/{row['id']}/stop", headers=other_headers)
    ).status_code == 404
    db_row = await db_session.get(PsychosocialSchedule, uuid.UUID(row["id"]))
    await db_session.refresh(db_row)
    assert db_row.stopped_at is None
