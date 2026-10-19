"""Tool 03 API: access control, patient flow, immutability, isolation.

Every write is checked in the database, not only by status code.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.psychosocial import (
    PsychosocialAssignment,
    PsychosocialConsent,
    PsychosocialSession,
)
from app.screening import rate_limit
from app.screening.consent import CONSENT_TEXT_VERSION
from app.services.psychosocial import hash_token, utcnow
from tests.screening.conftest import API, entitle, make_patient, set_overrides

pytestmark = pytest.mark.asyncio


def code_of(response) -> str | None:
    body = response.json()
    if isinstance(body.get("detail"), dict):
        return body["detail"].get("code")
    meta = body.get("meta") or {}
    return (meta.get("error") or {}).get("code")


async def assign(client, headers, patient_id, instruments, days=7):
    res = await client.post(
        f"{API}/patients/{patient_id}/psychosocial/sessions",
        json={"instruments": instruments, "expires_in_days": days},
        headers=headers,
    )
    return res


def token_of(res) -> str:
    path = res.json()["data"]["screener_path"]
    assert path.startswith("/screener/")
    return path.rsplit("/", 1)[1]


async def consent(client, token):
    res = await client.post(f"{API}/screener/{token}/consent", json={"text_version": CONSENT_TEXT_VERSION})
    assert res.status_code == 200, res.text


async def answer(client, token, instrument, item, value):
    return await client.post(
        f"{API}/screener/{token}/answers",
        json={"instrument_id": instrument, "item_id": item, "value": value},
    )


async def answer_all(client, token, instrument, values):
    for n, v in enumerate(values, start=1):
        res = await answer(client, token, instrument, f"{instrument}_{n}", v)
        assert res.status_code == 200, res.text


async def submit(client, token, instrument):
    return await client.post(f"{API}/screener/{token}/submit", json={"instrument_id": instrument})


# ---------------------------------------------------------------------------
# access control
# ---------------------------------------------------------------------------
async def test_product_entitlement_required(client: AsyncClient, db_session: AsyncSession):
    email = f"noent_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "No Ent", "email": email, "password": "password123",
              "first_name": "A", "last_name": "B"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    res = await client.get(f"{API}/psychosocial/instruments", headers=headers)
    assert res.status_code == 403
    assert code_of(res) == "PRODUCT_NOT_ENTITLED"


async def test_admin_assigns_but_cannot_read_individual_results(client, db_session, env, auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, auth_headers, patient.id, ["phq9"])
    assert res.status_code == 201, res.text
    listed = await client.get(f"{API}/patients/{patient.id}/psychosocial/sessions", headers=auth_headers)
    assert listed.status_code == 403
    worklist = await client.get(f"{API}/psychosocial/sessions", headers=auth_headers)
    assert worklist.status_code == 403
    summary = await client.get(f"{API}/patients/{patient.id}/psychosocial/summary", headers=auth_headers)
    assert summary.status_code == 403


async def test_therapist_without_grant_is_refused(client, db_session, env, therapist_auth_headers):
    await set_overrides(db_session, env["clinic"].id, env["therapist"].id, {})
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    assert res.status_code == 403


async def test_validation_of_assign_payload(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    for payload in (
        {"instruments": []},
        {"instruments": ["phq9", "phq9"]},
        {"instruments": ["bdi"]},
        {"instruments": ["phq9"], "expires_in_days": 0},
        {"instruments": ["phq9"], "expires_in_days": 31},
    ):
        res = await client.post(
            f"{API}/patients/{patient.id}/psychosocial/sessions", json=payload, headers=therapist_auth_headers
        )
        assert res.status_code == 422, (payload, res.text)
    missing = await assign(client, therapist_auth_headers, uuid.uuid4(), ["phq9"])
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# full patient flow
# ---------------------------------------------------------------------------
async def test_full_flow_phq9_then_gad7(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id, first="Meera")
    res = await assign(client, therapist_auth_headers, patient.id, ["phq9", "gad7"])
    assert res.status_code == 201, res.text
    token = token_of(res)
    assignment_id = uuid.UUID(res.json()["data"]["assignment"]["id"])

    row = await db_session.get(PsychosocialAssignment, assignment_id)
    assert row.token_hash == hash_token(token) and token not in row.token_hash
    assert [s.instrument_id for s in row.sessions] == ["phq9", "gad7"]
    assert all(s.status == "pending" for s in row.sessions)

    opened = await client.get(f"{API}/screener/{token}")
    assert opened.status_code == 200
    body = opened.text
    assert "Meera" not in body and patient.last_name not in body
    assert str(patient.id) not in body
    for s in row.sessions:
        assert str(s.id) not in body
    data = opened.json()["data"]
    assert data["consent"]["required"] is True
    assert data["current_instrument_id"] == "phq9"
    assert [q["instrument"]["id"] for q in data["questionnaires"]] == ["phq9", "gad7"]

    early = await answer(client, token, "phq9", "phq9_1", 1)
    assert early.status_code == 403 and code_of(early) == "CONSENT_REQUIRED"

    await consent(client, token)
    consents = (await db_session.scalars(
        select(PsychosocialConsent).where(PsychosocialConsent.patient_id == patient.id)
    )).all()
    assert [(c.status, c.text_version) for c in consents] == [("granted", CONSENT_TEXT_VERSION)]

    # strict order, retries, no changes
    assert (await answer(client, token, "phq9", "phq9_2", 1)).status_code == 409
    assert (await answer(client, token, "gad7", "gad7_1", 1)).status_code == 409
    first = await answer(client, token, "phq9", "phq9_1", 2)
    assert first.status_code == 200
    assert first.json()["data"]["next_item_id"] == "phq9_2"
    retry = await answer(client, token, "phq9", "phq9_1", 2)
    assert retry.status_code == 200
    changed = await answer(client, token, "phq9", "phq9_1", 0)
    assert changed.status_code == 409 and code_of(changed) == "ANSWER_LOCKED"
    bad = await answer(client, token, "phq9", "phq9_2", 7)
    assert bad.status_code == 422

    incomplete = await submit(client, token, "phq9")
    assert incomplete.status_code == 409 and code_of(incomplete) == "INCOMPLETE"

    # resume: answers are saved server side after each question
    reopened = (await client.get(f"{API}/screener/{token}")).json()["data"]
    assert reopened["questionnaires"][0]["answers"] == {"phq9_1": 2}
    assert reopened["consent"]["required"] is False

    for n, v in enumerate([1, 1, 1, 1, 0, 0, 0, 1], start=2):  # item 9 = 1
        assert (await answer(client, token, "phq9", f"phq9_{n}", v)).status_code == 200
    last = await answer(client, token, "phq9", "phq9_difficulty", 1)
    assert last.json()["data"]["ready_to_submit"] is True

    done = await submit(client, token, "phq9")
    assert done.status_code == 200, done.text
    out = done.json()["data"]
    assert out == {
        "instrument_id": "phq9",
        "assignment_complete": False,
        "next_instrument_id": "gad7",
        "show_referral_message": True,
        "show_support_contacts": True,
    }
    again = await submit(client, token, "phq9")
    assert again.status_code == 200 and again.json()["data"] == out

    await db_session.refresh(row, attribute_names=["sessions"])
    phq = row.sessions[0]
    await db_session.refresh(phq)
    assert phq.status == "completed" and phq.completed_at is not None
    assert phq.result["scales"][0]["score"] == 7  # 2+1+1+1+1+0+0+0+1
    assert phq.result["scales"][0]["band_label"] == "Mild"
    assert phq.referral_flag is True and phq.risk_item_flag is True
    assert phq.instrument_version == "1.0.0"

    after = await answer(client, token, "phq9", "phq9_9", 0)
    assert after.status_code == 409

    await answer_all(client, token, "gad7", [1, 1, 1, 0, 0, 0, 0])
    gad = await submit(client, token, "gad7")
    assert gad.json()["data"]["assignment_complete"] is True
    assert gad.json()["data"]["next_instrument_id"] is None

    closed = await client.get(f"{API}/screener/{token}")
    assert closed.status_code == 409 and code_of(closed) == "ALREADY_COMPLETED"

    # physio review
    listed = await client.get(
        f"{API}/patients/{patient.id}/psychosocial/sessions", headers=therapist_auth_headers
    )
    assert listed.status_code == 200
    a = listed.json()["data"][0]
    assert a["effective_status"] == "completed"
    assert [s["status"] for s in a["sessions"]] == ["completed", "completed"]

    detail = await client.get(f"{API}/psychosocial/sessions/{phq.id}", headers=therapist_auth_headers)
    assert detail.status_code == 200
    d = detail.json()["data"]
    assert d["is_baseline"] is True and d["baseline"] is None
    assert d["responses"][0]["answer_label"] == "More than half the days"
    assert d["responses"][9]["item_id"] == "phq9_difficulty" and d["responses"][9]["scored"] is False
    assert any("item 9" in r for r in d["reasons"])

    logged = await client.post(
        f"{API}/psychosocial/sessions/{phq.id}/referral-actions",
        json={"action": "referred_psychologist", "note": "Discussed in session."},
        headers=therapist_auth_headers,
    )
    assert logged.status_code == 201, logged.text
    gad_id = row.sessions[1].id
    no_flag = await client.post(
        f"{API}/psychosocial/sessions/{gad_id}/referral-actions",
        json={"action": "other"},
        headers=therapist_auth_headers,
    )
    assert no_flag.status_code == 409
    history = await client.get(
        f"{API}/patients/{patient.id}/psychosocial/referral-actions", headers=therapist_auth_headers
    )
    assert [h["action"] for h in history.json()["data"]] == ["referred_psychologist"]

    summary = (await client.get(
        f"{API}/patients/{patient.id}/psychosocial/summary", headers=therapist_auth_headers
    )).json()["data"]
    assert summary["referral_flag"] is True and summary["risk_item_flag"] is True
    assert sorted(s["instrument_id"] for s in summary["latest"]) == ["gad7", "phq9"]

    # audit: right events, and no scores or flags in details
    logs = (await db_session.scalars(
        select(AuditLog).where(AuditLog.action.like("psychosocial.%"))
    )).all()
    mine = [l for l in logs if (l.details or {}).get("patient_id") == str(patient.id)]
    actions = sorted({l.action for l in mine})
    assert actions == sorted({
        "psychosocial.assigned", "psychosocial.consent_granted", "psychosocial.completed",
        "psychosocial.result_viewed", "psychosocial.referral_logged",
    })
    for l in mine:
        blob = str(l.details).lower()
        for word in ("score", "band", "referral_flag", "risk"):
            assert word not in blob


async def test_second_session_shows_baseline(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    ids = []
    for values in ([3] * 9, [1] * 8 + [0]):
        res = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
        token = token_of(res)
        await consent(client, token)
        await answer_all(client, token, "phq9", values)
        assert (await submit(client, token, "phq9")).status_code == 200
        ids.append(res.json()["data"]["assignment"]["sessions"][0]["id"])
    d = (await client.get(f"{API}/psychosocial/sessions/{ids[1]}", headers=therapist_auth_headers)).json()["data"]
    assert d["is_baseline"] is False
    assert d["baseline"]["session_id"] == ids[0]
    assert d["baseline"]["scales"][0]["score"] == 27
    assert d["session"]["scales"][0]["score"] == 8


async def test_dass21_severe_subscale_refers(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["dass21"]))
    await consent(client, token)
    values = [0] * 21
    for n in (2, 4, 7, 9, 15, 19, 20):  # anxiety items
        values[n - 1] = 1
    values[1] = 3  # item 2 -> anxiety raw 9 -> 18 Severe
    await answer_all(client, token, "dass21", values)
    out = (await submit(client, token, "dass21")).json()["data"]
    assert out["show_referral_message"] is True and out["show_support_contacts"] is False
    session = await db_session.scalar(select(PsychosocialSession).where(PsychosocialSession.patient_id == patient.id))
    await db_session.refresh(session)
    anxiety = next(s for s in session.result["scales"] if s["scale_id"] == "anxiety")
    assert (anxiety["raw_sum"], anxiety["score"], anxiety["band_label"]) == (9, 18, "Severe")


async def test_partial_risk_visible_before_submit(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    await consent(client, token)
    await answer_all(client, token, "phq9", [0] * 8 + [2])  # stops before submit
    rows = (await client.get(
        f"{API}/psychosocial/sessions?status=in_progress", headers=therapist_auth_headers
    )).json()["data"]
    mine = [r for r in rows if r["session"]["patient_id"] == str(patient.id)]
    assert len(mine) == 1 and mine[0]["session"]["partial_risk"] is True
    assert mine[0]["session"]["answered_count"] == 9


# ---------------------------------------------------------------------------
# immutability, expiry, cancel, reissue, consent withdrawal
# ---------------------------------------------------------------------------
async def test_completed_session_rejects_db_update(client, db_session, env, therapist_auth_headers):
    if db_session.bind.dialect.name != "postgresql":
        pytest.skip("trigger is Postgres only")
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, therapist_auth_headers, patient.id, ["gad7"])
    token = token_of(res)
    await consent(client, token)
    await answer_all(client, token, "gad7", [0] * 7)
    await submit(client, token, "gad7")
    session_id = res.json()["data"]["assignment"]["sessions"][0]["id"]
    with pytest.raises(DBAPIError, match="immutable"):
        await db_session.execute(
            text("UPDATE psychosocial_sessions SET referral_flag = true WHERE id = :id"),
            {"id": session_id},
        )
    await db_session.rollback()


async def test_expired_link(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    token = token_of(res)
    row = await db_session.get(PsychosocialAssignment, uuid.UUID(res.json()["data"]["assignment"]["id"]))
    row.expires_at = utcnow() - timedelta(minutes=1)
    await db_session.commit()
    opened = await client.get(f"{API}/screener/{token}")
    assert opened.status_code == 410 and code_of(opened) == "LINK_EXPIRED"
    listed = (await client.get(
        f"{API}/patients/{patient.id}/psychosocial/sessions", headers=therapist_auth_headers
    )).json()["data"]
    assert listed[0]["effective_status"] == "expired"


async def test_cancel_only_before_start(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    a_id = res.json()["data"]["assignment"]["id"]
    token = token_of(res)
    cancel = await client.post(f"{API}/psychosocial/assignments/{a_id}/cancel", headers=therapist_auth_headers)
    assert cancel.status_code == 200
    row = await db_session.get(PsychosocialAssignment, uuid.UUID(a_id))
    await db_session.refresh(row)
    assert row.status == "cancelled" and row.cancelled_by == env["therapist"].id
    gone = await client.get(f"{API}/screener/{token}")
    assert gone.status_code == 410 and code_of(gone) == "LINK_CANCELLED"

    res2 = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    t2 = token_of(res2)
    await consent(client, t2)
    await answer(client, t2, "phq9", "phq9_1", 0)
    blocked = await client.post(
        f"{API}/psychosocial/assignments/{res2.json()['data']['assignment']['id']}/cancel",
        headers=therapist_auth_headers,
    )
    assert blocked.status_code == 409 and code_of(blocked) == "ALREADY_STARTED"


async def test_reissue_link_invalidates_old_token(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, therapist_auth_headers, patient.id, ["gad7"])
    old = token_of(res)
    a_id = res.json()["data"]["assignment"]["id"]
    new = await client.post(
        f"{API}/psychosocial/assignments/{a_id}/link", json={"expires_in_days": 3}, headers=therapist_auth_headers
    )
    assert new.status_code == 200
    assert (await client.get(f"{API}/screener/{old}")).status_code == 404
    assert (await client.get(f"{API}/screener/{token_of(new)}")).status_code == 200


async def test_withdraw_consent_cancels_open_and_blocks_new(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    t1 = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    t2 = token_of(await assign(client, therapist_auth_headers, patient.id, ["gad7"]))
    res = await client.post(f"{API}/screener/{t1}/withdraw")
    assert res.status_code == 200
    assert (await client.get(f"{API}/screener/{t2}")).status_code == 410
    states = (await db_session.scalars(
        select(PsychosocialAssignment.status).where(PsychosocialAssignment.patient_id == patient.id)
    )).all()
    assert sorted(states) == ["cancelled", "cancelled"]
    blocked = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    assert blocked.status_code == 409 and code_of(blocked) == "CONSENT_WITHDRAWN"


async def test_unknown_token_is_404(client):
    res = await client.get(f"{API}/screener/{'x' * 43}")
    assert res.status_code == 404 and code_of(res) == "LINK_NOT_FOUND"
    short = await client.get(f"{API}/screener/abc")
    assert short.status_code == 422


# ---------------------------------------------------------------------------
# scope and clinic isolation
# ---------------------------------------------------------------------------
async def test_own_scope_hides_other_users_sessions(client, db_session, env, auth_headers, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, auth_headers, patient.id, ["phq9"])  # assigned by admin
    session_id = res.json()["data"]["assignment"]["sessions"][0]["id"]
    listed = await client.get(f"{API}/patients/{patient.id}/psychosocial/sessions", headers=therapist_auth_headers)
    assert listed.status_code == 200 and listed.json()["data"] == []
    detail = await client.get(f"{API}/psychosocial/sessions/{session_id}", headers=therapist_auth_headers)
    assert detail.status_code == 404


async def test_clinic_isolation(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    session_id = res.json()["data"]["assignment"]["sessions"][0]["id"]
    a_id = res.json()["data"]["assignment"]["id"]

    email = f"iso_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Other", "email": email, "password": "password123",
              "first_name": "O", "last_name": "C"},
    )
    other_headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    other_admin = await db_session.scalar(select(__import__("app.models.user", fromlist=["User"]).User).where(
        __import__("app.models.user", fromlist=["User"]).User.email == email))
    await entitle(db_session, other_admin.clinic_id)
    await set_overrides(db_session, other_admin.clinic_id, other_admin.id,
                        {"screening.view": "all", "screening.refer": "all"})

    assert (await assign(client, other_headers, patient.id, ["phq9"])).status_code == 404
    assert (await client.get(f"{API}/patients/{patient.id}/psychosocial/sessions", headers=other_headers)).status_code == 404
    assert (await client.get(f"{API}/psychosocial/sessions/{session_id}", headers=other_headers)).status_code == 404
    assert (await client.post(f"{API}/psychosocial/assignments/{a_id}/cancel", headers=other_headers)).status_code == 404
    worklist = (await client.get(f"{API}/psychosocial/sessions", headers=other_headers)).json()["data"]
    assert worklist == []


# ---------------------------------------------------------------------------
# rate limiting
# ---------------------------------------------------------------------------
async def test_rate_limit_per_token(client, db_session, env, therapist_auth_headers, monkeypatch):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    monkeypatch.setattr(rate_limit.token_limiter, "limit", 3)
    for _ in range(3):
        assert (await client.get(f"{API}/screener/{token}")).status_code == 200
    blocked = await client.get(f"{API}/screener/{token}")
    assert blocked.status_code == 429 and code_of(blocked) == "RATE_LIMITED"
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_rate_limit_per_ip_and_trusted_header(client, monkeypatch):
    monkeypatch.setattr(rate_limit.ip_limiter, "limit", 2)
    for _ in range(2):
        assert (await client.get(f"{API}/screener/{'a' * 43}")).status_code == 404
    assert (await client.get(f"{API}/screener/{'b' * 43}")).status_code == 429

    rate_limit.ip_limiter.reset()
    monkeypatch.setattr(settings, "SCREENER_CLIENT_IP_HEADER", "X-Real-IP")
    for ip in ("1.1.1.1", "1.1.1.1", "2.2.2.2", "2.2.2.2"):
        res = await client.get(f"{API}/screener/{'c' * 43}", headers={"X-Real-IP": ip})
        assert res.status_code == 404
    assert (await client.get(f"{API}/screener/{'c' * 43}", headers={"X-Real-IP": "1.1.1.1"})).status_code == 429
