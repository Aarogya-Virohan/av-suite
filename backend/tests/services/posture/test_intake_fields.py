"""Optional intake fields, 27 October 2026."""

import inspect

from app.api.v1 import posture
from app.api.v1.posture import blank_if_placeholder


def test_placeholders_become_empty():
    for v in ("NA", "Na", " n/a ", "N.A.", "nil", "None", "-", "--", "null", "Not applicable", "", None):
        assert blank_if_placeholder(v) == "", v


def test_real_values_are_kept():
    assert blank_if_placeholder("  Dr. Shivank ") == "Dr. Shivank"
    assert blank_if_placeholder("AV-1042") == "AV-1042"
    assert blank_if_placeholder("Nandini") == "Nandini"


def test_report_route_takes_no_free_text_identity():
    # POS-2 (23 Nov 2026): name, age, sex and case reference come from the CRM
    # patient (patient_id), so the old optional-field problems (blank case
    # reference, "Not given" gender) cannot happen at the last step any more.
    params = inspect.signature(posture.report_from_review).parameters
    for gone in ("patient_name", "age", "gender", "case_ref"):
        assert gone not in params, gone
    assert "patient_id" in params
