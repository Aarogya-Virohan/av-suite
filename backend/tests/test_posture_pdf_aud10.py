"""
AUD-10 (23 Nov 2026) and POS-10 (24 Nov 2026): POST /api/v1/posture/report/pdf
takes a report id and renders only the report saved for the signed-in clinic.
Bad input = 422 with a fixed message; an unexpected failure (or a stored copy
that cannot be rendered) = 500 with a fixed message; exception text never
reaches the client; nothing the client sends is rendered.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import posture as posture_api
from app.enums.user import UserRole
from app.services import posture_report_store as store
from tests.test_posture_auth import make_user
from tests.test_posture_patient_link import _clinic_for, _patient

pytestmark = pytest.mark.asyncio

URL = "/api/v1/posture/report/pdf"



def _report(name: str = "Valid Payload", report_id: str | None = None) -> dict:
    # report_id is unique in the table and test rows persist, so make it fresh.
    report_id = report_id or f"PT-20261124-{uuid.uuid4().hex[:8].upper()}"
    return {
        "patient": {"name": name, "age": 30, "gender": "Male", "caseRef": "SPC-000007"},
        "reportId": report_id,
        "analysisVersion": "2026-11-21.1",
        "views": {"side": {"measurements": []}, "front": {}, "back": None},
        "signature": {"regions": []},
        "synthesis": {},
    }


async def _save(db: AsyncSession, headers: dict, report: dict, number: int = 7):
    clinic = await _clinic_for(db, headers)
    patient = await _patient(db, clinic, number=number)
    row = await store.save_report(db, clinic_id=clinic.id, patient_id=patient.id, user_id=None, report=report)
    await db.commit()
    return row


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"patient": "x"},
        {"views": {}, "patient": {}},
        {"views": {"side": "x"}},
        {"views": {}, "reportId": 5},
        {"reportId": ""},
        {"reportId": "   "},
        {"reportId": None},
        {"reportId": ["PT-1"]},
    ],
)
async def test_bad_body_is_422_with_a_fixed_message(client: AsyncClient, db_session: AsyncSession, payload):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    response = await client.post(URL, headers=headers, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": posture_api.PDF_BAD_PAYLOAD}


async def test_unexpected_failure_is_500_without_exception_text(
    client: AsyncClient, db_session: AsyncSession, monkeypatch, caplog
):
    def boom(*_a, **_k):
        raise RuntimeError("secret internal detail /app/path")

    monkeypatch.setattr(posture_api, "generate_posture_pdf", boom)
    headers = await make_user(db_session, role=UserRole.ADMIN)
    report = _report()
    await _save(db_session, headers, report)
    response = await client.post(URL, headers=headers, json={"reportId": report["reportId"]})
    assert response.status_code == 500
    assert response.json() == {"detail": posture_api.PDF_FAILED}
    assert "secret internal detail" not in response.text
    assert "secret internal detail" in caplog.text


async def test_unreadable_stored_copy_is_500_with_the_fixed_message(client: AsyncClient, db_session: AsyncSession):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    bad = {"reportId": f"PT-20261124-{uuid.uuid4().hex[:8].upper()}", "views": [], "patient": "x"}
    await _save(db_session, headers, bad)
    response = await client.post(URL, headers=headers, json={"reportId": bad["reportId"]})
    assert response.status_code == 500
    assert response.json() == {"detail": posture_api.PDF_FAILED}


async def test_saved_report_returns_a_pdf(client: AsyncClient, db_session: AsyncSession):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    report = _report()
    await _save(db_session, headers, report)
    response = await client.post(URL, headers=headers, json={"reportId": report["reportId"]})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


async def test_client_sent_report_is_never_rendered(client: AsyncClient, db_session: AsyncSession):
    """A body that carries a whole (different) report still gets the stored copy."""
    import io

    from pypdf import PdfReader

    headers = await make_user(db_session, role=UserRole.ADMIN)
    stored = _report(name="Stored Person")
    await _save(db_session, headers, stored)
    forged = {**_report(name="Forged Person"), "reportId": stored["reportId"]}
    response = await client.post(URL, headers=headers, json=forged)
    assert response.status_code == 200
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages)
    assert "Stored Person" in text and "Forged Person" not in text
    # An id that was never saved cannot be rendered from the posted data.
    unsaved = _report(name="Forged Person", report_id="PT-20261124-NOPE" + uuid.uuid4().hex[:4].upper())
    assert (await client.post(URL, headers=headers, json=unsaved)).status_code == 404


async def test_another_clinics_report_is_404(client: AsyncClient, db_session: AsyncSession):
    owner = await make_user(db_session, role=UserRole.ADMIN)
    other = await make_user(db_session, role=UserRole.ADMIN)
    report = _report()
    await _save(db_session, owner, report)
    response = await client.post(URL, headers=other, json={"reportId": report["reportId"]})
    assert response.status_code == 404
    assert (await client.get(f"{URL.rsplit('/report/pdf', 1)[0]}/reports/{report['reportId']}/pdf", headers=other)).status_code == 404
