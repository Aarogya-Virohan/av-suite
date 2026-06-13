import pytest

from app.services.posture.classifier import classify


def test_unknown_parameter():

    with pytest.raises(ValueError):
        classify("PT-UNKNOWN", 10)
