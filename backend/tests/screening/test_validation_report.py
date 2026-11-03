"""The committed scoring validation report must match the scoring engine."""

from __future__ import annotations

from tests.screening.validation_report import REPORT_PATH, render


def test_every_validation_check_passes():
    _, report = render()
    assert report.cases > 0
    assert report.failures == []


def test_committed_report_is_current():
    text, _ = render()
    assert REPORT_PATH.read_text(encoding="utf-8") == text, (
        "Report is out of date. Run: python -m tests.screening.validation_report --write"
    )
