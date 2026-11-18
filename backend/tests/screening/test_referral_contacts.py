"""Referral contact directory (SRS 4.3.1, S-D-029)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.enums.permission import CapabilityScope
from app.models.audit import AuditLog
from app.models.psychosocial import PsychosocialReferralAction, PsychosocialReferralContact
from app.services import psychosocial_report as report
from tests.screening.conftest import API, entitle, make_patient, set_overrides
from tests.screening.test_api import code_of
from tests.screening.test_trend_report import insert_completed

ADMIN_URL = f"{API}/psychosocial/settings/referral-contacts"
PICKER_URL = f"{API}/psychosocial/referral-contacts"
WHEN = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)

DR_RAO = {"name": "Dr Kavita Rao", "role": "Clinical psychologist", "phone": "+91 98765 43210", "email": None, "note": "Tue and Thu"}


@pytest.fixture
async def clean_contacts(db_session, env):
    clinic_id = env["clinic"].id

    async def wipe():
        await db_session.rollback()
        await db_session.execute(
            delete(PsychosocialReferralContact).where(PsychosocialReferralContact.clinic_id == clinic_id)
        )
        await db_session.commit()

    await wipe()
    yield
    await wipe()


async def add(client, headers, body):
    return await client.post(ADMIN_URL, json=body, headers=headers)


async def flagged_session(db_session, env):
    patient = await make_patient(db_session, env["clinic"].id)
    session_id = await insert_completed(
        db_session, env["clinic"].id, patient.id, env["therapist"].id, "phq9", 12, WHEN
    )
    return patient, session_id


# ---------------------------------------------------------------------------
# admin directory
# ---------------------------------------------------------------------------
async def test_admin_adds_edits_archives_and_restores(client, db_session, env, clean_contacts, auth_headers):
    res = await add(client, auth_headers, DR_RAO)
    assert res.status_code == 201, res.text
    c = res.json()["data"]
    assert (c["name"], c["role"], c["phone"], c["email"], c["note"], c["archived"]) == (
        "Dr Kavita Rao", "Clinical psychologist", "+91 98765 43210", None, "Tue and Thu", False
    )
    assert c["updated_by_name"]

    res = await client.put(
        f"{ADMIN_URL}/{c['id']}",
        json={**DR_RAO, "email": "kavita@example.in", "note": "  "},
        headers=auth_headers,
    )
    assert res.status_code == 200, res.text
    assert (res.json()["data"]["email"], res.json()["data"]["note"]) == ("kavita@example.in", None)

    assert (await client.post(f"{ADMIN_URL}/{c['id']}/archive", headers=auth_headers)).json()["data"]["archived"] is True
    # Archiving twice is harmless.
    assert (await client.post(f"{ADMIN_URL}/{c['id']}/archive", headers=auth_headers)).status_code == 200
    listed = (await client.get(ADMIN_URL, headers=auth_headers)).json()["data"]
    assert [(x["name"], x["archived"]) for x in listed] == [("Dr Kavita Rao", True)]
    assert (await client.post(f"{ADMIN_URL}/{c['id']}/restore", headers=auth_headers)).json()["data"]["archived"] is False

    # Saving the same values again changes nothing and writes no audit event.
    same = {**DR_RAO, "email": "kavita@example.in", "note": None}
    assert (await client.put(f"{ADMIN_URL}/{c['id']}", json=same, headers=auth_headers)).status_code == 200

    row = await db_session.get(PsychosocialReferralContact, uuid.UUID(c["id"]))
    await db_session.refresh(row)
    assert (row.clinic_id, row.email, row.archived_at) == (env["clinic"].id, "kavita@example.in", None)

    events = (
        await db_session.scalars(
            select(AuditLog)
            .where(AuditLog.entity_id == uuid.UUID(c["id"]))
            .order_by(AuditLog.created_at, AuditLog.id)
        )
    ).all()
    assert [e.action for e in events] == [
        "psychosocial.referral_contact_created",
        "psychosocial.referral_contact_updated",
        "psychosocial.referral_contact_archived",
        "psychosocial.referral_contact_restored",
    ]
    assert events[1].details == {"fields": ["email", "note"]}


async def test_admin_list_puts_active_first_then_by_name(client, env, clean_contacts, auth_headers):
    ids = {}
    for name in ("zoya Khan", "Arun Shah", "Meena Iyer"):
        ids[name] = (await add(client, auth_headers, {**DR_RAO, "name": name})).json()["data"]["id"]
    await client.post(f"{ADMIN_URL}/{ids['Arun Shah']}/archive", headers=auth_headers)
    listed = (await client.get(ADMIN_URL, headers=auth_headers)).json()["data"]
    assert [x["name"] for x in listed] == ["Meena Iyer", "zoya Khan", "Arun Shah"]


@pytest.mark.parametrize(
    "body",
    [
        {**DR_RAO, "name": "   "},
        {**DR_RAO, "role": ""},
        {**DR_RAO, "phone": None, "email": None},
        {**DR_RAO, "phone": "  ", "email": ""},
        {**DR_RAO, "phone": "12345"},
        {**DR_RAO, "phone": "98765abc10"},
        {**DR_RAO, "phone": "98+7654321"},
        {**DR_RAO, "email": "not-an-email"},
        {**DR_RAO, "name": "x" * 121},
        {**DR_RAO, "note": "x" * 501},
        {**DR_RAO, "patient_id": str(uuid.uuid4())},
    ],
)
async def test_invalid_contact_is_rejected(client, env, clean_contacts, auth_headers, body):
    res = await add(client, auth_headers, body)
    assert res.status_code == 422, res.text


async def test_email_only_contact_is_fine(client, env, clean_contacts, auth_headers):
    res = await add(client, auth_headers, {**DR_RAO, "phone": None, "email": "help@clinic.in"})
    assert res.status_code == 201, res.text


async def test_database_requires_phone_or_email(db_session, env, clean_contacts):
    db_session.add(
        PsychosocialReferralContact(id=uuid.uuid4(), clinic_id=env["clinic"].id, name="A", role="B")
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_access_and_clinic_isolation(
    client, db_session, env, clean_contacts, auth_headers, therapist_auth_headers
):
    c = (await add(client, auth_headers, DR_RAO)).json()["data"]
    # The physio can read the picker list but cannot manage the directory.
    assert (await client.get(PICKER_URL, headers=therapist_auth_headers)).status_code == 200
    assert (await client.get(ADMIN_URL, headers=therapist_auth_headers)).status_code == 403
    assert (await add(client, therapist_auth_headers, DR_RAO)).status_code == 403
    assert (await client.post(f"{ADMIN_URL}/{c['id']}/archive", headers=therapist_auth_headers)).status_code == 403

    # Another clinic sees none of it and cannot touch it.
    email = f"other_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Other", "email": email, "password": "password123", "first_name": "A", "last_name": "B"},
    )
    other = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    other_clinic = uuid.UUID((await client.get(f"{API}/me", headers=other)).json()["data"]["active_workspace"]["id"])
    await entitle(db_session, other_clinic)
    assert (await client.get(ADMIN_URL, headers=other)).json()["data"] == []
    res = await client.put(f"{ADMIN_URL}/{c['id']}", json=DR_RAO, headers=other)
    assert res.status_code == 404 and code_of(res) == "CONTACT_NOT_FOUND"
    assert (await client.post(f"{ADMIN_URL}/{c['id']}/archive", headers=other)).status_code == 404

    # An admin whose configure grant is removed is refused.
    await set_overrides(db_session, env["clinic"].id, env["admin"].id, {"screening.configure": "none"})
    assert (await add(client, auth_headers, DR_RAO)).status_code == 403


# ---------------------------------------------------------------------------
# referral actions name a contact
# ---------------------------------------------------------------------------
async def test_physio_logs_a_referral_to_a_contact(
    client, db_session, env, clean_contacts, auth_headers, therapist_auth_headers
):
    c = (await add(client, auth_headers, DR_RAO)).json()["data"]
    archived = (await add(client, auth_headers, {**DR_RAO, "name": "Old Contact"})).json()["data"]
    await client.post(f"{ADMIN_URL}/{archived['id']}/archive", headers=auth_headers)

    picker = (await client.get(PICKER_URL, headers=therapist_auth_headers)).json()["data"]
    assert [x["name"] for x in picker] == ["Dr Kavita Rao"]
    assert picker[0]["phone"] == "+91 98765 43210"

    patient, session_id = await flagged_session(db_session, env)
    url = f"{API}/psychosocial/sessions/{session_id}/referral-actions"
    res = await client.post(
        url, json={"action": "referred_psychologist", "contact_id": c["id"]}, headers=therapist_auth_headers
    )
    assert res.status_code == 201, res.text
    assert (res.json()["data"]["contact_name"], res.json()["data"]["contact_role"]) == (
        "Dr Kavita Rao", "Clinical psychologist"
    )

    # Archived, unknown and other-clinic contacts are refused.
    for bad in (archived["id"], str(uuid.uuid4())):
        res = await client.post(url, json={"action": "referred_psychologist", "contact_id": bad}, headers=therapist_auth_headers)
        assert res.status_code == 422 and code_of(res) == "CONTACT_UNAVAILABLE"
    # No contact is still fine.
    assert (await client.post(url, json={"action": "patient_declined"}, headers=therapist_auth_headers)).status_code == 201

    # The log keeps the name and role it was saved with, after an edit and an archive.
    await client.put(f"{ADMIN_URL}/{c['id']}", json={**DR_RAO, "name": "Dr K Rao-Menon", "role": "Psychiatrist"}, headers=auth_headers)
    await client.post(f"{ADMIN_URL}/{c['id']}/archive", headers=auth_headers)
    history = (
        await client.get(f"{API}/patients/{patient.id}/psychosocial/referral-actions", headers=therapist_auth_headers)
    ).json()["data"]
    assert [(h["action"], h["contact_name"], h["contact_role"]) for h in history] == [
        ("referred_psychologist", "Dr Kavita Rao", "Clinical psychologist"),
        ("patient_declined", None, None),
    ]
    rows = (
        await db_session.scalars(
            select(PsychosocialReferralAction).where(PsychosocialReferralAction.session_id == session_id)
        )
    ).all()
    assert {r.contact_id for r in rows} == {uuid.UUID(c["id"]), None}

    # The PDF summary names the contact too.
    data = await report.build_report_data(
        db_session, clinic_id=env["clinic"].id, patient_id=patient.id, scope=CapabilityScope.ALL, user_id=env["therapist"].id
    )
    assert [r.contact for r in data.referrals] == ["Dr Kavita Rao (Clinical psychologist)", None]
    assert "To: Dr Kavita Rao (Clinical psychologist)" in report.build_report_html(data)


async def test_contact_details_stay_out_of_the_audit_log_for_referrals(
    client, db_session, env, clean_contacts, auth_headers, therapist_auth_headers
):
    c = (await add(client, auth_headers, DR_RAO)).json()["data"]
    _, session_id = await flagged_session(db_session, env)
    await client.post(
        f"{API}/psychosocial/sessions/{session_id}/referral-actions",
        json={"action": "referred_gp", "contact_id": c["id"]},
        headers=therapist_auth_headers,
    )
    [event] = (
        await db_session.scalars(
            select(AuditLog).where(AuditLog.action == "psychosocial.referral_logged", AuditLog.entity_id == session_id)
        )
    ).all()
    assert event.details["contact_id"] == c["id"]
    assert "98765" not in str(event.details) and "Rao" not in str(event.details)
