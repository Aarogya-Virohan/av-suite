"""
Report letterhead and patient box, 13 October 2026: a clinic letterhead from
report["branding"] when it is there, Aarogya Virohan's otherwise, and every
intake field in the patient box.
"""

from app.services.posture.pdf_service import (
    AV_FALLBACK,
    _letterhead,
    _patient_box,
    _safe_logo,
    build_report_html,
)

PATIENT = {
    "name": "Sample Patient",
    "age": 21,
    "gender": "Male",
    "heightCm": 174.0,
    "caseRef": "SP-0142",
    "assessmentDate": "2026-10-12",
    "clinician": "Dr. Karan Singh",
}

CLINIC = {
    "clinicName": "Sunrise Physio",
    "addressLine": "Sector 62, Noida",
    "phone": "+91 98100 00000",
    "email": "care@example.com",
    "doctorName": "Dr. Anjali Mehta (PT)",
    "doctorDegree": "BPT, MPT",
    "doctorRegNo": "DPC/1",
}


def test_without_branding_the_letterhead_is_aarogya_virohans():
    html = _letterhead({"patient": PATIENT})
    assert AV_FALLBACK["phone"] in html
    assert "Assessing physiotherapist" in html
    assert "Dr. Karan Singh" in html


def test_fallback_without_a_clinician_prints_no_empty_label():
    html = _letterhead({"patient": {**PATIENT, "clinician": ""}})
    assert "Assessing physiotherapist" not in html


def test_clinic_branding_replaces_the_fallback():
    html = _letterhead({"patient": PATIENT, "branding": CLINIC})
    assert "Sunrise Physio" in html
    assert "Dr. Anjali Mehta (PT)" in html
    assert "Reg. No. DPC/1" in html
    assert AV_FALLBACK["phone"] not in html
    # The assessing physiotherapist moves to the patient box.
    assert "Dr. Karan Singh" not in html


def test_clinic_text_is_escaped():
    html = _letterhead({"patient": PATIENT, "branding": {"clinicName": "<script>x</script>"}})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_only_inline_png_or_jpeg_logos_are_accepted():
    assert _safe_logo("data:image/png;base64,iVBORw0KGgo=") != ""
    assert _safe_logo("data:image/jpeg;base64,/9j/4AAQ") != ""
    for bad in (
        "https://example.com/logo.png",
        "file:///etc/passwd",
        "data:image/svg+xml;base64,PHN2Zz4=",
        'data:image/png;base64,AAAA" onerror="x',
        None,
        42,
    ):
        assert _safe_logo(bad) == ""


def test_a_refused_logo_falls_back_to_initials():
    html = _letterhead({"patient": PATIENT, "branding": {**CLINIC, "logo": "https://logo-host.test/x.png"}})
    assert "logo-host.test" not in html
    assert "<img" not in html
    assert '<span class="initials">SP</span>' in html


def test_patient_box_carries_every_intake_field():
    views = {k: {"captureSource": "camera"} for k in ("side", "front", "back")}
    html = _patient_box({"patient": PATIENT, "views": views, "reportId": "PT-20261012-ABCD1234", "branding": CLINIC})
    for text in ("Sample Patient", "21 Y / Male", "174&nbsp;cm", "SP-0142", "12 Oct 2026",
                 "Dr. Karan Singh", "PT-20261012-ABCD1234"):
        assert text in html, text


def test_patient_box_leaves_out_empty_fields():
    html = _patient_box({"patient": {**PATIENT, "caseRef": "", "heightCm": None}, "views": {}, "branding": CLINIC})
    assert "Case ref." not in html
    assert "Height" not in html


def test_fallback_box_names_the_clinic_not_the_assessor():
    html = _patient_box({"patient": PATIENT, "views": {}})
    assert "AV Clinic" in html
    assert "Assessed by" not in html


def test_no_photographs_row_and_no_subtitle():
    views = {k: {"captureSource": "camera"} for k in ("side", "front", "back")}
    html = _patient_box({"patient": PATIENT, "views": views})
    assert "Photographs" not in html
    assert "Static standing posture" not in html
    assert "POSTURE ASSESSMENT REPORT" in html


def test_footer_has_no_tagline_and_carries_the_mark():
    html = build_report_html({"patient": PATIENT, "views": {}})
    assert "PRESCRIPTION TOOL" not in html
    assert 'class="mark"' in html


def test_footer_names_the_patient_and_report_on_every_page():
    html = build_report_html({"patient": PATIENT, "reportId": "PT-20261012-ABCD1234", "views": {}})
    assert '<span class="who">Sample Patient &nbsp;&middot;&nbsp; PT-20261012-ABCD1234</span>' in html
