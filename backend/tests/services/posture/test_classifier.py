import pytest

from app.services.posture.classifier import classify


def test_unknown_parameter():

    with pytest.raises(ValueError):
        classify("PT-UNKNOWN", 10)


def test_pt_l06_knee_hyperextension_thresholds():

    # PT-L06 — lower_worse, more negative = worse.
    assert classify("PT-L06", 5) == "none"
    assert classify("PT-L06", -5) == "none"
    assert classify("PT-L06", -7) == "mild"
    assert classify("PT-L06", -12) == "moderate"
    assert classify("PT-L06", -20) == "severe"


def test_pt_a08_elbow_carrying_angle_gender_thresholds():

    # PT-A08 — higher_worse, all three bands shift for female patients.
    assert classify("PT-A08", 10, gender="male") == "none"
    assert classify("PT-A08", 12, gender="male") == "mild"
    assert classify("PT-A08", 18, gender="male") == "moderate"
    assert classify("PT-A08", 25, gender="male") == "severe"

    assert classify("PT-A08", 12, gender="female") == "none"
    assert classify("PT-A08", 18, gender="female") == "mild"
    assert classify("PT-A08", 23, gender="female") == "moderate"
    assert classify("PT-A08", 30, gender="female") == "severe"
