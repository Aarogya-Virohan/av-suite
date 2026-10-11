from app.services.posture.pdf_service import _view_section

BASE = {"accuracy": 0.9, "measurements": [], "interpretation": "x", "photoUrl": ""}


def test_uploaded_photo_is_named_on_the_pdf():
    html = _view_section("Front", {**BASE, "captureSource": "upload"})
    assert "Landmark visibility: 90.0%<br>Uploaded photo, capture protocol not checked" in html


def test_camera_capture_is_named_on_the_pdf():
    html = _view_section("Front", {**BASE, "captureSource": "camera"})
    assert "Guided camera capture" in html


def test_unknown_or_missing_source_prints_nothing_extra():
    for view in ({**BASE, "captureSource": "unknown"}, dict(BASE)):
        html = _view_section("Front", view)
        assert "capture" not in html.lower()
