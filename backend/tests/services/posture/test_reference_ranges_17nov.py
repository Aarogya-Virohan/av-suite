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
    # One line per measure that has a row in this report (three here).
    assert section.count('<p class="src">') == 3
    assert "font-size: 8pt" in html


def test_every_table_uses_the_same_fixed_columns():
    html = build_report_html(_report())
    assert html.count('<col class="c-param" />') == 3
    assert "table-layout: fixed" in html


def _full_report():
    rows = {
        "side": [
            ("PT-L01", rr.LABELS["PT-L01"], "none"),
            ("PT-L05", "Backward Trunk Lean", "none"),
            ("PT-L06", "Knee Flexion", "none"),
        ],
        "front": [
            ("PT-A01", "Head Lateral Tilt", "none"),
            ("PT-A04", "Pelvic Obliquity", "none"),
            ("PT-A06", "Left Knee Alignment (Hip-Knee-Ankle)", "none"),
            ("PT-A06", "Right Knee Alignment (Hip-Knee-Ankle)", "none"),
        ],
        "back": [
            ("PT-P01", "Trunk Lateral Deviation (Posterior)", "moderate"),
            ("PT-P02", "Shoulder Level Asymmetry", "mild"),
        ],
    }
    views = {
        v: {"measurements": [measurement(p, label, 1.0, rr.UNITS[p], sev) for p, label, sev in ms]}
        for v, ms in rows.items()
    }
    return {"patient": {"name": "Sample Patient"}, "views": views}


def _svg_text(svg: str) -> str:
    lines = re.findall(r"<text[^>]*>([^<]*)</text>", svg)
    return re.sub(r"- ", "-", " ".join(lines))


def test_one_name_everywhere_chart_sources_and_table():
    """
    Coordinator review of v4 (17 Nov 2026): the radar axis and the sources
    line carry the table row's own label, same text and case.
    """
    from html import unescape

    from app.services.posture.signature import build_signature
    from app.services.posture.signature_svg import render_signature_svg

    report = _full_report()
    labels = [m["label"] for v in report["views"].values() for m in v["measurements"]]
    chart = unescape(_svg_text(render_signature_svg(build_signature(report["views"]))))
    for label in labels:
        assert label in chart, label
    for old in ("Head position", "Knee flexion", "Forward head"):
        assert old not in chart

    names = [name for name, _ in rr.source_lines(report["views"])]
    assert names == [
        rr.LABELS["PT-L01"],
        "Backward Trunk Lean",
        "Knee Flexion",
        "Head Lateral Tilt",
        "Pelvic Obliquity",
        "Left Knee Alignment (Hip-Knee-Ankle), Right Knee Alignment (Hip-Knee-Ankle)",
        "Trunk Lateral Deviation (Posterior)",
        "Shoulder Level Asymmetry",
    ]
    html = build_report_html(report)
    section = html[html.index('<div class="sources-section">'):html.index('<div class="closing">')]
    for name in names:
        assert f"<strong>{name}:</strong>" in section.replace("&#x27;", "'")


def test_sources_name_follows_the_sign_of_the_row():
    report = _full_report()
    report["views"]["side"]["measurements"][1]["label"] = "Forward Trunk Lean"
    report["views"]["side"]["measurements"][2]["label"] = "Knee Hyperextension"
    names = [name for name, _ in rr.source_lines(report["views"])]
    assert "Forward Trunk Lean" in names and "Knee Hyperextension" in names
    assert "Trunk Lean" not in names and "Knee Flexion / Hyperextension" not in names


def test_ring_names_cover_no_point_and_no_outline():
    from app.services.posture.signature import build_signature
    from app.services.posture.signature_svg import _circle_hits_rect, _seg_hits_rect, render_signature_svg

    svg = render_signature_svg(build_signature(_full_report()["views"]))
    pills = [tuple(map(float, m)) for m in re.findall(
        r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg)]
    dots = [tuple(map(float, m)) for m in re.findall(r'<circle cx="([-\d.]+)" cy="([-\d.]+)" r="5.5"', svg)]
    outline = [tuple(map(float, p.split(","))) for p in re.search(r'<polygon points="([^"]+)"', svg).group(1).split()]
    assert len(pills) == 4 and len(dots) == 9
    for x, y, w, h in pills:
        box = (x, y, x + w, y + h)
        assert not any(_circle_hits_rect(a, b, 7, *box) for a, b in dots)
        assert not any(
            _seg_hits_rect(*outline[k], *outline[(k + 1) % len(outline)], *box) for k in range(len(outline))
        )
    # Not on the vertical centre line above the centre any more, where
    # "Normal" used to cover the two top points.
    normal = pills[0]
    assert abs(normal[1] + normal[3] / 2 - 200) < 1


def test_report_response_carries_the_sources_for_the_web():
    report = _full_report()
    r = build_report_response({}, report["views"]["side"], report["views"]["front"], report["views"]["back"], {})
    names = [s["name"] for s in r["screeningSources"]]
    assert names[0] == rr.LABELS["PT-L01"]
    assert "Backward Trunk Lean" in names
    assert r["screeningNote"] == rr.SCREENING_NOTE
