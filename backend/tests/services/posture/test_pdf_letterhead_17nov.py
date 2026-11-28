"""
Posture report on the shared letterhead, 17 November 2026.

The clinic on the report is the signed-in clinic (clinics row), passed in by
the route; never a placeholder and never report["branding"] from the client.
The footer carries the document number and page only (D-036): no patient
name. Assessed-on date is IST.
"""

import asyncio
import base64
import io
from types import SimpleNamespace

from app.services.posture.clinic_letterhead import clinic_letterhead, web_branding
from app.services.posture.pdf_service import _patient_box, build_report_html, footer_reference

PATIENT = {
    "name": "Sample Patient",
    "age": 21,
    "gender": "Male",
    "heightCm": 174.0,
    "caseRef": "SP-0142",
    "assessmentDate": "2026-10-12",
    "clinician": "Dr. Karan Singh",
}
REPORT = {"patient": PATIENT, "reportId": "PT-20261012-ABCD1234", "views": {}}


def _png_data_uri() -> str:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (60, 30), (20, 90, 160)).save(out, format="PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def _clinic(**kw):
    base = dict(
        name="SpineAct Physiotherapy Clinic",
        branding_logo_url=None,
        address_line="G-207, Beta 2 Rd",
        city="Greater Noida",
        state="Uttar Pradesh",
        pincode="201310",
        phone="+91 99911 12222",
        email="clinic@example.com",
        registration_number="REG-1",
        gstin="09ABCDE1234F1Z5",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_signed_in_clinic_is_on_the_letterhead():
    clinic = asyncio.run(clinic_letterhead(_clinic()))
    html = build_report_html(REPORT, clinic)
    assert "SpineAct Physiotherapy Clinic" in html
    assert "+91 99911 12222" in html
    assert "Greater Noida" in html
    assert "AV Clinic" not in html


def test_registration_and_gstin_stay_off_the_report():
    html = build_report_html(REPORT, asyncio.run(clinic_letterhead(_clinic())))
    assert "REG-1" not in html
    assert "09ABCDE1234F1Z5" not in html


def test_client_branding_in_the_report_body_is_ignored():
    report = {**REPORT, "branding": {"clinicName": "Spoofed Clinic", "logo": "https://evil.test/x.png"}}
    html = build_report_html(report, asyncio.run(clinic_letterhead(_clinic())))
    assert "Spoofed Clinic" not in html
    assert "evil.test" not in html


def test_without_a_clinic_the_letterhead_is_aarogya_virohan_only():
    html = build_report_html(REPORT, None)
    assert "AV Clinic" not in html
    assert "Aarogya Virohan" in html


def test_clinic_name_is_escaped():
    html = build_report_html(REPORT, asyncio.run(clinic_letterhead(_clinic(name="<script>x</script>"))))
    assert "<script>x" not in html
    assert "&lt;script&gt;x" in html


def test_data_uri_logo_reaches_the_letterhead_as_png():
    clinic = asyncio.run(clinic_letterhead(_clinic(branding_logo_url=_png_data_uri())))
    assert clinic["logoSrc"].startswith("data:image/png;base64,")
    assert clinic["logoSrc"] in build_report_html(REPORT, clinic)


def test_remote_or_unusable_logo_is_dropped_without_failing():
    clinic = asyncio.run(clinic_letterhead(_clinic(branding_logo_url="file:///etc/passwd")))
    assert clinic["logoSrc"] == ""
    assert "SpineAct Physiotherapy Clinic" in build_report_html(REPORT, clinic)


def test_footer_has_document_number_and_page_but_no_patient_name():
    html = build_report_html(REPORT, asyncio.run(clinic_letterhead(_clinic())))
    footer = html[html.index('<div class="cl-footer">'):]
    footer = footer[: footer.index("</tr></table></div></div>")]
    assert "Report No. <b>PT-20261012-ABCD1234</b>" in footer
    assert "Sample Patient" not in footer
    assert 'class="pages"' in footer
    assert footer_reference("") == ""
    # D-043: a report saved since 27 Nov prints its POS number instead.
    numbered = build_report_html({**REPORT, "reportNumber": "SPC-POS-000012"}, asyncio.run(clinic_letterhead(_clinic())))
    assert "Report No. <b>SPC-POS-000012</b>" in numbered


def test_patient_box_names_the_assessor_and_never_a_placeholder_clinic():
    html = _patient_box(REPORT)
    for text in ("Sample Patient", "21 Y / Male", "174&nbsp;cm", "SP-0142", "12 Oct 2026",
                 "Dr. Karan Singh", "PT-20261012-ABCD1234", "Patient ID"):
        assert text in html, text
    assert "Case ref." not in html  # POS-10: the label is "Patient ID" everywhere
    assert "AV Clinic" not in html


def test_patient_box_keeps_its_grid_and_drops_only_the_height_line():
    html = _patient_box({"patient": {**PATIENT, "caseRef": "", "heightCm": None, "clinician": ""}})
    # BR-l: same labels on every report; an empty value is a dash.
    assert '<span class="k">Patient ID</span><span class="v">&ndash;</span>' in html
    assert '<span class="k">Treating therapist</span><span class="v">&ndash;</span>' in html
    # Height is posture-only, on its own line under the box (Q3), and left out when unknown.
    assert "Height" not in html
    assert "Height" in _patient_box(REPORT)


def test_web_branding_is_plain_text_and_drops_empty_fields():
    b = web_branding(_clinic(email=None), "")
    assert b["clinicName"] == "SpineAct Physiotherapy Clinic"
    assert b["addressLine"] == "G-207, Beta 2 Rd, Greater Noida, Uttar Pradesh 201310"
    assert "email" not in b and "logo" not in b
    assert web_branding(None) == {}
