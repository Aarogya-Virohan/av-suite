"""
Founders' answers of 11 October 2026 on the knee row and ear level.
"""

import pytest

from app.services.posture.classifier import classify
from app.services.posture.report_builder import measurement


@pytest.mark.parametrize("param_id", ["PT-A05", "PT-A06"])
@pytest.mark.parametrize(
    "value, expected",
    [
        (0.0, "none"),
        (5.0, "none"),
        (5.1, "mild"),
        (9.0, "mild"),
        (9.1, "moderate"),
        (13.0, "moderate"),
        (13.1, "severe"),
    ],
)
def test_knee_bands_are_the_founders_table_in_both_directions(param_id, value, expected):
    assert classify(param_id, value) == expected


@pytest.mark.parametrize("param_id", ["PT-A05", "PT-A06"])
def test_knee_bands_have_no_female_allowance(param_id):
    # PT-A05 used to stay normal up to 7 degrees for women.
    assert classify(param_id, 6.0, gender="Female") == "mild"
    assert classify(param_id, 6.0, gender="Male") == "mild"


def test_knee_direction_prints_in_plain_words():
    valgus = measurement("PT-A05", "Left Knee Alignment (Hip-Knee-Ankle)", 6.0, "°", "mild", side="valgus")
    varus = measurement("PT-A06", "Left Knee Alignment (Hip-Knee-Ankle)", 6.0, "°", "mild", side="varus")
    assert valgus["sideLabel"] == "Knock-knee"
    assert varus["sideLabel"] == "Bow-leg"


def test_neutral_knee_has_no_direction():
    m = measurement("PT-A06", "Left Knee Alignment (Hip-Knee-Ankle)", 0.3, "°", "none", side=None)
    assert m["sideLabel"] is None
