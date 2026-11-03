"""Anonymised clinic statistics and small-cell suppression (SRS 4.3.3, S-D-028)."""

from __future__ import annotations

import csv
import io
import random
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, update

from app.core.rbac import ROLE_TEMPLATES
from app.enums.permission import CapabilityScope
from app.enums.user import UserRole
from app.models.audit import AuditLog
from app.models.patient import Patient
from app.models.psychosocial import PsychosocialSession
from app.screening.aggregates import MIN_CELL, SessionRow, aggregate, referral_figure, suppress
from app.screening.registry import get_instrument
from app.screening.scoring import score
from app.services.psychosocial import serialise_result
from tests.screening.conftest import API, TEST_SURNAME_PREFIX, entitle, make_patient, set_overrides
from tests.screening.test_api import code_of
from tests.screening.test_trend_report import insert_completed, responses

STATS = f"{API}/psychosocial/aggregates"


# ---------------------------------------------------------------------------
# pure suppression
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "counts,expected",
    [
        ([0, 0, 0, 0, 0], [0, 0, 0, 0, 0]),
        ([10, 6, 5, 0, 0], [10, 6, 5, 0, 0]),
        # One small cell: the smallest other non-zero cell goes too.
        ([10, 6, 3, 0, 0], [10, None, None, 0, 0]),
        ([7, 0, 0, 0, 1], [None, 0, 0, 0, None]),
        # Two small cells already hide each other.
        ([10, 2, 3, 0, 0], [10, None, None, 0, 0]),
        ([4, 4, 9, 5], [None, None, 9, 5]),
    ],
)
def test_suppress(counts, expected):
    assert suppress(counts) == expected


def test_no_hidden_cell_can_be_worked_out_from_the_total():
    rng = random.Random(20261022)
    for _ in range(5000):
        counts = [rng.choice([0, 0, 1, 2, 3, 4, 5, 6, 9, 20]) for _ in range(rng.randint(4, 5))]
        if sum(counts) < MIN_CELL:
            continue
        shown = suppress(counts)
        hidden = [i for i, v in enumerate(shown) if v is None]
        assert len(hidden) != 1, counts
        assert not any(v is not None and 0 < v < MIN_CELL for v in shown), counts
        assert all(v is None or v == counts[i] for i, v in enumerate(shown))


@pytest.mark.parametrize(
    "flagged,total,expected",
    [
        (0, 10, (0, 0.0, False)),
        (5, 10, (5, 50.0, False)),
        (10, 10, (10, 100.0, False)),
        (2, 50, (None, None, True)),
        (48, 50, (None, None, True)),
        (0, 4, (None, None, True)),
        (7, 30, (7, 23.3, False)),
    ],
)
def test_referral_figure(flagged, total, expected):
    r = referral_figure(flagged, total)
    assert (r.count, r.rate_percent, r.suppressed) == expected


def row(instrument_id: str, total: int) -> SessionRow:
    inst = get_instrument(instrument_id)
    result = score(inst, responses(instrument_id, total))
    return SessionRow(instrument_id, result.referral_flag, serialise_result(result))


def test_aggregate_counts_bands_and_hides_small_groups():
    rows = [row("phq9", 2)] * 6 + [row("phq9", 12)] * 5 + [row("phq9", 22)] * 2 + [row("gad7", 3)] * 4
    by_id = {a.instrument_id: a for a in aggregate(rows, [get_instrument("phq9"), get_instrument("gad7")])}

    phq = by_id["phq9"]
    assert phq.completed == 13 and phq.too_few is False
    bands = [(b.label, b.count) for b in phq.scales[0].bands]
    # Severe (2) is small, so the smallest other non-zero band (Moderate, 5) is hidden with it.
    assert bands == [("None-minimal", 6), ("Mild", 0), ("Moderate", None), ("Moderately severe", 0), ("Severe", None)]
    # 7 flagged (5 Moderate + 2 Severe), 6 not: both 5 or more, so shown.
    assert (phq.referral.count, phq.referral.rate_percent) == (7, 53.8)

    gad = by_id["gad7"]
    assert gad.completed == 4 and gad.too_few is True
    assert all(b.suppressed for b in gad.scales[0].bands)
    assert gad.referral.suppressed


def test_aggregate_dass21_has_three_subscales():
    rows = [row("dass21", 0)] * 5
    [dass] = aggregate(rows, [get_instrument("dass21")])
    assert [s.scale_id for s in dass.scales] == ["depression", "anxiety", "stress"]
    for scale in dass.scales:
        assert [b.count for b in scale.bands] == [5, 0, 0, 0, 0]
    assert (dass.referral.count, dass.referral.rate_percent) == (0, 0.0)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@pytest.fixture
async def fresh(client, db_session):
    """A clinic of its own, so other tests' sessions never change the counts."""
    email = f"stats_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Stats", "email": email, "password": "password123", "first_name": "Neha", "last_name": "K"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    me = (await client.get(f"{API}/me", headers=headers)).json()["data"]
    clinic_id = uuid.UUID(me["active_workspace"]["id"])
    await entitle(db_session, clinic_id)
    yield {"headers": headers, "clinic_id": clinic_id, "user_id": uuid.UUID(me["user"]["id"])}
    await db_session.rollback()
    await db_session.execute(
        delete(Patient).where(Patient.clinic_id == clinic_id, Patient.last_name.like(f"{TEST_SURNAME_PREFIX}%"))
    )
    await db_session.commit()


async def seed(db, f, instrument_id, total, when, n=1):
    for _ in range(n):
        patient = await make_patient(db, f["clinic_id"])
        await insert_completed(db, f["clinic_id"], patient.id, f["user_id"], instrument_id, total, when)


def ist(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=timezone(timedelta(hours=5, minutes=30)))


async def test_admin_gets_suppressed_statistics_never_rows(client, db_session, fresh):
    when = ist(2026, 10, 10, 11, 0)
    await seed(db_session, fresh, "phq9", 2, when, n=6)
    await seed(db_session, fresh, "phq9", 12, when, n=5)
    await seed(db_session, fresh, "phq9", 22, when, n=2)
    await seed(db_session, fresh, "gad7", 12, when, n=3)

    res = await client.get(STATS, params={"from": "2026-10-01", "to": "2026-10-31"}, headers=fresh["headers"])
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert (data["date_from"], data["date_to"], data["min_cell"]) == ("2026-10-01", "2026-10-31", 5)
    phq, gad, dass = data["instruments"]
    assert phq["completed"] == 13
    assert [b["count"] for b in phq["scales"][0]["bands"]] == [6, 0, None, 0, None]
    assert phq["referral"] == {"count": 7, "rate_percent": 53.8, "suppressed": False}
    assert gad["completed"] == 3 and gad["too_few"] is True
    assert gad["referral"]["suppressed"] and all(b["count"] is None for b in gad["scales"][0]["bands"])
    assert dass["completed"] == 0

    # Nothing in the response can point at a person: no ids, no per-session fields.
    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                yield from keys(v)
        elif isinstance(node, list):
            for v in node:
                yield from keys(v)

    assert set(keys(data)) <= {
        "date_from", "date_to", "min_cell", "instruments", "instrument_id", "short_name", "completed",
        "too_few", "referral", "count", "rate_percent", "suppressed", "scales", "scale_id", "label", "bands",
    }
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", res.text)


async def test_filters_by_ist_date_range_and_screener(client, db_session, fresh):
    # 23:59 and 00:01 IST either side of midnight between 21 and 22 Oct.
    await seed(db_session, fresh, "phq9", 2, ist(2026, 10, 21, 23, 59), n=5)
    await seed(db_session, fresh, "phq9", 2, ist(2026, 10, 22, 0, 1), n=5)
    await seed(db_session, fresh, "gad7", 2, ist(2026, 10, 21, 12, 0), n=5)

    async def completed(params):
        res = await client.get(STATS, params=params, headers=fresh["headers"])
        assert res.status_code == 200, res.text
        return {i["instrument_id"]: i["completed"] for i in res.json()["data"]["instruments"]}

    assert await completed({"from": "2026-10-21", "to": "2026-10-21"}) == {"phq9": 5, "gad7": 5, "dass21": 0}
    assert await completed({"from": "2026-10-22", "to": "2026-10-22"}) == {"phq9": 5, "gad7": 0, "dass21": 0}
    assert await completed({"from": "2026-10-21", "to": "2026-10-22", "instrument": "phq9"}) == {"phq9": 10}


async def test_open_and_other_clinic_sessions_are_not_counted(client, db_session, fresh, env, therapist_auth_headers):
    when = ist(2026, 10, 10, 11, 0)
    await seed(db_session, fresh, "phq9", 2, when, n=5)
    # Another clinic's completed sessions on the same day.
    other = await make_patient(db_session, env["clinic"].id)
    for _ in range(5):
        await insert_completed(db_session, env["clinic"].id, other.id, env["admin"].id, "phq9", 2, when)
    # An open link in this clinic.
    patient = await make_patient(db_session, fresh["clinic_id"])
    res = await client.post(
        f"{API}/patients/{patient.id}/psychosocial/sessions", json={"instruments": ["phq9"]}, headers=fresh["headers"]
    )
    assert res.status_code == 201, res.text

    # Even with a completion time written on it, a session that is not completed does not count.
    await db_session.execute(
        update(PsychosocialSession)
        .where(PsychosocialSession.patient_id == patient.id)
        .values(completed_at=when, status="in_progress")
    )
    await db_session.commit()

    res = await client.get(STATS, params={"from": "2026-10-01", "to": "2026-10-31"}, headers=fresh["headers"])
    assert res.json()["data"]["instruments"][0]["completed"] == 5


async def test_default_range_and_invalid_input(client, fresh):
    res = await client.get(STATS, headers=fresh["headers"])
    assert res.status_code == 200
    data = res.json()["data"]
    span = date.fromisoformat(data["date_to"]) - date.fromisoformat(data["date_from"])
    assert span.days == 89

    bad = [
        {"from": "2026-10-10", "to": "2026-10-01"},
        {"from": "2020-01-01", "to": "2026-10-01"},
    ]
    for params in bad:
        res = await client.get(STATS, params=params, headers=fresh["headers"])
        assert res.status_code == 422 and code_of(res) == "INVALID_RANGE", params
    for params in ({"from": "10/01/2026"}, {"instrument": "bdi2"}):
        assert (await client.get(STATS, params=params, headers=fresh["headers"])).status_code == 422


async def test_csv_matches_the_screen_and_is_audited(client, db_session, fresh):
    when = ist(2026, 10, 10, 11, 0)
    await seed(db_session, fresh, "phq9", 2, when, n=6)
    await seed(db_session, fresh, "phq9", 12, when, n=1)
    params = {"from": "2026-10-01", "to": "2026-10-31", "instrument": "phq9"}

    res = await client.get(f"{STATS}.csv", params=params, headers=fresh["headers"])
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/csv")
    assert res.headers["cache-control"] == "no-store"
    assert 'filename="screening-statistics-2026-10-01-to-2026-10-31.csv"' in res.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(res.text)))
    assert rows[0] == ["From", "To", "Screener", "Scale", "Measure", "Value"]
    values = {(r[3], r[4]): r[5] for r in rows[1:]}
    assert values[("", "Completed sessions")] == "7"
    # 1 flagged of 7 is small: hidden, in the file too.
    assert values[("", "Referral recommended")] == "hidden"
    assert values[("", "Referral recommended (%)")] == "hidden"
    assert values[("PHQ-9", "Band: None-minimal")] == "hidden"  # secondary suppression
    assert values[("PHQ-9", "Band: Moderate")] == "hidden"
    assert values[("PHQ-9", "Band: Severe")] == "0"
    assert all(r[0:2] == ["2026-10-01", "2026-10-31"] for r in rows[1:])

    [event] = (
        await db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "psychosocial.aggregates_exported", AuditLog.clinic_id == fresh["clinic_id"]
            )
        )
    ).all()
    assert event.details == {"from": "2026-10-01", "to": "2026-10-31", "instrument": "phq9"}


async def test_only_holders_of_screening_aggregates_see_statistics(
    client, db_session, env, auth_headers, therapist_auth_headers
):
    # A physio with full results rights still gets no clinic statistics.
    assert (await client.get(STATS, headers=therapist_auth_headers)).status_code == 403
    assert (await client.get(f"{STATS}.csv", headers=therapist_auth_headers)).status_code == 403
    assert (await client.get(STATS, headers=auth_headers)).status_code == 200
    await set_overrides(db_session, env["clinic"].id, env["admin"].id, {"screening.aggregates": "none"})
    assert (await client.get(STATS, headers=auth_headers)).status_code == 403


async def test_statistics_need_the_product(client):
    email = f"noent_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "No Ent", "email": email, "password": "password123", "first_name": "A", "last_name": "B"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    res = await client.get(STATS, headers=headers)
    assert res.status_code == 403 and code_of(res) == "PRODUCT_NOT_ENTITLED"


def test_aggregates_is_admin_only_by_default():
    assert ROLE_TEMPLATES[UserRole.ADMIN]["screening.aggregates"] == CapabilityScope.ALL
    assert ROLE_TEMPLATES[UserRole.THERAPIST]["screening.aggregates"] == CapabilityScope.NONE
    assert ROLE_TEMPLATES[UserRole.FRONT_DESK]["screening.aggregates"] == CapabilityScope.NONE
