"""Score trend (SRS 4.1.2, 3.5) and the PDF summary (SRS 4.1.4), S-D-025."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.enums.permission import CapabilityScope
from app.models.audit import AuditLog
from app.models.psychosocial import PsychosocialAssignment, PsychosocialSession
from app.screening.registry import get_instrument
from app.screening.scoring import score
from app.screening.trend import build_series
from app.services import psychosocial_report as report
from app.services.psychosocial import hash_token, serialise_result
from tests.screening.conftest import API, entitle, make_patient
from tests.screening.test_api import answer_all, assign, consent, submit, token_of

pytestmark = pytest.mark.asyncio

START = datetime(2024, 11, 5, 6, 0, tzinfo=timezone.utc)


def responses(instrument_id: str, total: int) -> dict[str, int]:
    """Scored answers summing to ``total`` (each 0-3), item 9 kept at 0 for PHQ-9."""
    items = [i for i in get_instrument(instrument_id).scored_items if i.id != "phq9_9"]
    out = {i.id: 0 for i in get_instrument(instrument_id).scored_items}
    for item in items:
        out[item.id] = min(3, total)
        total -= out[item.id]
    assert total == 0
    return out


def fake_session(instrument_id: str, total: int, when: datetime, status: str = "completed"):
    instrument = get_instrument(instrument_id)
    result = score(instrument, responses(instrument_id, total))
    return SimpleNamespace(
        id=uuid.uuid4(),
        instrument_id=instrument_id,
        instrument_version=instrument.version,
        completed_at=when if status == "completed" else None,
        result=serialise_result(result) if status == "completed" else None,
        referral_flag=result.referral_flag,
        risk_item_flag=result.risk_item_flag,
    )


async def insert_completed(db, clinic_id, patient_id, assigned_by, instrument_id, total, when):
    """A completed session written straight to the database, back-dated."""
    instrument = get_instrument(instrument_id)
    result = score(instrument, responses(instrument_id, total))
    assignment = PsychosocialAssignment(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        assigned_by=assigned_by,
        token_hash=hash_token(uuid.uuid4().hex),
        status="completed",
        expires_at=when + timedelta(days=7),
    )
    assignment.sessions = [
        PsychosocialSession(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patient_id,
            assigned_by=assigned_by,
            position=0,
            instrument_id=instrument_id,
            instrument_version=instrument.version,
            status="completed",
            responses=responses(instrument_id, total),
            started_at=when,
            completed_at=when,
            result=serialise_result(result),
            referral_flag=result.referral_flag,
            risk_item_flag=result.risk_item_flag,
        )
    ]
    db.add(assignment)
    await db.commit()
    return assignment.sessions[0].id


# ---------------------------------------------------------------------------
# pure trend
# ---------------------------------------------------------------------------
def test_series_are_ordered_by_instrument_then_time():
    sessions = [
        fake_session("gad7", 12, START + timedelta(days=40)),
        fake_session("phq9", 5, START + timedelta(days=60)),
        fake_session("phq9", 13, START),
        fake_session("dass21", 30, START + timedelta(days=10)),
        fake_session("phq9", 0, START, status="in_progress"),
    ]
    series = build_series(sessions)
    assert [(s.instrument_id, s.scale_id) for s in series] == [
        ("phq9", "total"),
        ("gad7", "total"),
        ("dass21", "depression"),
        ("dass21", "anxiety"),
        ("dass21", "stress"),
    ]
    phq = series[0]
    assert [p.score for p in phq.points] == [13, 5]  # oldest first, unfinished left out
    assert [p.band_label for p in phq.points] == ["Moderate", "Mild"]
    assert [p.referral for p in phq.points] == [True, False]


def test_bands_and_referral_lines_match_published_thresholds():
    sessions = [
        fake_session("phq9", 1, START),
        fake_session("gad7", 1, START),
        fake_session("dass21", 1, START),
    ]
    by_key = {(s.instrument_id, s.scale_id): s for s in build_series(sessions)}
    assert {k: s.referral_from for k, s in by_key.items()} == {
        ("phq9", "total"): 10,
        ("gad7", "total"): 10,
        ("dass21", "depression"): 21,
        ("dass21", "anxiety"): 15,
        ("dass21", "stress"): 26,
    }
    for s in by_key.values():
        assert s.bands[0].min_score == 0
        assert s.bands[-1].max_score == s.max_score
        for prev, nxt in zip(s.bands, s.bands[1:]):
            assert nxt.min_score == prev.max_score + 1


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
async def test_trend_api_respects_scope_and_order(
    client, db_session, env, auth_headers, therapist_auth_headers
):
    clinic_id = env["clinic"].id
    patient = await make_patient(db_session, clinic_id)
    therapist_id, admin_id = env["therapist"].id, env["admin"].id
    await insert_completed(db_session, clinic_id, patient.id, therapist_id, "phq9", 13, START)
    await insert_completed(db_session, clinic_id, patient.id, therapist_id, "phq9", 5, START + timedelta(days=30))
    # Sent by the admin: hidden from a therapist with OWN scope.
    await insert_completed(db_session, clinic_id, patient.id, admin_id, "gad7", 12, START + timedelta(days=5))

    res = await client.get(f"{API}/patients/{patient.id}/psychosocial/trend", headers=therapist_auth_headers)
    assert res.status_code == 200, res.text
    series = res.json()["data"]["series"]
    assert [(s["instrument_id"], [p["score"] for p in s["points"]]) for s in series] == [("phq9", [13, 5])]
    assert series[0]["referral_from"] == 10 and series[0]["max_score"] == 27

    # The admin cannot read results (SRS 3.2).
    assert (
        await client.get(f"{API}/patients/{patient.id}/psychosocial/trend", headers=auth_headers)
    ).status_code == 403


async def test_trend_and_report_are_clinic_isolated(client, db_session, env, therapist_auth_headers):
    from app.models.user import User
    from tests.screening.conftest import set_overrides

    patient = await make_patient(db_session, env["clinic"].id)
    await insert_completed(db_session, env["clinic"].id, patient.id, env["therapist"].id, "phq9", 9, START)
    email = f"tr_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Other", "email": email, "password": "password123", "first_name": "O", "last_name": "C"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    other = await db_session.scalar(select(User).where(User.email == email))
    await entitle(db_session, other.clinic_id)
    await set_overrides(db_session, other.clinic_id, other.id, {"screening.view": "all"})
    assert (await client.get(f"{API}/patients/{patient.id}/psychosocial/trend", headers=headers)).status_code == 404
    assert (await client.get(f"{API}/patients/{patient.id}/psychosocial/report.pdf", headers=headers)).status_code == 404


async def test_twenty_four_months_of_history(client, db_session, env, therapist_auth_headers):
    clinic_id = env["clinic"].id
    patient = await make_patient(db_session, clinic_id)
    totals = [(m * 5) % 25 for m in range(24)]  # item 9 stays 0, so at most 24
    for m, total in enumerate(totals):
        await insert_completed(
            db_session, clinic_id, patient.id, env["therapist"].id, "phq9", total, START + timedelta(days=30 * m)
        )
    res = await client.get(f"{API}/patients/{patient.id}/psychosocial/trend", headers=therapist_auth_headers)
    points = res.json()["data"]["series"][0]["points"]
    assert [p["score"] for p in points] == totals
    dates = [p["completed_at"] for p in points]
    assert dates == sorted(dates)

    started = time.perf_counter()
    pdf = await client.get(f"{API}/patients/{patient.id}/psychosocial/report.pdf", headers=therapist_auth_headers)
    elapsed = time.perf_counter() - started
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert elapsed < 15, f"PDF took {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
async def test_report_pdf_download_and_audit(client, db_session, env, auth_headers, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id, first="Kavya")
    res = await assign(client, therapist_auth_headers, patient.id, ["phq9"])
    token = token_of(res)
    session_id = res.json()["data"]["assignment"]["sessions"][0]["id"]
    await consent(client, token)
    await answer_all(client, token, "phq9", [2, 2, 2, 2, 2, 0, 0, 0, 0])
    assert (await submit(client, token, "phq9")).status_code == 200
    logged = await client.post(
        f"{API}/psychosocial/sessions/{session_id}/referral-actions",
        json={"action": "referred_gp"},
        headers=therapist_auth_headers,
    )
    assert logged.status_code == 201

    pdf = await client.get(f"{API}/patients/{patient.id}/psychosocial/report.pdf", headers=therapist_auth_headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["cache-control"] == "no-store"
    slug = f"kavya-{patient.last_name.lower()}"
    assert f'filename="screening-summary-{slug}-' in pdf.headers["content-disposition"]
    assert pdf.content.startswith(b"%PDF") and len(pdf.content) > 5000

    events = (
        await db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "psychosocial.report_generated", AuditLog.entity_id == patient.id
            )
        )
    ).all()
    assert len(events) == 1
    assert events[0].user_id == env["therapist"].id
    assert events[0].details == {"patient_id": str(patient.id), "sessions": 1}

    # Admins cannot download individual results (SRS 3.2).
    denied = await client.get(f"{API}/patients/{patient.id}/psychosocial/report.pdf", headers=auth_headers)
    assert denied.status_code == 403


async def test_report_content(db_session, env):
    clinic_id = env["clinic"].id
    patient = await make_patient(db_session, clinic_id, first="Ishaan")
    therapist_id, admin_id = env["therapist"].id, env["admin"].id
    await insert_completed(db_session, clinic_id, patient.id, therapist_id, "phq9", 13, START)
    await insert_completed(db_session, clinic_id, patient.id, therapist_id, "gad7", 4, START + timedelta(days=2))
    await insert_completed(db_session, clinic_id, patient.id, admin_id, "dass21", 30, START + timedelta(days=3))

    full = await report.build_report_data(
        db_session, clinic_id=clinic_id, patient_id=patient.id, scope=CapabilityScope.ALL, user_id=therapist_id
    )
    html = report.build_report_html(full)
    assert f"Ishaan {patient.last_name}" in html
    assert "<strong>13</strong> / 27 &middot; Moderate" in html
    assert "<strong>4</strong> / 21 &middot; None-minimal" in html
    assert "Depression: <strong>" in html
    assert "Referral from 10" in html  # PHQ-9 trend chart
    assert "No referral actions recorded." in html
    assert "includes only the screenings sent by" not in html
    assert len(full.sessions) == 3

    own = await report.build_report_data(
        db_session, clinic_id=clinic_id, patient_id=patient.id, scope=CapabilityScope.OWN, user_id=therapist_id
    )
    assert [r.short_name for r in own.sessions] == ["PHQ-9", "GAD-7"]
    assert "includes only the screenings sent by" in report.build_report_html(own)


async def test_report_for_patient_without_results(client, db_session, env, therapist_auth_headers):
    patient = await make_patient(db_session, env["clinic"].id)
    pdf = await client.get(f"{API}/patients/{patient.id}/psychosocial/report.pdf", headers=therapist_auth_headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    data = await report.build_report_data(
        db_session,
        clinic_id=env["clinic"].id,
        patient_id=patient.id,
        scope=CapabilityScope.OWN,
        user_id=env["therapist"].id,
    )
    assert "No completed screenings yet." in report.build_report_html(data)


def test_report_text_escapes_user_input():
    data = report.ReportData(
        report_id="PS-1",
        clinic_name="<b>Clinic</b>",
        patient_name="<script>x</script>",
        patient_details=[],
        generated_at=START,
        generated_by="A & B",
        own_scope=False,
        series=[],
        referrals=[
            report.ReferralRow(START, "PHQ-9", START, "Other", "<img src=x>", "Dr <i>")
        ],
    )
    html = report.build_report_html(data)
    for raw in ("<script>x</script>", "<img src=x>", "<b>Clinic</b>", "Dr <i>"):
        assert raw not in html
    assert "&lt;script&gt;" in html
