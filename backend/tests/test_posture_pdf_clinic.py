"""
/api/v1/posture/report/pdf prints the signed-in clinic (17 November 2026),
whatever report["branding"] the client posts, and no patient name in the
footer.
"""

from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.core.security import decode_token
from app.services import posture_report_store as store
from tests.test_posture_auth import make_user
from tests.test_posture_patient_link import _patient

pytestmark = pytest.mark.asyncio


async def test_pdf_uses_the_signed_in_clinic_not_the_posted_branding(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    token = headers["Authorization"].split()[1]
    clinic_id = decode_token(token)["clinic_id"]
    clinic = await db_session.get(Clinic, uuid.UUID(str(clinic_id)))
    clinic.name = f"SpineAct Test {uuid.uuid4().hex[:6]}"
    clinic.phone = "+91 99911 12222"
    clinic.city = "Greater Noida"
    await db_session.commit()

    report = {
        "patient": {"name": "Zed Patientname", "assessmentDate": "2026-11-17", "clinician": "Dr. X"},
        "reportId": "PT-20261117-ABCD1234",
        "views": {},
    }
    patient = await _patient(db_session, clinic, number=3)
    await store.save_report(db_session, clinic_id=clinic.id, patient_id=patient.id, user_id=None, report=report)
    await db_session.commit()
    # POS-10: the PDF reads the saved copy; a posted body adds nothing, so a
    # spoofed branding sent along with the id is ignored as well.
    posted = {"reportId": report["reportId"], "branding": {"clinicName": "Spoofed Clinic", "logo": "https://evil.test/x.png"}}
    response = await client.post("/api/v1/posture/report/pdf", headers=headers, json=posted)
    assert response.status_code == 200, response.text
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages)
    assert clinic.name in text
    assert "+91 99911 12222" in text
    assert "Spoofed Clinic" not in text
    assert "AV Clinic" not in text
    assert f"Report No. {clinic.code}-POS-000001" in text
    # Patient name only in the patient box, once per document, not per page footer.
    assert text.count("Zed Patientname") == 1
