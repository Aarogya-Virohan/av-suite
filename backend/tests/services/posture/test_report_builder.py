from app.services.posture.report_builder import build_side_view_result


def test_capture_source_is_carried_into_the_view() -> None:
    """
    A photograph taken through the in-app capture screen and one chosen
    from the gallery are indistinguishable once they reach the server, but
    only the first went through the tripod and framing protocol and was
    encoded losslessly. The report has to record which it was.
    """

    result = build_side_view_result(
        measurements=[],
        photo_url="",
        accuracy=0.9,
        capture_source="camera",
    )

    assert result["captureSource"] == "camera"


def test_capture_source_defaults_to_unknown_not_camera() -> None:
    """
    The default must not claim the stronger of the two. A client that does
    not send the field has not told us the photograph was guided, and
    assuming it was would overstate every measurement's provenance.
    """

    result = build_side_view_result(measurements=[], photo_url="")

    assert result["captureSource"] == "unknown"


def test_severity_labels_describe_the_deviation_not_the_patient():

    # Founders, 10 October 2026.
    from app.services.posture.classifier import SEVERITY_LABELS

    assert SEVERITY_LABELS["none"] == "NORMAL"
    for grade in ("mild", "moderate", "severe"):
        assert SEVERITY_LABELS[grade] == f"{grade.upper()} DEVIATION"


def test_report_carries_no_global_score():

    # Founders, 10 October 2026: the single Global Stability Index is
    # removed from the report. If it is ever reinstated, that should be a
    # deliberate decision, and this test is where it will surface.
    from app.services.posture.report_builder import build_report_response

    report = build_report_response(
        patient={}, side_view={}, front_view={}, back_view={}, synthesis={}
    )
    assert "globalIndex" not in report
