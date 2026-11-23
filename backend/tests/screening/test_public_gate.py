"""U3: every public patient link (screener, re-consent, shared report) stops
when the clinic or its organisation is suspended, or the screening
entitlement is outside its validity window. The patient only ever sees
SCREENING_UNAVAILABLE, never a suspension or organisation detail.

T3-a #4: link errors that follow a matched token carry clinic_name; the
not-found and unavailable errors never do.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.enums.organization import ClinicStatus, OrganizationStatus
from app.models.clinic import Clinic
from app.models.organization import Organization
from app.models.product import WorkspaceProduct
from app.models.psychosocial import PsychosocialAssignment, PsychosocialSession
from app.services.psychosocial import utcnow
from tests.screening.conftest import API, PRODUCT, make_patient
from tests.screening.test_api import answer, assign, code_of, consent, submit, token_of
from tests.screening.test_reconsent import request_link, token_from, withdrawn_patient
from tests.screening.test_share import completed, open_report, report_token, share

BLOCKS = ["clinic_suspended", "org_suspended", "valid_until_past", "valid_from_future"]
LEAK_WORDS = ("suspend", "organisation", "organization", "workspace")


async def _apply(db, clinic_id, block: str | None):
    """Apply one block (or undo all of them with None)."""
    clinic = await db.get(Clinic, clinic_id)
    await db.execute(
        update(Clinic).where(Clinic.id == clinic_id).values(
            status=ClinicStatus.SUSPENDED if block == "clinic_suspended" else ClinicStatus.ACTIVE
        )
    )
    await db.execute(
        update(Organization).where(Organization.id == clinic.organization_id).values(
            status=OrganizationStatus.SUSPENDED if block == "org_suspended" else OrganizationStatus.ACTIVE
        )
    )
    now = utcnow()
    await db.execute(
        update(WorkspaceProduct)
        .where(WorkspaceProduct.clinic_id == clinic_id, WorkspaceProduct.product_id == PRODUCT)
        .values(
            valid_until=now - timedelta(minutes=1) if block == "valid_until_past" else None,
            valid_from=now + timedelta(days=1) if block == "valid_from_future" else None,
        )
    )
    await db.commit()
    db.expire_all()


def _unavailable(res) -> None:
    assert res.status_code == 403, res.text
    assert code_of(res) == "SCREENING_UNAVAILABLE"
    body = json.dumps(res.json()).lower()
    assert "clinic_name" not in body
    for word in LEAK_WORDS:
        assert word not in body, word


@pytest.mark.parametrize("block", BLOCKS)
async def test_screener_link_collects_nothing_when_blocked(block, client, db_session, env, therapist_auth_headers):
    clinic_id = env["clinic"].id
    patient = await make_patient(db_session, clinic_id)
    patient_id = patient.id  # _apply expires ORM objects
    res = await assign(client, therapist_auth_headers, patient_id, ["phq9"])
    token = token_of(res)
    await consent(client, token)
    try:
        await _apply(db_session, clinic_id, block)
        _unavailable(await client.get(f"{API}/screener/{token}"))
        _unavailable(await answer(client, token, "phq9", "phq9_1", 3))
        _unavailable(await submit(client, token, "phq9"))
        _unavailable(await client.post(f"{API}/screener/{token}/withdraw"))
        responses = (
            await db_session.scalars(
                select(PsychosocialSession.responses)
                .join(PsychosocialAssignment, PsychosocialAssignment.id == PsychosocialSession.assignment_id)
                .where(PsychosocialAssignment.patient_id == patient_id)
            )
        ).all()
        assert responses and all(not (r or {}) for r in responses)
    finally:
        await _apply(db_session, clinic_id, None)
    assert (await client.get(f"{API}/screener/{token}")).status_code == 200


@pytest.mark.parametrize("block", BLOCKS)
async def test_reconsent_link_blocked(block, client, db_session, env, therapist_auth_headers):
    clinic_id = env["clinic"].id
    patient = await withdrawn_patient(client, db_session, env, therapist_auth_headers)
    token = token_from(await request_link(client, therapist_auth_headers, patient.id))
    try:
        await _apply(db_session, clinic_id, block)
        _unavailable(await client.get(f"{API}/screener/reconsent/{token}"))
        _unavailable(
            await client.post(
                f"{API}/screener/reconsent/{token}/answer", json={"accept": False, "text_version": None}
            )
        )
    finally:
        await _apply(db_session, clinic_id, None)
    assert (await client.get(f"{API}/screener/reconsent/{token}")).status_code == 200


@pytest.mark.parametrize("block", BLOCKS)
async def test_shared_report_blocked(block, client, db_session, env, therapist_auth_headers):
    clinic_id = env["clinic"].id
    _, assignment_id = await completed(client, db_session, env, therapist_auth_headers)
    token = report_token(await share(client, therapist_auth_headers, assignment_id))
    try:
        await _apply(db_session, clinic_id, block)
        _unavailable(await client.get(f"{API}/screener/report/{token}"))
        _unavailable(await open_report(client, token, 1985))
    finally:
        await _apply(db_session, clinic_id, None)
    assert (await client.get(f"{API}/screener/report/{token}")).status_code == 200


# ---------------------------------------------------------------------------
# T3-a #4: clinic name on matched-link errors only
# ---------------------------------------------------------------------------
async def test_link_errors_carry_clinic_name_only_after_a_match(client, db_session, env, therapist_auth_headers):
    clinic_name = env["clinic"].name
    patient = await make_patient(db_session, env["clinic"].id)
    token = token_of(await assign(client, therapist_auth_headers, patient.id, ["phq9"]))
    await consent(client, token)
    for i in range(1, 10):
        await answer(client, token, "phq9", f"phq9_{i}", 0)
    await submit(client, token, "phq9")

    done = await client.get(f"{API}/screener/{token}")
    assert done.status_code == 409 and code_of(done) == "ALREADY_COMPLETED"
    detail = done.json()["detail"]
    assert detail["clinic_name"] == clinic_name
    assert set(detail) == {"code", "message", "clinic_name"}  # nothing about the patient

    missing = await client.get(f"{API}/screener/{'x' * 43}")
    assert missing.status_code == 404 and "clinic_name" not in json.dumps(missing.json())

    patient2 = await make_patient(db_session, env["clinic"].id)
    token2 = token_of(await assign(client, therapist_auth_headers, patient2.id, ["phq9"]))
    await db_session.execute(
        update(PsychosocialAssignment)
        .where(PsychosocialAssignment.patient_id == patient2.id)
        .values(expires_at=utcnow() - timedelta(minutes=1))
    )
    await db_session.commit()
    expired = await client.get(f"{API}/screener/{token2}")
    assert expired.status_code == 410 and code_of(expired) == "LINK_EXPIRED"
    assert expired.json()["detail"]["clinic_name"] == clinic_name
