"""Tool 03 deletion on request (SRS 3.2, S-D-024).

Every case checks the database, not only the status code.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.rbac import ROLE_TEMPLATES
from app.enums.permission import CapabilityScope
from app.enums.user import UserRole
from app.models.audit import AuditLog
from app.models.psychosocial import (
    PsychosocialAssignment,
    PsychosocialConsent,
    PsychosocialReferralAction,
    PsychosocialSchedule,
    PsychosocialSession,
)
from tests.screening.conftest import API, entitle, make_patient, set_overrides
from tests.screening.test_api import answer_all, assign, code_of, consent, submit, token_of

pytestmark = pytest.mark.asyncio

TABLES = (
    PsychosocialAssignment,
    PsychosocialSession,
    PsychosocialConsent,
    PsychosocialReferralAction,
    PsychosocialSchedule,
)


async def rows(db, patient_id) -> dict[str, int]:
    out = {}
    for model in TABLES:
        out[model.__tablename__] = await db.scalar(
            select(func.count()).select_from(model).where(model.patient_id == patient_id)
        )
    return out


async def screened_patient(client, db, clinic_id, headers):
    """One completed PHQ-9 with a risk answer and a referral action, plus one open GAD-7 link set to repeat every 4 weeks."""
    patient = await make_patient(db, clinic_id)
    res = await assign(client, headers, patient.id, ["phq9"])
    token = token_of(res)
    session_id = res.json()["data"]["assignment"]["sessions"][0]["id"]
    await consent(client, token)
    await answer_all(client, token, "phq9", [1, 1, 1, 1, 1, 1, 1, 1, 1])
    assert (await submit(client, token, "phq9")).status_code == 200
    logged = await client.post(
        f"{API}/psychosocial/sessions/{session_id}/referral-actions",
        json={"action": "referred_gp"},
        headers=headers,
    )
    assert logged.status_code == 201, logged.text
    repeating = await client.post(
        f"{API}/patients/{patient.id}/psychosocial/sessions",
        json={"instruments": ["gad7"], "expires_in_days": 7, "repeat_every_weeks": 4},
        headers=headers,
    )
    assert repeating.status_code == 201, repeating.text
    open_token = token_of(repeating)
    return patient, token, open_token


async def delete_data(client, headers, patient_id, confirm="DELETE"):
    return await client.post(
        f"{API}/patients/{patient_id}/psychosocial/data/delete",
        json={"confirm": confirm},
        headers=headers,
    )


async def test_admin_deletes_all_screening_data(
    client, db_session, env, auth_headers, therapist_auth_headers
):
    clinic_id = env["clinic"].id
    patient, done_token, open_token = await screened_patient(
        client, db_session, clinic_id, therapist_auth_headers
    )
    other, _, _ = await screened_patient(client, db_session, clinic_id, therapist_auth_headers)
    other_before = await rows(db_session, other.id)

    expected = {
        "patient_id": str(patient.id),
        "links": 2,
        "screeners": 2,
        "referral_actions": 1,
        "schedules": 1,
        "consent_records": 1,
        "withdrawal_on_file": False,
    }
    preview = await client.get(f"{API}/patients/{patient.id}/psychosocial/data", headers=auth_headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"] == expected
    assert await rows(db_session, patient.id) == {
        "psychosocial_assignments": 2,
        "psychosocial_sessions": 2,
        "psychosocial_consents": 1,
        "psychosocial_referral_actions": 1,
        "psychosocial_schedules": 1,
    }

    # The confirmation word is required, exactly.
    assert (await delete_data(client, auth_headers, patient.id, "delete")).status_code == 422
    missing = await client.post(
        f"{API}/patients/{patient.id}/psychosocial/data/delete", json={}, headers=auth_headers
    )
    assert missing.status_code == 422
    assert (await rows(db_session, patient.id))["psychosocial_sessions"] == 2

    res = await delete_data(client, auth_headers, patient.id)
    assert res.status_code == 200, res.text
    assert res.json()["data"] == expected

    # Gone from every table, including the completed session.
    assert await rows(db_session, patient.id) == {
        "psychosocial_assignments": 0,
        "psychosocial_sessions": 0,
        "psychosocial_consents": 0,
        "psychosocial_referral_actions": 0,
        "psychosocial_schedules": 0,
    }
    # Another patient in the same clinic is untouched.
    assert await rows(db_session, other.id) == other_before

    # Old links stop working and the physio sees nothing.
    assert (await client.get(f"{API}/screener/{open_token}")).status_code == 404
    assert (await client.get(f"{API}/screener/{done_token}")).status_code == 404
    listed = await client.get(
        f"{API}/patients/{patient.id}/psychosocial/sessions", headers=therapist_auth_headers
    )
    assert listed.status_code == 200 and listed.json()["data"] == []
    summary = await client.get(
        f"{API}/patients/{patient.id}/psychosocial/summary", headers=therapist_auth_headers
    )
    assert summary.json()["data"]["latest"] == []

    after = await client.get(f"{API}/patients/{patient.id}/psychosocial/data", headers=auth_headers)
    assert after.json()["data"]["links"] == 0 and after.json()["data"]["screeners"] == 0

    # Audit: one event by the admin, counts only, no clinical values.
    events = (
        await db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "psychosocial.data_deleted",
                AuditLog.entity_id == patient.id,
            )
        )
    ).all()
    assert len(events) == 1
    event = events[0]
    assert event.user_id == env["admin"].id
    assert event.details == {
        "patient_id": str(patient.id),
        "links": 2,
        "screeners": 2,
        "referral_actions": 1,
        "schedules": 1,
        "consent_records": 1,
        "withdrawal_kept": False,
    }
    blob = str(event.details).lower()
    for word in ("score", "band", "referral_flag", "risk", "phq9", "gad7"):
        assert word not in blob

    # A fresh screener works and asks for consent again.
    fresh = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    assert fresh.status_code == 201
    opened = (await client.get(f"{API}/screener/{token_of(fresh)}")).json()["data"]
    assert opened["consent"]["required"] is True


async def test_withdrawal_is_kept_so_no_new_screener_goes_out(
    client, db_session, env, auth_headers, therapist_auth_headers
):
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    await consent(client, token)
    await answer_all(client, token, "phq9", [0, 0, 0])
    assert (await client.post(f"{API}/screener/{token}/withdraw")).status_code == 200

    preview = (
        await client.get(f"{API}/patients/{patient.id}/psychosocial/data", headers=auth_headers)
    ).json()["data"]
    assert preview["withdrawal_on_file"] is True
    assert preview["consent_records"] == 1  # the grant; the withdrawal is kept

    res = await delete_data(client, auth_headers, patient.id)
    assert res.status_code == 200, res.text

    kept = (
        await db_session.scalars(
            select(PsychosocialConsent).where(PsychosocialConsent.patient_id == patient.id)
        )
    ).all()
    assert [(c.status, c.assignment_id) for c in kept] == [("withdrawn", None)]
    counts = await rows(db_session, patient.id)
    assert counts["psychosocial_sessions"] == 0 and counts["psychosocial_assignments"] == 0

    blocked = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    assert blocked.status_code == 409 and code_of(blocked) == "CONSENT_WITHDRAWN"

    # Running it again is safe and removes nothing more.
    again = await delete_data(client, auth_headers, patient.id)
    assert again.status_code == 200
    assert again.json()["data"]["consent_records"] == 0
    assert again.json()["data"]["withdrawal_on_file"] is True
    assert await rows(db_session, patient.id) == {
        "psychosocial_assignments": 0,
        "psychosocial_sessions": 0,
        "psychosocial_consents": 1,
        "psychosocial_referral_actions": 0,
        "psychosocial_schedules": 0,
    }


async def test_only_holders_of_screening_delete_can_delete(
    client, db_session, env, therapist_auth_headers
):
    # The therapist can see every result but has no delete grant.
    await set_overrides(
        db_session,
        env["clinic"].id,
        env["therapist"].id,
        {"screening.assign": "all", "screening.view": "all", "screening.refer": "all"},
    )
    patient, _, _ = await screened_patient(client, db_session, env["clinic"].id, therapist_auth_headers)
    before = await rows(db_session, patient.id)

    preview = await client.get(
        f"{API}/patients/{patient.id}/psychosocial/data", headers=therapist_auth_headers
    )
    assert preview.status_code == 403
    res = await delete_data(client, therapist_auth_headers, patient.id)
    assert res.status_code == 403
    assert await rows(db_session, patient.id) == before


async def test_admin_can_switch_off_their_own_delete(client, db_session, env, auth_headers, therapist_auth_headers):
    patient, _, _ = await screened_patient(client, db_session, env["clinic"].id, therapist_auth_headers)
    await set_overrides(db_session, env["clinic"].id, env["admin"].id, {"screening.delete": "none"})
    try:
        res = await delete_data(client, auth_headers, patient.id)
        assert res.status_code == 403
        assert (await rows(db_session, patient.id))["psychosocial_sessions"] == 2
    finally:
        await set_overrides(db_session, env["clinic"].id, env["admin"].id, {})


async def test_other_clinic_cannot_delete(client, db_session, env, therapist_auth_headers):
    from app.models.user import User

    patient, _, _ = await screened_patient(client, db_session, env["clinic"].id, therapist_auth_headers)
    before = await rows(db_session, patient.id)

    email = f"del_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Other", "email": email, "password": "password123",
              "first_name": "O", "last_name": "C"},
    )
    other_headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    other_admin = await db_session.scalar(select(User).where(User.email == email))
    await entitle(db_session, other_admin.clinic_id)

    preview = await client.get(f"{API}/patients/{patient.id}/psychosocial/data", headers=other_headers)
    assert preview.status_code == 404
    res = await delete_data(client, other_headers, patient.id)
    assert res.status_code == 404 and code_of(res) == "PATIENT_NOT_FOUND"
    assert await rows(db_session, patient.id) == before


async def test_unknown_patient_is_404(client, env, auth_headers):
    res = await delete_data(client, auth_headers, uuid.uuid4())
    assert res.status_code == 404 and code_of(res) == "PATIENT_NOT_FOUND"


def test_delete_capability_is_admin_only_by_default():
    assert ROLE_TEMPLATES[UserRole.ADMIN]["screening.delete"] == CapabilityScope.ALL
    assert ROLE_TEMPLATES[UserRole.THERAPIST]["screening.delete"] == CapabilityScope.NONE
    assert ROLE_TEMPLATES[UserRole.FRONT_DESK]["screening.delete"] == CapabilityScope.NONE
