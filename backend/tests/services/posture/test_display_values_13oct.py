"""
Founders' answers of 13 October 2026, Q4 and Q5: one decimal on the report,
and no minus sign on rows whose label already names the direction.
"""

import pytest

from app.services.posture.classifier import classify
from app.services.posture.pdf_service import (
    _measurement_rows,
    _number,
    _value_with_unit,
)
from app.services.posture.report_builder import display_value, measurement


def test_values_carry_one_decimal():
    degrees = measurement("PT-L01", "Forward Head (CVA)", 71.27, "°", "none")
    millimetres = measurement("PT-P02", "Shoulder Level Asymmetry", 12.19, "mm", "moderate")
    assert degrees["value"] == 71.3
    assert millimetres["value"] == 12.2


@pytest.mark.parametrize(
    "param_id, label, raw, shown",
    [
        ("PT-L05", "Backward Trunk Lean", -3.23, 3.2),
        ("PT-L06", "Knee Hyperextension", -6.04, 6.0),
    ],
)
def test_direction_named_rows_print_the_size_only(param_id, label, raw, shown):
    m = measurement(param_id, label, raw, "°", "none")
    assert m["value"] == shown
    # The label is what carries the direction, and it is passed through untouched.
    assert m["label"] == label


def test_forward_lean_and_flexion_are_unchanged_in_sign():
    assert measurement("PT-L05", "Forward Trunk Lean", 4.46, "°", "mild")["value"] == 4.5
    assert measurement("PT-L06", "Knee Flexion", 7.04, "°", "mild")["value"] == 7.0


def test_other_rows_keep_their_value_and_are_not_made_positive():
    # No other row can be negative today. If one ever is, the sign must stay.
    assert display_value("PT-A01", -2.26) == -2.3
    assert display_value("PT-A01", 2.26) == 2.3


def test_negative_zero_prints_as_zero():
    assert str(display_value("PT-A01", -0.04)) == "0.0"
    assert str(display_value("PT-L05", -0.04)) == "0.0"


def test_missing_values_pass_through():
    assert display_value("PT-L05", None) is None
    assert measurement("PT-L05", "Forward Trunk Lean", None, "°", "insufficient_data")["value"] is None


def test_the_grade_is_decided_on_the_unrounded_signed_value():
    # -4.04 is outside the normal band (4) so it grades mild, even though it
    # prints as 4.0. The borderline flag is what tells the clinician.
    assert classify("PT-L05", -4.04) == "mild"
    m = measurement("PT-L05", "Backward Trunk Lean", -4.04, "°", classify("PT-L05", -4.04))
    assert m["value"] == 4.0
    assert m["severity"] == "mild"
    assert m["borderline"] is True


def test_pdf_pads_to_one_decimal():
    assert _number(71.3) == "71.3"
    assert _number(12.0) == "12.0"
    assert _value_with_unit(12.2, "mm") == "12.2&nbsp;mm"
    assert _value_with_unit(3.2, "°") == "3.2°"


def test_pdf_row_for_a_backward_lean_has_no_minus_sign():
    row = measurement("PT-L05", "Backward Trunk Lean", -3.23, "°", "none")
    html = _measurement_rows([row])
    assert '<td class="value">3.2°</td>' in html
    assert "-3" not in html
