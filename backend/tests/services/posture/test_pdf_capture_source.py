from app.services.posture.pdf_service import UPLOAD_NOTE, _view_section, build_report_html

BASE = {"accuracy": 0.9, "measurements": [], "interpretation": "x", "photoUrl": ""}


def test_uploaded_photo_is_named_on_the_pdf():
    # Since 11 October 2026 the source is a plain detail on every view, and
    # the explanation is printed once in the notes, not as an amber flag.
    html = _view_section("Front", {**BASE, "captureSource": "upload"})
    assert '<td class="d-label">Photograph</td><td class="d-value">Uploaded photo</td>' in html
    # Landmark visibility removed from the PDF on 13 October 2026.
    assert "Landmark visibility" not in html
    assert "90.0%" not in html


def test_camera_capture_is_named_on_the_pdf():
    html = _view_section("Front", {**BASE, "captureSource": "camera"})
    assert "Guided camera capture" in html


def test_unknown_or_missing_source_prints_nothing_extra():
    for view in ({**BASE, "captureSource": "unknown"}, dict(BASE)):
        html = _view_section("Front", view)
        assert "capture" not in html.lower()
        assert "Photograph" not in html


def test_upload_note_appears_once_only_when_a_view_was_uploaded():
    views = {k: {**BASE, "captureSource": "camera"} for k in ("side", "front", "back")}
    assert UPLOAD_NOTE not in build_report_html({"views": views})
    views["back"] = {**BASE, "captureSource": "upload"}
    assert build_report_html({"views": views}).count(UPLOAD_NOTE) == 1
