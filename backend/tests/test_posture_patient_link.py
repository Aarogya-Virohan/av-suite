"""POS-2 / BE-2: a posture report belongs to a CRM patient of the clinic.

POST /posture/report takes patient_id, reads name / age / sex and the case ID
from the CRM record, saves the report in posture_sessions, and the saved report
can be listed, opened and downloaded again. Usage events carry no patient data.
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import posture
from app.core.security import decode_token
from app.enums.shared import Gender
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.posture_session import PostureSession
from app.models.usage_event import UsageEvent
from app.services import posture_report_store as store
from app.services.posture.review import make_detection_token, review_indices
from app.services.posture.schemas import Landmark
from tests.test_posture_auth import make_user

pytestmark = pytest.mark.asyncio

W, H = 600, 1000
BASE = "/api/v1/posture"


# --- synthetic photographs and detection (same points as test_assessment_date_ist) ---

def _standing() -> dict[int, tuple[float, float]]:
    p = {0: (0.5, 0.11)}
    for left, right, dx, y in [(1, 4, .02, .10), (2, 5, .03, .10), (3, 6, .04, .10), (7, 8, .06, .11),
                               (9, 10, .02, .13), (11, 12, .17, .21), (13, 14, .2, .36), (15, 16, .21, .49),
                               (17, 18, .21, .51), (19, 20, .21, .51), (21, 22, .21, .51), (23, 24, .1, .5),
                               (25, 26, .1, .7), (27, 28, .1, .89), (29, 30, .1, .9), (31, 32, .11, .92)]:
        p[left], p[right] = (0.5 + dx, y), (0.5 - dx, y)
    return p


def _landmarks(points: dict[int, tuple[float, float]]) -> list[Landmark]:
    return [Landmark(i, *points.get(i, (0.5, 0.5)), 0.0, 0.95) for i in range(33)]


def _side_points() -> dict[int, tuple[float, float]]:
    side = _standing()
    for i in (2, 5, 8, 12, 14, 16, 24, 26, 28, 30, 32):
        side[i] = side[i - 1] if i % 2 == 0 else side[i]
    return side


def _jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (W, H), (220, 220, 220)).save(out, format="JPEG")
    return out.getvalue()


def _report_request() -> dict:
    """detection_token, review and the three display images for POST /report."""
    views = {}
    review: dict = {"confirmed": True}
    for name, pts in (("side", _side_points()), ("front", _standing()), ("back", _standing())):
        lms = _landmarks(pts)
        lateral = posture.get_lateral_side(lms) if name == "side" else None
        views[name] = {"landmarks": lms, "width_px": W, "height_px": H, "lateral_side": lateral, "iris": None}
        review[name] = {
            "points": [
                {"index": i, "x": lms[i].x, "y": lms[i].y}
                for i in review_indices(name, lateral)
            ]
        }
    return {
        "data": {
            "detection_token": make_detection_token(views),
            "review": json.dumps(review),
            "patient_height_cm": "172",
            "clinician_name": "Dr Test",
            "front_source": "camera",
            "side_source": "camera",
            "back_source": "camera",
        },
        "files": {
            "front_display": ("front.jpg", _jpeg(), "image/jpeg"),
            "side_display": ("side.jpg", _jpeg(), "image/jpeg"),
            "back_display": ("back.jpg", _jpeg(), "image/jpeg"),
        },
    }


async def _post_report(client: AsyncClient, headers: dict, patient_id, **extra):
    req = _report_request()
    data = {**req["data"], **extra}
    if patient_id is not None:
        data["patient_id"] = str(patient_id)
    return await client.post(f"{BASE}/report", headers=headers, data=data, files=req["files"])


# --- clinic and patient helpers ---

async def _clinic_for(db: AsyncSession, headers: dict) -> Clinic:
    claims = decode_token(headers["Authorization"].split()[1])
    return await db.get(Clinic, uuid.UUID(str(claims["clinic_id"])))


async def _patient(db: AsyncSession, clinic: Clinic, *, number: int, first="Asha", last="Rao",
                   age: int | None = 34, dob: date | None = None, gender: Gender | None = Gender.FEMALE,
                   deleted: bool = False) -> Patient:
    patient = Patient(
        clinic_id=clinic.id, display_number=number, first_name=first, last_name=last,
        age=age, date_of_birth=dob, gender=gender, phone="9000000001",
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    db.add(patient)
    await db.commit()
    return patient


@pytest.fixture
async def ctx(db_session: AsyncSession):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    clinic = await _clinic_for(db_session, headers)
    clinic.name = "Spine Care Clinic"
    # The Patient ID uses clinics.code (a fresh one per run: codes are unique).
    clinic.code = f"S{uuid.uuid4().hex[:4].upper()}"
    await db_session.commit()
    patient = await _patient(db_session, clinic, number=7)
    return headers, clinic, patient


# --- 404 for another clinic's patient (AUD-05) ---

async def test_foreign_patient_is_404_everywhere(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, _, _ = ctx
    other_headers = await make_user(db_session, role=UserRole.ADMIN)
    other_clinic = await _clinic_for(db_session, other_headers)
    foreign = await _patient(db_session, other_clinic, number=1, first="Foreign", last="Person")

    response = await _post_report(client, headers, foreign.id)
    assert response.status_code == 404
    assert response.json()["detail"] == "Patient not found or not in caller's clinic"
    assert (await client.get(f"{BASE}/patients/{foreign.id}", headers=headers)).status_code == 404
    assert (await client.get(f"{BASE}/patients/{foreign.id}/reports", headers=headers)).status_code == 404
    # nothing saved for the foreign patient
    rows = (await db_session.execute(select(PostureSession).where(PostureSession.patient_id == foreign.id))).all()
    assert rows == []


async def test_unknown_and_deleted_patient_are_404(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, _ = ctx
    gone = await _patient(db_session, clinic, number=8, deleted=True)
    assert (await _post_report(client, headers, uuid.uuid4())).status_code == 404
    assert (await _post_report(client, headers, gone.id)).status_code == 404


async def test_patient_id_is_required(client: AsyncClient, ctx):
    headers, _, _ = ctx
    response = await _post_report(client, headers, None, patient_name="Free Text", age="30")
    assert response.status_code == 422


# --- the report comes from the CRM record ---

async def test_report_uses_crm_patient_and_is_saved(client: AsyncClient, db_session: AsyncSession, ctx, tmp_path, monkeypatch):
    headers, clinic, patient = ctx
    monkeypatch.chdir(tmp_path)

    # Free-text identity fields from an old client are ignored.
    response = await _post_report(client, headers, patient.id, patient_name="Someone Else", age="61", gender="Male", case_ref="ZZ-1")
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["patient"]["name"] == "Asha Rao"
    assert report["patient"]["age"] == 34
    assert report["patient"]["gender"] == "Female"
    assert report["patient"]["caseRef"] == f"{clinic.code}-000007"
    assert report["patient"]["patientId"] == str(patient.id)
    assert report["patient"]["heightCm"] == 172.0
    assert report["reportId"].startswith("PT-")

    row = (await db_session.execute(select(PostureSession).where(PostureSession.report_id == report["reportId"]))).scalar_one()
    assert row.patient_id == patient.id and row.clinic_id == clinic.id
    assert row.analysis_version == report["analysisVersion"]
    saved = row.report_json
    assert saved["patient"]["name"] == "Asha Rao"
    assert saved["views"]["front"]["measurements"], "measurements are kept"
    assert all("photoUrl" not in v for v in saved["views"].values())
    assert "branding" not in saved
    assert report["views"]["front"]["photoUrl"], "the answer to the clinician still carries the photographs"
    # no file written to the container disk any more
    assert not (tmp_path / "data").exists()


async def test_age_comes_from_date_of_birth_when_present(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, _ = ctx
    today = datetime.now(posture.IST).date()
    dob = date(today.year - 40, today.month, today.day) - timedelta(days=1)  # 40 today
    patient = await _patient(db_session, clinic, number=9, age=20, dob=dob, gender=None)
    report = (await _post_report(client, headers, patient.id)).json()
    assert report["patient"]["age"] == 40
    assert report["patient"]["gender"] == ""


async def test_patient_without_age_is_422_with_a_clear_message(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, _ = ctx
    patient = await _patient(db_session, clinic, number=10, age=None)
    response = await _post_report(client, headers, patient.id)
    assert response.status_code == 422
    assert "CRM" in response.json()["detail"]
    rows = (await db_session.execute(select(PostureSession).where(PostureSession.patient_id == patient.id))).all()
    assert rows == []


# --- saved report: list, open again, download again ---

async def test_saved_report_can_be_listed_reopened_and_downloaded(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, patient = ctx
    report = (await _post_report(client, headers, patient.id)).json()
    rid = report["reportId"]

    listing = (await client.get(f"{BASE}/patients/{patient.id}/reports", headers=headers)).json()["reports"]
    assert [r["reportId"] for r in listing] == [rid]

    reopened = await client.get(f"{BASE}/reports/{rid}", headers=headers)
    assert reopened.status_code == 200
    again = reopened.json()
    assert again["patient"] == report["patient"]
    assert again["views"]["side"]["measurements"] == report["views"]["side"]["measurements"]
    assert again["branding"]["clinicName"] == "Spine Care Clinic"

    pdf = await client.get(f"{BASE}/reports/{rid}/pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    # D-043: the printed number is the server-given POS number, not the PT id.
    assert report["reportNumber"] == f"{clinic.code}-POS-000001"
    assert listing[0]["reportNumber"] == report["reportNumber"]
    assert "Asha Rao" in text and f"{clinic.code}-000007" in text and report["reportNumber"] in text


async def test_saved_report_of_another_clinic_is_404(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, _, patient = ctx
    rid = (await _post_report(client, headers, patient.id)).json()["reportId"]
    other = await make_user(db_session, role=UserRole.ADMIN)
    assert (await client.get(f"{BASE}/reports/{rid}", headers=other)).status_code == 404
    assert (await client.get(f"{BASE}/reports/{rid}/pdf", headers=other)).status_code == 404
    assert (await client.get(f"{BASE}/reports/PT-00000000-NOPE", headers=headers)).status_code == 404


async def test_old_session_rows_without_a_report_are_not_listed(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, patient = ctx
    db_session.add(PostureSession(clinic_id=clinic.id, patient_id=patient.id))
    await db_session.commit()
    assert (await client.get(f"{BASE}/patients/{patient.id}/reports", headers=headers)).json()["reports"] == []


# --- picker ---

async def test_picker_finds_by_name_and_crm_id_and_shows_no_phone(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, patient = ctx
    await _patient(db_session, clinic, number=21, first="Ravi", last="Kumar", gender=Gender.MALE)
    other = await make_user(db_session, role=UserRole.ADMIN)
    await _patient(db_session, await _clinic_for(db_session, other), number=7, first="Asha", last="Foreign")

    async def find(term):
        r = await client.get(f"{BASE}/patients", headers=headers, params={"search": term})
        assert r.status_code == 200
        return r.json()["patients"]

    assert [p["name"] for p in await find("asha")] == ["Asha Rao"]
    assert [p["name"] for p in await find(f"{clinic.code}-000007")] == ["Asha Rao"]
    assert [p["name"] for p in await find("#21")] == ["Ravi Kumar"]
    assert {p["name"] for p in await find("")} >= {"Asha Rao", "Ravi Kumar"}
    assert "Foreign" not in json.dumps(await find(""))
    found = (await find("asha"))[0]
    assert found["caseId"] == f"{clinic.code}-000007" and found["age"] == 34 and found["gender"] == "Female"
    assert "phone" not in found and "9000000001" not in json.dumps(found)
    one = (await client.get(f"{BASE}/patients/{patient.id}", headers=headers)).json()
    assert one["id"] == str(patient.id) and one["caseId"] == f"{clinic.code}-000007"


async def test_picker_needs_posture_access(client: AsyncClient, db_session: AsyncSession):
    headers = await make_user(db_session, role=UserRole.THERAPIST)  # no posture.create grant
    assert (await client.get(f"{BASE}/patients", headers=headers)).status_code == 403
    assert (await client.get(f"{BASE}/patients")).status_code == 401


# --- usage events: product and event only ---

async def _events(db: AsyncSession, clinic: Clinic):
    return (await db.execute(select(UsageEvent).where(UsageEvent.clinic_id == clinic.id).order_by(UsageEvent.created_at))).scalars().all()


async def test_usage_events_for_report_and_pdf_carry_no_patient_data(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, patient = ctx
    report = (await _post_report(client, headers, patient.id)).json()
    assert (await client.post(f"{BASE}/report/pdf", headers=headers, json={"reportId": report["reportId"]})).status_code == 200
    assert (await client.get(f"{BASE}/reports/{report['reportId']}/pdf", headers=headers)).status_code == 200

    events = await _events(db_session, clinic)
    assert [(e.product_key, e.event_type) for e in events] == [
        ("posture-tool", "posture_report"),
        ("posture-tool", "posture_pdf"),
        ("posture-tool", "posture_pdf"),
    ]
    columns = {c.name for c in UsageEvent.__table__.columns}
    assert columns == {"id", "organization_id", "clinic_id", "user_id", "product_key", "event_type", "created_at"}
    blob = " ".join(str(getattr(e, c)) for e in events for c in columns)
    for secret in ("Asha", "Rao", str(patient.id), f"{clinic.code}-000007", report["reportId"]):
        assert secret not in blob


async def test_failed_requests_record_no_usage(client: AsyncClient, db_session: AsyncSession, ctx):
    headers, clinic, patient = ctx
    other = await make_user(db_session, role=UserRole.ADMIN)
    foreign = await _patient(db_session, await _clinic_for(db_session, other), number=3)
    assert (await _post_report(client, headers, foreign.id)).status_code == 404
    assert (await client.post(f"{BASE}/report/pdf", headers=headers, json={"patient": "x"})).status_code == 422
    assert await _events(db_session, clinic) == []


# --- Patient ID = the CRM's: clinics.code, then the number padded to 6 digits ---

@pytest.mark.parametrize(
    "code, name, number, expected",
    [
        ("ASC2", "AV Suite Clinic 1", 4, "ASC2-000004"),   # the stored code wins over the name rule
        ("asc2", "AV Suite Clinic 1", 4, "ASC2-000004"),
        (" SCC ", "Anything", 7, "SCC-000007"),
        ("", "Spine Care Clinic", 7, "SCC-000007"),        # empty code: name rule
        (None, "SpineAct", 123, "SPI-000123"),
        ("", "Aarogya Virohan Physio Centre", 5, "AVP-000005"),
        (None, "", 1, "PT-000001"),
        ("", "123 456", 1, "PT-000001"),
        ("", "Dr. Rao's Clinic", 42, "DRS-000042"),
    ],
)
async def test_case_id_matches_crm_format(code, name, number, expected):
    assert store.format_case_id(number, code, name) == expected


async def test_case_id_empty_without_a_number():
    assert store.format_case_id(None, "SC", "Spine Care") == ""


async def test_report_pdf_and_picker_use_the_clinic_code(client: AsyncClient, db_session: AsyncSession):
    """Clinic code ASC2 on a clinic named "AV Suite Clinic 1": ASC2-000004 on the
    picker, the saved report and the PDF (the WhatsApp text is built from the
    report's caseRef, checked in the browser run)."""
    headers = await make_user(db_session, role=UserRole.ADMIN)
    clinic = await _clinic_for(db_session, headers)
    clinic.name = "AV Suite Clinic 1"
    clinic.code = f"A{uuid.uuid4().hex[:4].upper()}"  # unique per run; same shape as ASC2
    await db_session.commit()
    patient = await _patient(db_session, clinic, number=4)

    picked = (await client.get(f"{BASE}/patients/{patient.id}", headers=headers)).json()
    assert picked["caseId"] == f"{clinic.code}-000004"

    report = (await _post_report(client, headers, patient.id)).json()
    assert report["patient"]["caseRef"] == f"{clinic.code}-000004"
    assert "AVS" not in report["patient"]["caseRef"]

    pdf = await client.get(f"{BASE}/reports/{report['reportId']}/pdf", headers=headers)
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert f"{clinic.code}-000004" in text


async def test_clinic_with_code_asc2_gives_asc2_000004(client: AsyncClient, db_session: AsyncSession):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    clinic = await _clinic_for(db_session, headers)
    other = (await db_session.execute(select(Clinic).where(Clinic.code == "ASC2"))).scalars().first()
    if other is not None:  # keep the literal code from the request when it is free
        pytest.skip("ASC2 already taken in this database")
    clinic.name = "AV Suite Clinic 1"
    clinic.code = "ASC2"
    await db_session.commit()
    patient = await _patient(db_session, clinic, number=4)
    report = (await _post_report(client, headers, patient.id)).json()
    assert report["patient"]["caseRef"] == "ASC2-000004"
    pdf = await client.get(f"{BASE}/reports/{report['reportId']}/pdf", headers=headers)
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "ASC2-000004" in text
    clinic.code = f"Z{uuid.uuid4().hex[:4].upper()}"  # free the literal code for the next run
    await db_session.commit()
