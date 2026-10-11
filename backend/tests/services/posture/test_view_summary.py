from app.services.posture.report_builder import summarise_view


def row(label, severity):
    return {"label": label, "severity": severity}


def test_mild_is_never_called_acceptable():
    s = summarise_view([row("Head Lateral Tilt", "mild"), row("Pelvic Obliquity", "none")])
    assert s == "No moderate or severe deviation. Mild deviation in: Head Lateral Tilt."
    assert "acceptable" not in s


def test_major_and_mild_are_both_listed():
    s = summarise_view([
        row("Trunk Lateral Deviation (Posterior)", "moderate"),
        row("Shoulder Level Asymmetry", "mild"),
    ])
    assert s == (
        "Moderate or severe deviation in: Trunk Lateral Deviation (Posterior). "
        "Mild deviation in: Shoulder Level Asymmetry."
    )


def test_all_normal():
    assert summarise_view([row("A", "none"), row("B", "none")]) == "All measured parameters graded normal."


def test_unmeasured_rows_are_named_not_hidden():
    s = summarise_view([row("Forward Head (CVA)", "none"), row("Knee Sagittal Alignment", "insufficient_data")])
    assert s == "All measured parameters graded normal. Not measured: Knee Sagittal Alignment."


def test_nothing_measured():
    s = summarise_view([row("A", "insufficient_data"), row("B", "not_available")])
    assert s == "No parameter could be measured on this view."
