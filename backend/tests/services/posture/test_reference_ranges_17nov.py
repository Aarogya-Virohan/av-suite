"""
Normal ranges on the posture report, 17 November 2026: read from THRESHOLDS
(single source of truth), one format, shown on every row in one fixed
column grid, basis and sources in their own section above the disclaimer,
chart names equal to the table names, PT-L01 not labelled CVA. No grade
moves.
"""

import inspect
import re

from app.api.v1 import posture
from app.services.posture import reference_ranges as rr
from app.services.posture.classifier import THRESHOLDS, classify
from app.services.posture.pdf_service import build_report_html
from app.services.posture.report_builder import build_report_response, measurement

REPORT_PARAMS = ("PT-L01", "PT-L05", "PT-L06", "PT-A01", "PT-A04", "PT-A05", "PT-A06", "PT-P01", "PT-P02")
DEG = "°"


def _visible(html: str) -> str:
    html = re.sub(r"data:[^\"')]+", "", html)  # base64 images can contain any letters
    return re.sub(r'<span class="sym">(.)</span>', r"\1", html)


def test_every_report_row_has_a_range_and_a_source():
    covered = {p for e in rr.SOURCES for p in e["params"].split(",")}
    for pid in REPORT_PARAMS:
        assert rr.screening_range(pid), pid
        assert pid in covered, pid


def test_one_range_format_read_from_thresholds():
    assert rr.screening_range("PT-L01") == f"≥ 50{DEG}"
    assert rr.screening_range("PT-L05") == f"± 4{DEG}"
    assert rr.screening_range("PT-L06") == f"± 5{DEG}"
    assert rr.screening_range("PT-A01") == f"≤ 5{DEG}"
    assert rr.screening_range("PT-A04") == f"≤ 3{DEG}"
    assert rr.screening_range("PT-A05") == rr.screening_range("PT-A06") == f"≤ 5{DEG}"
    assert rr.screening_range("PT-P01") == "≤ 10 mm"
    assert rr.screening_range("PT-P02") == "≤ 5 mm"


def test_range_follows_a_band_change(monkeypatch):
    monkeypatch.setitem(THRESHOLDS, "PT-A04", {**THRESHOLDS["PT-A04"], "none_max": 4})
    assert rr.screening_range("PT-A04") == f"≤ 4{DEG}"


def test_shown_range_matches_the_grade_at_its_edges():
    assert classify("PT-A04", 3.0) == "none" and classify("PT-A04", 3.01) != "none"
    assert classify("PT-L01", 50.0) == "none" and classify("PT-L01", 49.99) != "none"
    assert classify("PT-L05", -4.0) == "none" and classify("PT-L05", 4.01) != "none"


def test_measurement_payload_carries_the_range():
    m = measurement("PT-P02", "Shoulder Level Asymmetry", 9.2, "mm", "mild")
    assert m["screeningRange"] == "≤ 5 mm"
    assert measurement("PT-X99", "Unknown", 1.0, DEG, "none")["screeningRange"] == ""


def test_pt_l01_is_not_labelled_cva():
    assert "CVA" not in rr.LABELS["PT-L01"]
    src = inspect.getsource(posture)
    assert '"Forward Head (CVA)"' not in src
    assert "calc_cva(" in src  # function name unchanged


def _report(**extra):
    views = {
        "side": {"measurements": [measurement("PT-L01", rr.LABELS["PT-L01"], 72.0, DEG, "none")]},
        "front": {"measurements": [measurement("PT-A04", "Pelvic Obliquity", 2.1, DEG, "none")]},
        "back": {"measurements": [measurement("PT-P02", "Shoulder Level Asymmetry", 9.2, "mm", "mild")]},
    }
    return {"patient": {"name": "Sample Patient"}, "views": views, **extra}


def test_pdf_has_the_normal_range_column_and_the_sources_section():
    html = build_report_html(_report())
    text = _visible(html)
    assert "<th>Normal range</th>" in html
    assert '<td class="range">≤ 5 mm</td>' in _visible(html)
    assert f'<td class="range">≥ 50{DEG}</td>' in _visible(html)
    assert "Normal ranges: basis and sources" in html
    assert "AV screening range" not in text
    assert "Moharrami et al. 2023" in html and f"0 to 5.6{DEG}" in html
    assert "not the C7-based craniovertebral angle" in html
    assert "AV clinical team, Oct 2026" in html
    assert "no source" not in text.lower()
    assert "CVA" not in text


def test_pdf_range_comes_from_the_server_not_the_posted_report():
    report = _report()
    report["views"]["back"]["measurements"][0]["screeningRange"] = "0 to 999 mm"
    html = build_report_html(report)
    assert "0 to 999 mm" not in html
    assert '<td class="range">≤ 5 mm</td>' in _visible(html)


def test_moharrami_only_in_the_sources_section():
    html = build_report_html(_report())
    body, rest = html.split('class="sources-section"', 1)
    assert "5.6" not in body.split("<body>", 1)[1]
    assert "5.6" in rest
    for word in ("Below", "Within", "Above"):
        assert f">{word}<" not in html


def test_sources_section_sits_above_the_disclaimer_one_line_per_measure():
    html = build_report_html(_report())
    start = html.index('<div class="sources-section">')
    closing = html.index('<div class="closing">')
    assert start < closing < html.index(">Disclaimer<")
    section = html[start:closing]
    assert section.count('<p class="src">') == len(rr.SOURCES)
    assert "font-size: 8pt" in html


def test_every_table_uses_the_same_fixed_columns():
    html = build_report_html(_report())
    assert html.count('<col class="c-param" />') == 3
    assert "table-layout: fixed" in html


def test_chart_names_match_the_table_labels():
    from app.services.posture.signature import build_signature
    from app.services.posture.signature_svg import render_signature_svg

    svg = render_signature_svg(build_signature(_report()["views"]))
    assert "Head position" in svg
    assert "Left knee" in rr.chart_label("Left Knee Alignment (Hip-Knee-Ankle)")
    assert "Forward head" not in svg
    assert rr.chart_label("Left Knee Alignment (Hip-Knee-Ankle)") == "Left knee alignment"
    assert rr.chart_label("Trunk Lateral Deviation (Posterior)") == "Trunk lateral deviation"


def test_report_response_carries_the_sources_for_the_web():
    r = build_report_response({}, {"measurements": []}, {"measurements": []}, {"measurements": []}, {})
    names = [s["name"] for s in r["screeningSources"]]
    assert names[0] == rr.LABELS["PT-L01"]
    assert "Pelvic Obliquity" in names
    assert r["screeningNote"] == rr.SCREENING_NOTE
