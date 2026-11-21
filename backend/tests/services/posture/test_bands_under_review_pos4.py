"""
POS-4 (21 Nov 2026): head position (C3) and shoulder level asymmetry (C4)
are measured but not graded until the founders answer F-2.
"""

from app.services.posture import reference_ranges as rr
from app.services.posture.classifier import BANDS_UNDER_REVIEW, SEVERITY_LABELS, classify, grade
from app.services.posture.pdf_service import build_report_html
from app.services.posture.report_builder import build_report_response, measurement, summarise_view
from app.services.posture.signature import build_signature
from app.services.posture.signature_svg import render_signature_svg
from app.services.posture.synthesizer import generate_synthesis

DEG = "°"


def test_under_review_params_do_not_grade_but_others_do():
    assert BANDS_UNDER_REVIEW == {"PT-L01", "PT-A02", "PT-P02"}
    for value in (10.0, 72.0):
        assert grade("PT-L01", value) == "under_review"
    assert grade("PT-P02", 40.0) == "under_review"
    # The bands themselves are unchanged and still classify.
    assert classify("PT-L01", 30.0) == "severe"
    assert grade("PT-A04", 8.0) == classify("PT-A04", 8.0) == "moderate"
    assert SEVERITY_LABELS["under_review"] == "UNDER REVIEW"


def test_row_keeps_the_value_and_says_under_review():
    m = measurement("PT-L01", rr.LABELS["PT-L01"], 33.3, DEG, grade("PT-L01", 33.3), side="anterior")
    assert (m["value"], m["severityLabel"], m["screeningRange"], m["borderline"]) == (
        33.3, "UNDER REVIEW", "Under review", False,
    )


def test_under_review_never_drives_synthesis():
    assert generate_synthesis({"PT-L01": "under_review", "PT-P02": "under_review"}) == {
        "hypertonic": [], "inhibited": [],
    }


def test_summary_does_not_call_an_ungraded_row_normal():
    rows = [
        {"label": "Head Position", "severity": "under_review"},
        {"label": "Trunk Lean", "severity": "none"},
    ]
    assert summarise_view(rows) == (
        "All graded parameters normal. Band under review, not graded: Head Position."
    )
    assert summarise_view(rows[:1]) == "Band under review, not graded: Head Position."


def _views(head_sev="under_review"):
    return {
        "side": {"measurements": [
            measurement("PT-L01", rr.LABELS["PT-L01"], 40.0, DEG, head_sev, side="anterior"),
            measurement("PT-L05", "Forward Trunk Lean", 2.0, DEG, "none"),
        ]},
        "front": {"measurements": [measurement("PT-A04", "Pelvic Obliquity", 2.1, DEG, "none")]},
        "back": {"measurements": [
            measurement("PT-P02", "Shoulder Level Asymmetry", 14.0, "mm", "under_review", side="left"),
        ]},
    }


def test_signature_and_pdf_show_under_review():
    views = _views()
    sig = build_signature(views)
    svg = render_signature_svg(sig)
    assert "under review" in svg
    report = build_report_response(
        patient={"name": "Sample Patient", "assessmentDate": "2026-11-21"},
        side_view=views["side"], front_view=views["front"], back_view=views["back"],
        synthesis={"hypertonic": [], "inhibited": []},
    )
    html = build_report_html(report)
    assert html.count('<td class="range">Under review</td>') == 2
    assert "UNDER REVIEW" in html
    assert "measured but not graded" in html
    # Direction words are hidden on an ungraded row, as on a normal one.
    assert "Head anterior to shoulder" not in html
    assert "Left shoulder higher" not in html
    assert report["analysisVersion"] == "2026-11-21.1"
