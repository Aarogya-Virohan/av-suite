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
