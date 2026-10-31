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


def test_case_ref_is_optional_on_the_report_route():
    # Required here meant every report with a blank case reference failed
    # at the last step with "case_ref: Field required".
    default = inspect.signature(posture.report_from_review).parameters["case_ref"].default
    assert getattr(default, "default", None) == ""
