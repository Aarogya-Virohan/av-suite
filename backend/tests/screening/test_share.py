"""Provider-shared report (founders' F2 follow-up, S-D-039).

Pure wording rules first, then the API end to end with database checks.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select, update

from app.enums.product import EntitlementStatus
from app.models.audit import AuditLog
from app.models.product import WorkspaceProduct
from app.models.psychosocial import PsychosocialAssignment, PsychosocialSharedReport
from app.screening.share import (
    RESOURCES,
    RESOURCES_BY_KEY,
    clean_custom_link,
    link_domain,
    summary_line,
)
from app.services.psychosocial import aware, utcnow
from app.services.psychosocial_share import MAX_BIRTH_YEAR_ATTEMPTS
from tests.screening.conftest import API, PRODUCT, make_patient, set_overrides
from tests.screening.test_api import answer_all, assign, code_of, consent, submit, token_of

pytestmark = pytest.mark.asyncio

PHQ9_18 = [2, 2, 2, 2, 2, 2, 2, 2, 2]  # 18, includes an item 9 answer
GAD7_6 = [1, 1, 1, 1, 1, 1, 0]
# Words the patient must never read on the shared page.
FORBIDDEN = ("severe", "moderate", "minimal", "risk", "referral", "urgent", "flag", "self-harm", "harm")


# ---------------------------------------------------------------------------
# pure rules
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "instrument,values,phrase",
    [
        ("phq9", [0] * 9, "Within the typical range."),
        ("phq9", [1, 1, 1, 1, 1, 0, 0, 0, 0], "Mild indicators of low mood or tiredness."),
        ("phq9", [2, 2, 2, 2, 2, 0, 0, 0, 0], "Elevated indicators of low mood or tiredness."),
        ("phq9", PHQ9_18, "Elevated indicators of low mood or tiredness."),
        ("phq9", [3] * 9, "Elevated indicators of low mood or tiredness."),
        ("gad7", [0] * 7, "Within the typical range."),
        ("gad7", GAD7_6, "Mild indicators of worry or tension."),
        ("gad7", [2, 2, 2, 2, 2, 0, 0], "Elevated indicators of worry or tension."),
        ("gad7", [3] * 7, "Elevated indicators of worry or tension."),
    ],
)
def test_summary_wording(instrument, values, phrase):
    from app.screening.registry import LATEST

    inst = LATEST[instrument]
    line = summary_line(instrument, inst.version, {item.id: v for item, v in zip(inst.items, values)})
    assert line.phrase == phrase
    assert line.score == sum(values) and line.max_score == {"phq9": 27, "gad7": 21}[instrument]
    for word in FORBIDDEN:
        assert word not in line.phrase.lower()


def test_retired_instrument_is_not_shareable():
    from app.screening.registry import LATEST

    inst = LATEST["dass21"]
    with pytest.raises(ValueError):
        summary_line("dass21", inst.version, {item.id: 0 for item in inst.items})


@pytest.mark.parametrize(
    "url",
    ["http://example.com", "https://localhost", "javascript:alert(1)", "https://user:pw@example.com/x", "ftp://a.b"],
)
def test_custom_links_must_be_plain_https(url):
    with pytest.raises(ValueError):
        clean_custom_link("A video", url)


def test_custom_link_cleaned():
    assert clean_custom_link("  My   video ", " https://www.youtube.com/watch?v=x ") == (
        "My video",
        "https://www.youtube.com/watch?v=x",
    )
    assert link_domain("https://www.youtube.com/watch?v=x") == "youtube.com"
    with pytest.raises(ValueError):
        clean_custom_link(" ", "https://example.com")


def test_catalogue_links_are_https_and_unique():
    assert len(RESOURCES_BY_KEY) == len(RESOURCES)
    assert [r.key for r in RESOURCES][:4] == ["tele_manas", "sleep_hygiene", "muscle_relaxation", "pain_stress"]
    for r in RESOURCES:
        assert (r.url is None) == bool(r.phones)
        if r.url:
            clean_custom_link(r.title, r.url)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
async def completed(client, db, env, headers, *, dob: date | None = date(1985, 4, 2)):
    patient = await make_patient(db, env["clinic"].id)
    if dob:
        patient.date_of_birth = dob
        await db.commit()
    res = await assign(client, headers, patient.id, ["phq9", "gad7"])
    token = token_of(res)
    await consent(client, token)
    await answer_all(client, token, "phq9", PHQ9_18)
    await submit(client, token, "phq9")
    await answer_all(client, token, "gad7", GAD7_6)
    await submit(client, token, "gad7")
    return patient, res.json()["data"]["assignment"]["id"]


async def share(client, headers, assignment_id, **body):
    body.setdefault("advice", "We discussed this today. Keep a sleep diary for 2 weeks.")
    body.setdefault("resources", ["pain_stress", "tele_manas"])
    return await client.post(f"{API}/psychosocial/assignments/{assignment_id}/share", json=body, headers=headers)


def report_token(res) -> str:
    path = res.json()["data"]["report_path"]
    assert path.startswith("/report/")
    return path.rsplit("/", 1)[1]


async def open_report(client, token, year=None):
    return await client.post(f"{API}/screener/report/{token}/open", json={"birth_year": year})


async def share_row(db, share_id) -> PsychosocialSharedReport:
    row = await db.get(PsychosocialSharedReport, uuid.UUID(share_id))
    await db.refresh(row)
    return row


async def test_provider_shares_and_patient_reads_a_sanitised_report(client, db_session, env, therapist_auth_headers):
    patient, aid = await completed(client, db_session, env, therapist_auth_headers)
    res = await share(
        client,
        therapist_auth_headers,
        aid,
        custom_links=[{"title": "Walking plan video", "url": "https://www.youtube.com/watch?v=abc"}],
    )
    assert res.status_code == 201, res.text
    data = res.json()["data"]["share"]
    assert data["state"] == "active" and data["birth_year_check"] is True
    assert data["resource_titles"] == [
        "Tele-MANAS mental health helpline",
        "Understanding the pain-stress connection",
        "Walking plan video",
    ]
    row = await share_row(db_session, data["id"])
    assert row.resource_keys == ["tele_manas", "pain_stress"]  # catalogue order
    assert row.advice.startswith("We discussed this today")
    assert utcnow() + timedelta(days=29) < aware(row.expires_at) < utcnow() + timedelta(days=31)
    token = report_token(res)

    gate = await client.get(f"{API}/screener/report/{token}")
    assert gate.status_code == 200
    assert gate.json()["data"] == {"clinic_name": gate.json()["data"]["clinic_name"], "needs_birth_year": True}

    wrong = await open_report(client, token, 1990)
    assert wrong.status_code == 403 and code_of(wrong) == "WRONG_BIRTH_YEAR"
    assert wrong.json()["detail"]["attempts_left"] == MAX_BIRTH_YEAR_ATTEMPTS - 1
    assert (await open_report(client, token)).status_code == 403  # no year at all

    ok = await open_report(client, token, 1985)
    assert ok.status_code == 200, ok.text
    report = ok.json()["data"]
    assert report["advice"].startswith("We discussed this today")
    assert [(s["short_name"], s["score"], s["max_score"], s["phrase"]) for s in report["summary"]] == [
        ("PHQ-9", 18, 27, "Elevated indicators of low mood or tiredness."),
        ("GAD-7", 6, 21, "Mild indicators of worry or tension."),
    ]
    assert [r["title"] for r in report["resources"]] == [
        "Tele-MANAS mental health helpline",
        "Understanding the pain-stress connection",
        "Walking plan video",
    ]
    assert report["resources"][2]["domain"] == "youtube.com"
    assert report["resources"][0]["phones"][0] == {"label": "14416", "tel": "14416"}
    text = json.dumps(report).lower()
    for word in FORBIDDEN:
        assert word not in text, word

    row = await share_row(db_session, data["id"])
    assert (row.open_count, row.failed_attempts) == (1, 0) and row.first_opened_at is not None
    await open_report(client, token, 1985)
    assert (await share_row(db_session, data["id"])).open_count == 2

    events = (
        await db_session.scalars(select(AuditLog).where(AuditLog.entity_id == row.id).order_by(AuditLog.created_at))
    ).all()
    assert [e.action for e in events] == ["psychosocial.report_shared", "psychosocial.report_opened"]
    for e in events:
        assert "18" not in json.dumps(e.details) and "elevated" not in json.dumps(e.details).lower()


async def test_five_wrong_years_lock_the_link(client, db_session, env, therapist_auth_headers):
    _, aid = await completed(client, db_session, env, therapist_auth_headers)
    res = await share(client, therapist_auth_headers, aid)
    token, sid = report_token(res), res.json()["data"]["share"]["id"]
    for left in range(MAX_BIRTH_YEAR_ATTEMPTS - 1, 0, -1):
        r = await open_report(client, token, 2000)
        assert r.status_code == 403 and r.json()["detail"]["attempts_left"] == left
    locked = await open_report(client, token, 2000)
    assert locked.status_code == 423 and code_of(locked) == "LINK_LOCKED"
    # Even the right year cannot open it now; the provider shares again.
    assert (await open_report(client, token, 1985)).status_code == 423
    assert (await client.get(f"{API}/screener/report/{token}")).status_code == 423
    row = await share_row(db_session, sid)
    assert row.locked_at is not None and row.open_count == 0
    listed = await client.get(f"{API}/patients/{row.patient_id}/psychosocial/shares", headers=therapist_auth_headers)
    assert listed.json()["data"][0]["state"] == "locked"


async def test_no_birth_date_on_file_opens_with_the_link_alone(client, db_session, env, therapist_auth_headers):
    _, aid = await completed(client, db_session, env, therapist_auth_headers, dob=None)
    res = await share(client, therapist_auth_headers, aid)
    assert res.json()["data"]["share"]["birth_year_check"] is False
    token = report_token(res)
    assert (await client.get(f"{API}/screener/report/{token}")).json()["data"]["needs_birth_year"] is False
    assert (await open_report(client, token)).status_code == 200


async def test_what_can_be_shared(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    open_res = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    unanswered = await share(client, therapist_auth_headers, open_res.json()["data"]["assignment"]["id"])
    assert unanswered.status_code == 422 and code_of(unanswered) == "NOTHING_TO_SHARE"

    _, aid = await completed(client, db_session, env, therapist_auth_headers)
    cases = [
        ({"advice": "  ", "resources": []}, "EMPTY_SHARE"),
        ({"resources": ["horoscope"]}, "UNKNOWN_RESOURCE"),
        ({"custom_links": [{"title": "x", "url": "http://example.com"}]}, "INVALID_LINK"),
        ({"custom_links": [{"title": f"v{i}", "url": f"https://e{i}.com"} for i in range(4)]}, "TOO_MANY_LINKS"),
        ({"advice": "a" * 2001}, "ADVICE_TOO_LONG"),
    ]
    for body, code in cases:
        res = await share(client, therapist_auth_headers, aid, **body)
        assert res.status_code == 422 and code_of(res) == code, (code, res.text)
    assert (await share(client, therapist_auth_headers, aid, expires_in_days=31)).status_code == 422
    assert await db_session.scalar(
        select(func.count()).select_from(PsychosocialSharedReport).where(PsychosocialSharedReport.assignment_id == uuid.UUID(aid))
    ) == 0
    # Advice alone is enough.
    assert (await share(client, therapist_auth_headers, aid, resources=[])).status_code == 201


async def test_only_providers_who_see_the_result_can_share(
    client, db_session, env, therapist_auth_headers, auth_headers
):
    _, aid = await completed(client, db_session, env, therapist_auth_headers)
    assert (await share(client, auth_headers, aid)).status_code == 403  # admin: no results access
    assert (await client.get(f"{API}/psychosocial/share-options", headers=auth_headers)).status_code == 403

    # Own scope: a link someone else sent is invisible.
    await db_session.execute(
        update(PsychosocialAssignment).where(PsychosocialAssignment.id == uuid.UUID(aid)).values(assigned_by=env["admin"].id)
    )
    await db_session.commit()
    res = await share(client, therapist_auth_headers, aid)
    assert res.status_code == 404 and code_of(res) == "ASSIGNMENT_NOT_FOUND"
    await set_overrides(db_session, env["clinic"].id, env["therapist"].id, {"screening.view": "all"})
    assert (await share(client, therapist_auth_headers, aid)).status_code == 201


async def test_stop_sharing_expiry_and_clinic_off(client, db_session, env, therapist_auth_headers):
    _, aid = await completed(client, db_session, env, therapist_auth_headers, dob=None)
    first = await share(client, therapist_auth_headers, aid)
    second = await share(client, therapist_auth_headers, aid)
    t1, t2 = report_token(first), report_token(second)

    sid = first.json()["data"]["share"]["id"]
    res = await client.post(f"{API}/psychosocial/shares/{sid}/revoke", headers=therapist_auth_headers)
    assert res.status_code == 200 and res.json()["data"]["state"] == "revoked"
    gone = await open_report(client, t1)
    assert gone.status_code == 410 and code_of(gone) == "LINK_CANCELLED"
    assert (await share_row(db_session, sid)).revoked_at is not None
    assert (await open_report(client, t2)).status_code == 200  # other share unaffected

    await db_session.execute(
        update(PsychosocialSharedReport)
        .where(PsychosocialSharedReport.id == uuid.UUID(second.json()["data"]["share"]["id"]))
        .values(expires_at=utcnow() - timedelta(minutes=1))
    )
    await db_session.commit()
    expired = await open_report(client, t2)
    assert expired.status_code == 410 and code_of(expired) == "LINK_EXPIRED"

    third = await share(client, therapist_auth_headers, aid)
    clinic_id = env["clinic"].id

    async def product(value):
        await db_session.execute(
            update(WorkspaceProduct)
            .where(WorkspaceProduct.clinic_id == clinic_id, WorkspaceProduct.product_id == PRODUCT)
            .values(status=value)
        )
        await db_session.commit()

    try:
        await product(EntitlementStatus.DISABLED)
        off = await open_report(client, report_token(third))
        assert off.status_code == 403 and code_of(off) == "SCREENING_UNAVAILABLE"
    finally:
        await product(EntitlementStatus.ENABLED)
    assert (await client.get(f"{API}/screener/report/{'x' * 43}")).status_code == 404


async def test_deletion_removes_shared_reports(client, db_session, env, therapist_auth_headers, auth_headers):
    patient, aid = await completed(client, db_session, env, therapist_auth_headers)
    token = report_token(await share(client, therapist_auth_headers, aid))
    res = await client.post(
        f"{API}/patients/{patient.id}/psychosocial/data/delete", json={"confirm": "DELETE"}, headers=auth_headers
    )
    assert res.status_code == 200, res.text
    left = await db_session.scalar(
        select(func.count()).select_from(PsychosocialSharedReport).where(PsychosocialSharedReport.patient_id == patient.id)
    )
    assert left == 0
    assert (await open_report(client, token, 1985)).status_code == 404
