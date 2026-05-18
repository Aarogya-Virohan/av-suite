from app.services.posture.classifier import classify


def test_cva_normal():
    assert classify("PT-L01", 55) == "none"


def test_cva_mild():
    assert classify("PT-L01", 46) == "mild"


def test_cva_severe():
    assert classify("PT-L01", 35) == "severe"
