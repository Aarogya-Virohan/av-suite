from app.services.posture.signature import REGION_OF, REGIONS, build_signature


def m(param_id, label, severity, value=1.0, unit="°"):
    return {"paramId": param_id, "label": label, "severity": severity, "value": value, "unit": unit}


def regions(sig):
    return {r["id"]: r for r in sig["regions"]}


def test_every_parameter_on_the_report_has_a_region():
    # The rows the report produces since 11 October 2026. A new row must be
    # given a region here or it silently drops out of the signature.
    live = {"PT-L01", "PT-L05", "PT-L06", "PT-A01", "PT-A04", "PT-A05", "PT-A06", "PT-P01", "PT-P02"}
    assert live <= set(REGION_OF)
    assert set(REGION_OF.values()) <= {rid for rid, _ in REGIONS}


def test_region_shows_its_worst_grade_and_adds_no_number():
    sig = build_signature({
        "side": {"measurements": [m("PT-L01", "Forward Head (CVA)", "none"), m("PT-L05", "Trunk Lean", "mild")]},
        "front": {"measurements": [m("PT-A01", "Head Lateral Tilt", "moderate")]},
        "back": {"measurements": [m("PT-P01", "Trunk Shift", "severe", 31, "mm")]},
    })
    r = regions(sig)
    assert r["head_neck"]["worst"] == "moderate"
    assert r["trunk"]["worst"] == "severe"
    assert [p["tier"] for p in r["head_neck"]["parameters"]] == [0, 2]
    assert set(r["trunk"].keys()) == {"id", "label", "worst", "worstLabel", "measured", "parameters"}
    assert r["trunk"]["worstLabel"] == "SEVERE DEVIATION"


def test_unmeasured_never_reads_as_normal():
    sig = build_signature({"side": {"measurements": [m("PT-L06", "Knee Sagittal Alignment", "insufficient_data", None)]}})
    knees = regions(sig)["knees"]
    assert knees["parameters"][0]["tier"] is None
    assert knees["worst"] is None and knees["measured"] == 0


def test_thoracic_is_present_and_empty():
    r = regions(build_signature({}))
    assert r["thoracic"]["parameters"] == [] and r["thoracic"]["worst"] is None


def test_regions_run_head_to_toe():
    assert [r["id"] for r in build_signature({})["regions"]] == [
        "head_neck", "shoulders", "thoracic", "trunk", "pelvis", "knees",
    ]


def test_svg_draws_no_point_for_an_unmeasured_parameter():
    from app.services.posture.signature_svg import render_signature_svg

    sig = build_signature({
        "side": {"measurements": [m("PT-L06", "Knee Sagittal Alignment", "insufficient_data", None)]},
        "front": {"measurements": [m("PT-A01", "Head Lateral Tilt", "mild"), m("PT-A04", "Pelvic Obliquity", "none")]},
    })
    svg = render_signature_svg(sig)
    # Four rings, plus one point per measured parameter, nothing for the knee.
    assert svg.count("<circle") == 4 + 2
    assert "not measured" in svg


def test_pdf_section_is_omitted_for_reports_without_a_signature():
    from app.services.posture.pdf_service import _biomech_signature_section

    assert _biomech_signature_section(None) == ""
    html = _biomech_signature_section(build_signature({}))
    assert "Biomechanical Signature" in html and "No parameter" in html
