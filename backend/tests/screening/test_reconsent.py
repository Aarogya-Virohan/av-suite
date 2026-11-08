"""Re-consent link after a withdrawal (Q7 = 7B, S-D-037) and the 14-day
warning before sending the same screener again (S-D-038).

Every write is checked in the database.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.enums.product import EntitlementStatus
from app.models.audit import AuditLog
from app.models.product import WorkspaceProduct
from app.models.psychosocial import (
    PsychosocialAssignment,
    PsychosocialConsent,
    PsychosocialConsentRequest,
)
from app.screening.consent import CONSENT_TEXT_VERSION
from app.services.psychosocial import RECENT_SEND_DAYS, utcnow
from tests.screening.conftest import API, PRODUCT, make_patient, set_overrides
from tests.screening.test_api import assign, code_of, consent, token_of

pytestmark = pytest.mark.asyncio


async def withdrawn_patient(client, db, env, headers, **assign_extra):
    patient = await make_patient(db, env["clinic"].id)
    token = token_of(await assign(client, headers, patient.id, ["phq9"], **assign_extra))
    await consent(client, token)
    assert (await client.post(f"{API}/screener/{token}/withdraw")).status_code == 200
    return patient


async def request_link(client, headers, patient_id, **body):
    return await client.post(f"{API}/patients/{patient_id}/psychosocial/consent-request", json=body, headers=headers)


def token_from(res) -> str:
    path = res.json()["data"]["consent_path"]
    assert path.startswith("/consent/")
    return path.rsplit("/", 1)[1]


async def answer(client, token, accept, version=CONSENT_TEXT_VERSION):
    return await client.post(
        f"{API}/screener/reconsent/{token}/answer", json={"accept": accept, "text_version": version}
    )


async def consent_state(client, headers, patient_id) -> dict:
    res = await client.get(f"{API}/patients/{patient_id}/psychosocial/consent", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()["data"]


async def latest_consent_row(db, patient_id) -> PsychosocialConsent:
    row = await db.scalar(
        select(PsychosocialConsent)
        .where(PsychosocialConsent.patient_id == patient_id)
        .order_by(PsychosocialConsent.recorded_at.desc())
        .limit(1)
    )
    await db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# re-consent
# ---------------------------------------------------------------------------
async def test_patient_opts_back_in_and_screeners_can_go_again(client, db_session, env, therapist_auth_headers):
    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers)
    state = await consent_state(client, therapist_auth_headers, patient.id)
    assert (state["status"], state["request"]) == ("withdrawn", None)
    blocked = await assign(client, therapist_auth_headers, patient.id, ["gad7"])
    assert blocked.status_code == 409 and code_of(blocked) == "CONSENT_WITHDRAWN"

    created = await request_link(client, therapist_auth_headers, patient.id)
    assert created.status_code == 201, created.text
    token = token_from(created)
    assert created.json()["data"]["request"]["state"] == "pending"

    opened = await client.get(f"{API}/screener/reconsent/{token}")
    assert opened.status_code == 200, opened.text
    data = opened.json()["data"]
    assert set(data) == {"clinic_name", "state", "expires_at", "consent"}  # no patient identity
    assert data["state"] == "pending" and data["consent"]["text_version"] == CONSENT_TEXT_VERSION

    stale = await answer(client, token, True, version="2026-10-20.draft1")
    assert stale.status_code == 409 and code_of(stale) == "CONSENT_TEXT_CHANGED"

    ok = await answer(client, token, True)
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["state"] == "granted"
    row = await latest_consent_row(db_session, patient.id)
    assert (row.status, row.text_version, row.assignment_id) == ("granted", CONSENT_TEXT_VERSION, None)
    request = await db_session.scalar(
        select(PsychosocialConsentRequest).where(PsychosocialConsentRequest.patient_id == patient.id)
    )
    await db_session.refresh(request)
    assert request.status == "granted" and request.answered_at is not None

    # Same answer again is fine; changing it is not.
    assert (await answer(client, token, True)).status_code == 200
    changed = await answer(client, token, False)
    assert changed.status_code == 409 and code_of(changed) == "ALREADY_ANSWERED"

    state = await consent_state(client, therapist_auth_headers, patient.id)
    assert state["status"] == "granted" and state["request"]["state"] == "granted"
    sent = await assign(client, therapist_auth_headers, patient.id, ["gad7"])
    assert sent.status_code == 201, sent.text
    screener = (await client.get(f"{API}/screener/{token_of(sent)}")).json()["data"]
    assert screener["consent"]["required"] is False  # no second consent screen

    events = (
        await db_session.scalars(
            select(AuditLog).where(AuditLog.action.like("psychosocial.reconsent_%"), AuditLog.entity_id == request.id)
        )
    ).all()
    assert sorted(e.action for e in events) == ["psychosocial.reconsent_granted", "psychosocial.reconsent_requested"]
    for e in events:
        for word in ("score", "band", "risk", "referral", "phq", "gad"):
            assert word not in str(e.details).lower()


async def test_patient_says_no_and_nothing_else_changes(client, db_session, env, therapist_auth_headers):
    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers)
    token = token_from(await request_link(client, therapist_auth_headers, patient.id))
    res = await answer(client, token, False, version=None)
    assert res.status_code == 200 and res.json()["data"]["state"] == "declined"
    assert (await latest_consent_row(db_session, patient.id)).status == "withdrawn"
    assert (await consent_state(client, therapist_auth_headers, patient.id))["request"]["state"] == "declined"
    assert (await assign(client, therapist_auth_headers, patient.id, ["gad7"])).status_code == 409
    # Asking again later is allowed.
    assert (await request_link(client, therapist_auth_headers, patient.id)).status_code == 201


async def test_only_after_a_withdrawal(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    res = await request_link(client, therapist_auth_headers, patient.id)
    assert res.status_code == 409 and code_of(res) == "CONSENT_NOT_WITHDRAWN"
    assert (await consent_state(client, therapist_auth_headers, patient.id))["status"] == "none"
    bad = await request_link(client, therapist_auth_headers, patient.id, expires_in_days=31)
    assert bad.status_code == 422


async def test_needs_send_permission(client, db_session, env, therapist_auth_headers, auth_headers):
    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers)
    # Admins send links (F3), so they may ask too.
    assert (await request_link(client, auth_headers, patient.id)).status_code == 201
    await set_overrides(db_session, env["clinic"].id, env["therapist"].id, {"screening.view": "own"})
    assert (await request_link(client, therapist_auth_headers, patient.id)).status_code == 403
    res = await client.get(f"{API}/patients/{patient.id}/psychosocial/consent", headers=therapist_auth_headers)
    assert res.status_code == 403


async def test_new_link_stops_the_old_one_and_links_expire(client, db_session, env, therapist_auth_headers):
    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers)
    first = token_from(await request_link(client, therapist_auth_headers, patient.id))
    second_res = await request_link(client, therapist_auth_headers, patient.id)
    second = token_from(second_res)
    old = await client.get(f"{API}/screener/reconsent/{first}")
    assert old.status_code == 410 and code_of(old) == "LINK_CANCELLED"
    assert (await answer(client, first, True)).status_code == 410
    pending = await db_session.scalar(
        select(func.count())
        .select_from(PsychosocialConsentRequest)
        .where(PsychosocialConsentRequest.patient_id == patient.id, PsychosocialConsentRequest.status == "pending")
    )
    assert pending == 1

    await db_session.execute(
        update(PsychosocialConsentRequest)
        .where(PsychosocialConsentRequest.id == uuid.UUID(second_res.json()["data"]["request"]["id"]))
        .values(expires_at=utcnow() - timedelta(minutes=1))
    )
    await db_session.commit()
    expired = await client.get(f"{API}/screener/reconsent/{second}")
    assert expired.status_code == 410 and code_of(expired) == "LINK_EXPIRED"
    assert (await answer(client, second, True)).status_code == 410
    assert (await latest_consent_row(db_session, patient.id)).status == "withdrawn"
    assert (await consent_state(client, therapist_auth_headers, patient.id))["request"]["state"] == "expired"


async def test_unknown_link_and_clinic_without_screening(client, db_session, env, therapist_auth_headers):
    missing = await client.get(f"{API}/screener/reconsent/{'x' * 43}")
    assert missing.status_code == 404 and code_of(missing) == "LINK_NOT_FOUND"
    assert (await client.get(f"{API}/screener/reconsent/short")).status_code == 422

    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers)
    token = token_from(await request_link(client, therapist_auth_headers, patient.id))
    clinic_id = env["clinic"].id

    async def set_product(value):
        await db_session.execute(
            update(WorkspaceProduct)
            .where(WorkspaceProduct.clinic_id == clinic_id, WorkspaceProduct.product_id == PRODUCT)
            .values(status=value)
        )
        await db_session.commit()

    try:
        await set_product(EntitlementStatus.DISABLED)
        for res in (await client.get(f"{API}/screener/reconsent/{token}"), await answer(client, token, True)):
            assert res.status_code == 403 and code_of(res) == "SCREENING_UNAVAILABLE"
        assert (await latest_consent_row(db_session, patient.id)).status == "withdrawn"
    finally:
        await set_product(EntitlementStatus.ENABLED)


async def test_paused_repeat_starts_again_after_opting_in(client, db_session, env, therapist_auth_headers):
    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers, repeat_every_weeks=4)
    res = await client.get(f"{API}/patients/{patient.id}/psychosocial/schedules", headers=therapist_auth_headers)
    assert [s["state"] for s in res.json()["data"]] == ["consent_withdrawn"]
    await answer(client, token_from(await request_link(client, therapist_auth_headers, patient.id)), True)
    res = await client.get(f"{API}/patients/{patient.id}/psychosocial/schedules", headers=therapist_auth_headers)
    assert [s["state"] for s in res.json()["data"]] != ["consent_withdrawn"]


async def test_deletion_removes_consent_links(client, db_session, env, therapist_auth_headers, auth_headers):
    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers)
    await request_link(client, therapist_auth_headers, patient.id)
    res = await client.post(
        f"{API}/patients/{patient.id}/psychosocial/data/delete", json={"confirm": "DELETE"}, headers=auth_headers
    )
    assert res.status_code == 200, res.text
    left = await db_session.scalar(
        select(func.count())
        .select_from(PsychosocialConsentRequest)
        .where(PsychosocialConsentRequest.patient_id == patient.id)
    )
    assert left == 0
    # The withdrawal is kept, so the provider can still ask again.
    assert (await consent_state(client, therapist_auth_headers, patient.id))["status"] == "withdrawn"
    assert (await request_link(client, therapist_auth_headers, patient.id)).status_code == 201


# ---------------------------------------------------------------------------
# 14-day warning (S-D-038)
# ---------------------------------------------------------------------------
async def test_same_screener_within_14_days_needs_a_second_yes(client, db_session, env, therapist_auth_headers):
    assert RECENT_SEND_DAYS == 14
    patient = await make_patient(db_session, env["clinic"].id)
    first = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    assert first.status_code == 201

    again = await assign(client, therapist_auth_headers, patient.id, ["phq9", "gad7"])
    assert again.status_code == 409 and code_of(again) == "RECENTLY_SENT"
    detail = again.json()["detail"]
    assert [r["instrument_id"] for r in detail["recent"]] == ["phq9"]
    assert "PHQ-9" in detail["message"]
    count = lambda: db_session.scalar(  # noqa: E731
        select(func.count()).select_from(PsychosocialAssignment).where(PsychosocialAssignment.patient_id == patient.id)
    )
    assert await count() == 1

    assert (await assign(client, therapist_auth_headers, patient.id, ["gad7"])).status_code == 201
    forced = await assign(client, therapist_auth_headers, patient.id, ["phq9"], allow_recent=True)
    assert forced.status_code == 201, forced.text
    assert await count() == 3


async def test_cancelled_or_older_sends_do_not_count(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    first = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    aid = first.json()["data"]["assignment"]["id"]
    assert (await client.post(f"{API}/psychosocial/assignments/{aid}/cancel", headers=therapist_auth_headers)).status_code == 200
    second = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    assert second.status_code == 201, second.text

    await db_session.execute(
        update(PsychosocialAssignment)
        .where(PsychosocialAssignment.patient_id == patient.id)
        .values(created_at=utcnow() - timedelta(days=RECENT_SEND_DAYS, minutes=1))
    )
    await db_session.commit()
    assert (await assign(client, therapist_auth_headers, patient.id, ["phq9"])).status_code == 201
