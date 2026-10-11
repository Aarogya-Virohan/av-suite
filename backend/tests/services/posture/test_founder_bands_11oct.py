"""
Founders' second reply of 11 October 2026, answers 1a to 5a. Each band is
pinned at every boundary, both sides where the value is signed.
"""

import pytest

from app.services.posture.classifier import classify

CASES = {
    # Head tilt: 5 / 8 / 12
    "PT-A01": [(5.0, "none"), (5.1, "mild"), (8.0, "mild"), (8.1, "moderate"), (12.0, "moderate"), (12.1, "severe")],
    # Pelvic obliquity: 3 / 6 / 10
    "PT-A04": [(3.0, "none"), (3.1, "mild"), (6.0, "mild"), (6.1, "moderate"), (10.0, "moderate"), (10.1, "severe")],
    # Trunk shift, back view: 10 / 20 / 30 mm
    "PT-P01": [(10.0, "none"), (10.1, "mild"), (20.0, "mild"), (20.1, "moderate"), (30.0, "moderate"), (30.1, "severe")],
    # Trunk lean, signed: 4 / 7 / 10
    "PT-L05": [(4.0, "none"), (-4.0, "none"), (4.1, "mild"), (-4.1, "mild"), (7.0, "mild"), (-7.1, "moderate"),
               (10.0, "moderate"), (-10.1, "severe")],
    # Knee from the side, signed: 5 / 10 / 15
    "PT-L06": [(5.0, "none"), (-5.0, "none"), (5.1, "mild"), (-5.1, "mild"), (10.0, "mild"), (10.1, "moderate"),
               (-15.0, "moderate"), (15.1, "severe"), (-15.1, "severe")],
}


@pytest.mark.parametrize(
    "param_id, value, expected",
    [(p, v, e) for p, rows in CASES.items() for v, e in rows],
)
def test_founder_bands(param_id, value, expected):
    assert classify(param_id, value) == expected


def test_trunk_shift_front_and_back_cannot_drift():
    for v in (5, 10, 15, 20, 25, 30, 35):
        assert classify("PT-A03", v) == classify("PT-P01", v)
