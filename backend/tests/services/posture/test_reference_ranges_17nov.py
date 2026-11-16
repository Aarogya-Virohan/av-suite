"""
AV screening ranges on the report, 17 November 2026: read from THRESHOLDS
(single source of truth), shown on every row, sources in the last-page
footnote, PT-L01 no longer labelled CVA. No grade moves.
"""

import inspect
import re

from app.api.v1 import posture
from app.services.posture import reference_ranges as rr
from app.services.posture.classifier import THRESHOLDS, classify
from app.services.posture.pdf_service import build_report_html
from app.services.posture.report_builder import build_report_response, measurement

REPORT_PARAMS = ("PT-L01", "PT-L05", "PT-L06", "PT-A01", "PT-A04", "PT-A05", "PT-A06", "PT-P01", "PT-P02")


def test_every_report_row_has_a_range_and_a_source():
    covered = {p for e in rr.SOURCES for p in e["params"].split(",")}
    for pid in REPORT_PARAMS:
        assert rr.screening_range(pid), pid
        assert pid in covered, pid


def test_ranges_are_read_from_thresholds():
    assert rr.screening_range("PT-L01") == "50° or more"
    assert rr.screening_range("PT-L05") == "Up to 4° either way"
    assert rr.screening_range("PT-L06") == "Up to 5° either way"
    assert rr.screening_range("PT-A01") == "0 to 5°"
    assert rr.screening_range("PT-A04") == "0 to 3°"
    assert rr.screening_range("PT-A05") == rr.screening_range("PT-A06") == "0 to 5°"
    assert rr.screening_range("PT-P01") == "0 to 10 mm"
    assert rr.screening_range("PT-P02") == "0 to 5 mm"


def test_range_follows_a_band_change(monkeypatch):
    monkeypatch.setitem(THRESHOLDS, "PT-A04", {**THRESHOLDS["PT-A04"], "none_max": 4})
    assert rr.screening_range("PT-A04") == "0 to 4°"


def test_shown_range_matches_the_grade_at_its_edges():
    # The printed Normal band is exactly what classify() calls normal.
    assert classify("PT-A04", 3.0) == "none" and classify("PT-A04", 3.01) != "none"
    assert classify("PT-L01", 50.0) == "none" and classify("PT-L01", 49.99) != "none"
    assert classify("PT-L05", -4.0) == "none" and classify("PT-L05", 4.01) != "none"


def test_measurement_payload_carries_the_range():
    m = measurement("PT-P02", "Shoulder Level Asymmetry", 9.2, "mm", "mild")
    assert m["screeningRange"] == "0 to 5 mm"
    assert measurement("PT-X99", "Unknown", 1.0, "°", "none")["screeningRange"] == ""


def test_pt_l01_is_not_labelled_cva():
    assert "CVA" not in rr.LABELS["PT-L01"]
    src = inspect.getsource(posture)
    assert '"Forward Head (CVA)"' not in src
    assert "calc_cva(" in src  # function name unchanged


def _report(**extra):
    views = {
        "side": {"measurements": [measurement("PT-L01", rr.LABELS["PT-L01"], 72.0, "°", "none")]},
        "front": {"measurements": [measurement("PT-A04", "Pelvic Obliquity", 2.1, "°", "none")]},
        "back": {"measurements": [measurement("PT-P02", "Shoulder Level Asymmetry", 9.2, "mm", "mild")]},
    }
    return {"patient": {"name": "Sample Patient"}, "views": views, **extra}


def test_pdf_has_the_range_column_and_the_footnote():
    html = build_report_html(_report())
    assert "<th>AV screening range</th>" in html
    assert '<td class="range">0 to 5 mm</td>' in html
    assert '<td class="range">50° or more</td>' in html
    assert "AV screening ranges and sources" in html
    assert "Moharrami et al. 2023" in html and "0 to 5.6°" in html
    assert "not the C7-based craniovertebral angle" in html
    assert "AV clinical team, Oct 2026" in html
    text = re.sub(r"data:[^\"')]+", "", html)  # base64 images can contain any letters
    assert "no source" not in text.lower()
    assert "CVA" not in text


def test_pdf_range_comes_from_the_server_not_the_posted_report():
    report = _report()
    report["views"]["back"]["measurements"][0]["screeningRange"] = "0 to 999 mm"
    html = build_report_html(report)
    assert "0 to 999 mm" not in html
    assert '<td class="range">0 to 5 mm</td>' in html


def test_no_below_within_above_and_moharrami_only_in_the_footnote():
    html = build_report_html(_report())
    for word in ("Below", "Within", "Above"):
        assert f">{word}<" not in html
    body, footnote = html.split("AV screening ranges and sources", 1)
    assert "5.6" not in body.split("<body>", 1)[1]
    assert "5.6" in footnote


def test_report_response_carries_the_footnote_for_the_web():
    r = build_report_response({}, {"measurements": []}, {"measurements": []}, {"measurements": []}, {})
    names = [s["name"] for s in r["screeningSources"]]
    assert names[0] == rr.LABELS["PT-L01"]
    assert "Pelvic Obliquity" in names
    assert r["screeningNote"] == rr.SCREENING_NOTE
