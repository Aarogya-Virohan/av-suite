"""Clinic configuration: default repeat per screener and the threshold view (SRS 4.3.2, S-D-027)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.rbac import ROLE_TEMPLATES
from app.enums.permission import CapabilityScope
from app.enums.user import UserRole
from app.models.audit import AuditLog
from app.models.psychosocial import PsychosocialClinicSetting
from app.screening.registry import list_instruments
from app.screening.scoring import score_scale
from app.screening.thresholds import thresholds_for
from tests.screening.conftest import API, entitle, make_patient, set_overrides
from tests.screening.test_api import code_of
from tests.screening.test_schedules import schedules_of, send

SETTINGS = f"{API}/psychosocial/settings"


@pytest.fixture
async def clean_settings(db_session, env):
    clinic_id = env["clinic"].id

    async def wipe():
        await db_session.rollback()
        await db_session.execute(
            delete(PsychosocialClinicSetting).where(PsychosocialClinicSetting.clinic_id == clinic_id)
        )
        await db_session.commit()

    await wipe()
    yield
    await wipe()


async def put(client, headers, instrument_id, body):
    return await client.put(f"{SETTINGS}/{instrument_id}", json=body, headers=headers)


def by_id(settings: dict) -> dict:
    return {i["instrument_id"]: i for i in settings["instruments"]}


async def instrument_defaults(client, headers) -> dict:
    res = await client.get(f"{API}/psychosocial/instruments", headers=headers)
    assert res.status_code == 200, res.text
    return {i["id"]: i["default_repeat_weeks"] for i in res.json()["data"]}


# ---------------------------------------------------------------------------
# threshold view (pure)
# ---------------------------------------------------------------------------
def test_threshold_view_matches_published_referral_rules():
    views = {inst.id: thresholds_for(inst) for inst in list_instruments()}

    phq9 = views["phq9"].scales[0]
    assert (phq9.referral_band, phq9.referral_min_score) == ("Moderate", 10)
    gad7 = views["gad7"].scales[0]
    assert (gad7.referral_band, gad7.referral_min_score) == ("Moderate", 10)
    dass = {s.scale_id: (s.referral_band, s.referral_min_score) for s in views["dass21"].scales}
    assert dass == {"depression": ("Severe", 21), "anxiety": ("Severe", 15), "stress": ("Severe", 26)}

    [rule] = views["phq9"].risk_rules
    assert (rule.item_number, rule.min_value, rule.min_label) == (9, 1, "Several days")
    assert views["gad7"].risk_rules == () and views["dass21"].risk_rules == ()
    for view in views.values():
        assert view.source


def test_threshold_view_agrees_with_the_scoring_engine_at_every_score():
    """What the admin is shown must be exactly what scoring does."""
    for inst in list_instruments():
        view = {s.scale_id: s for s in thresholds_for(inst).scales}
        for scale in inst.scales:
            shown = view[scale.id]
            for raw in range(0, scale.max_score // scale.multiplier + 1):
                responses = {}
                left = raw
                for item_id in scale.item_ids:
                    responses[item_id] = min(left, 3)
                    left -= responses[item_id]
                result = score_scale(scale, responses)
                assert result.referral == (result.score >= shown.referral_min_score), (inst.id, scale.id, raw)
                band = next(b for b in shown.bands if b.label == result.band_label)
                assert band.refers == result.referral
                assert band.min_score <= result.score and (band.max_score is None or result.score <= band.max_score)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
async def test_admin_reads_settings_with_fixed_thresholds(client, env, clean_settings, auth_headers):
    res = await client.get(SETTINGS, headers=auth_headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["thresholds_editable"] is False
    rows = by_id(data)
    assert list(rows) == ["phq9", "gad7", "dass21"]
    for row in rows.values():
        assert row["default_repeat_weeks"] is None
        assert row["updated_at"] is None and row["updated_by_name"] is None
    assert rows["phq9"]["scales"][0]["referral_min_score"] == 10
    assert [b["refers"] for b in rows["phq9"]["scales"][0]["bands"]] == [False, False, True, True, True]
    assert rows["phq9"]["risk_rules"][0]["item_number"] == 9


async def test_admin_sets_default_and_the_assign_form_gets_it(
    client, db_session, env, clean_settings, auth_headers, therapist_auth_headers
):
    assert await instrument_defaults(client, therapist_auth_headers) == {"phq9": None, "gad7": None, "dass21": None}

    res = await put(client, auth_headers, "phq9", {"default_repeat_weeks": 4})
    assert res.status_code == 200, res.text
    phq9 = by_id(res.json()["data"])["phq9"]
    assert phq9["default_repeat_weeks"] == 4
    assert phq9["updated_by_name"] and phq9["updated_at"]

    assert await instrument_defaults(client, therapist_auth_headers) == {"phq9": 4, "gad7": None, "dass21": None}

    # Saved in the database, one row for the clinic.
    rows = (
        await db_session.scalars(
            select(PsychosocialClinicSetting).where(PsychosocialClinicSetting.clinic_id == env["clinic"].id)
        )
    ).all()
    assert [(r.instrument_id, r.default_repeat_weeks, r.updated_by) for r in rows] == [
        ("phq9", 4, env["admin"].id)
    ]

    # Change, then the same value again, then back to just once.
    assert (await put(client, auth_headers, "phq9", {"default_repeat_weeks": 8})).status_code == 200
    assert (await put(client, auth_headers, "phq9", {"default_repeat_weeks": 8})).status_code == 200
    assert (await put(client, auth_headers, "phq9", {"default_repeat_weeks": None})).status_code == 200
    assert (await instrument_defaults(client, therapist_auth_headers))["phq9"] is None

    events = (
        await db_session.scalars(
            select(AuditLog)
            .where(AuditLog.action == "psychosocial.settings_updated", AuditLog.clinic_id == env["clinic"].id)
            .order_by(AuditLog.created_at, AuditLog.id)
        )
    ).all()
    changes = [(e.details["default_repeat_weeks_before"], e.details["default_repeat_weeks_after"]) for e in events[-3:]]
    # The repeated 8 wrote nothing.
    assert changes == [(None, 4), (4, 8), (8, None)]
    assert all(e.details["instrument_id"] == "phq9" for e in events[-3:])


async def test_changing_the_default_leaves_existing_schedules_alone(
    client, db_session, env, clean_settings, auth_headers, therapist_auth_headers
):
    patient = await make_patient(db_session, env["clinic"].id)
    assert (await send(client, therapist_auth_headers, patient.id, ["phq9"], weeks=4)).status_code == 201
    assert (await put(client, auth_headers, "phq9", {"default_repeat_weeks": 12})).status_code == 200
    [row] = await schedules_of(client, therapist_auth_headers, patient.id)
    assert row["interval_days"] == 28


@pytest.mark.parametrize(
    "instrument_id,body",
    [
        ("phq9", {"default_repeat_weeks": 0}),
        ("phq9", {"default_repeat_weeks": 53}),
        ("phq9", {"default_repeat_weeks": "four"}),
        ("phq9", {}),
        ("phq9", {"default_repeat_weeks": 4, "referral_min_score": 5}),
        ("bdi2", {"default_repeat_weeks": 4}),
    ],
)
async def test_invalid_setting_is_rejected(client, env, clean_settings, auth_headers, instrument_id, body):
    res = await put(client, auth_headers, instrument_id, body)
    assert res.status_code == 422, res.text


async def test_only_holders_of_screening_configure_can_configure(
    client, db_session, env, clean_settings, auth_headers, therapist_auth_headers
):
    # A physio with send and results rights still cannot configure.
    assert (await client.get(SETTINGS, headers=therapist_auth_headers)).status_code == 403
    res = await put(client, therapist_auth_headers, "phq9", {"default_repeat_weeks": 4})
    assert res.status_code == 403
    assert (await instrument_defaults(client, auth_headers))["phq9"] is None

    # Granted explicitly, it works.
    await set_overrides(
        db_session,
        env["clinic"].id,
        env["therapist"].id,
        {"screening.assign": "all", "screening.view": "own", "screening.refer": "own", "screening.configure": "all"},
    )
    assert (await put(client, therapist_auth_headers, "phq9", {"default_repeat_weeks": 6})).status_code == 200

    # And an admin whose grant is removed is refused.
    await set_overrides(db_session, env["clinic"].id, env["admin"].id, {"screening.configure": "none"})
    assert (await client.get(SETTINGS, headers=auth_headers)).status_code == 403


async def test_settings_need_the_product(client):
    email = f"noent_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "No Ent", "email": email, "password": "password123", "first_name": "A", "last_name": "B"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    res = await client.get(SETTINGS, headers=headers)
    assert res.status_code == 403
    assert code_of(res) == "PRODUCT_NOT_ENTITLED"


async def test_settings_are_per_clinic(client, db_session, env, clean_settings, auth_headers):
    email = f"other_{uuid.uuid4().hex[:8]}@test.com"
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Other", "email": email, "password": "password123", "first_name": "A", "last_name": "B"},
    )
    other = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    other_clinic = uuid.UUID(
        (await client.get(f"{API}/me", headers=other)).json()["data"]["active_workspace"]["id"]
    )
    await entitle(db_session, other_clinic)

    assert (await put(client, other, "gad7", {"default_repeat_weeks": 2})).status_code == 200
    assert (await instrument_defaults(client, auth_headers))["gad7"] is None
    assert by_id((await client.get(SETTINGS, headers=auth_headers)).json()["data"])["gad7"]["default_repeat_weeks"] is None
    assert (await instrument_defaults(client, other))["gad7"] == 2

    await db_session.execute(
        delete(PsychosocialClinicSetting).where(PsychosocialClinicSetting.clinic_id == other_clinic)
    )
    await db_session.commit()


async def test_database_rejects_an_out_of_range_default(db_session, env, clean_settings):
    db_session.add(
        PsychosocialClinicSetting(
            id=uuid.uuid4(), clinic_id=env["clinic"].id, instrument_id="phq9", default_repeat_weeks=0
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


def test_configure_is_admin_only_by_default():
    assert ROLE_TEMPLATES[UserRole.ADMIN]["screening.configure"] == CapabilityScope.ALL
    assert ROLE_TEMPLATES[UserRole.THERAPIST]["screening.configure"] == CapabilityScope.NONE
    assert ROLE_TEMPLATES[UserRole.FRONT_DESK]["screening.configure"] == CapabilityScope.NONE
