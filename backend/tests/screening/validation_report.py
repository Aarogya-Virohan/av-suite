"""Generate the Tool 03 scoring validation report (SRS section 7, deliverable 02).

The expected values come from the hand-written golden tables in
``test_scoring.py`` (written from the published norms, never derived from the
definitions under test). This module runs every case through the real scoring
engine and writes a Markdown report with expected and actual values side by
side. It exits with status 1 if any case does not match.

Run from ``backend/``:

    python -m tests.screening.validation_report            # check only
    python -m tests.screening.validation_report --write    # rewrite the report

``test_validation_report.py`` fails when the committed report is out of date.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.screening.registry import get_instrument
from app.screening.scoring import ScoringError, score
from tests.screening.test_scoring import (
    DASS21_GOLDEN,
    DASS_BANDS,
    DASS_ITEMS,
    GAD7_BANDS,
    GAD7_GOLDEN,
    PHQ9_BANDS,
    PHQ9_GOLDEN,
    answers,
    dass,
    expected_band,
    spread,
)

REPORT_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "screening" / "Scoring_Validation_Report.md"
)

PHQ9 = get_instrument("phq9")
GAD7 = get_instrument("gad7")
DASS21 = get_instrument("dass21")

DASS_ORDER = ("depression", "anxiety", "stress")
DASS_LABEL = {"depression": "Depression", "anxiety": "Anxiety", "stress": "Stress"}


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def ok(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def band_rows(table) -> list[str]:
    rows = []
    for lo, hi, label in table:
        rows.append(f"| {lo} to {hi} | {label} |")
    return rows


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.cases = 0
        self.failures: list[str] = []

    def add(self, *lines: str) -> None:
        self.lines.extend(lines)

    def check(self, name: str, passed: bool) -> str:
        self.cases += 1
        if not passed:
            self.failures.append(name)
        return ok(passed)


def phq9_section(r: Report) -> None:
    r.add(
        "## 2. PHQ-9 (depression)",
        "",
        f"Instrument `phq9` version `{PHQ9.version}`. Source: {PHQ9.citation}",
        "",
        "Scoring: 9 items, each 0 to 3, total 0 to 27. Referral at 10 or above"
        " (SRS 4.1.3). Item 9 above 0 sets the risk flag and forces referral"
        " (S-D-005, pending founder sign-off F1).",
        "",
        "Published bands:",
        "",
        "| Score | Band |",
        "|---|---|",
        *band_rows(PHQ9_BANDS),
        "",
        "### 2.1 Representative cases",
        "",
        "| # | Answers, items 1 to 9 | Expected total | Expected band | Expected referral | Expected risk flag | Actual total | Actual band | Actual referral | Actual risk flag | Result |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    )
    for n, (values, total, band, referral, risk) in enumerate(PHQ9_GOLDEN, start=1):
        res = score(PHQ9, answers("phq9", values))
        scale = res.scale("total")
        passed = (
            scale.score == total
            and scale.band_label == band
            and res.referral_flag is referral
            and res.risk_item_flag is risk
        )
        result = r.check(f"PHQ-9 case {n}", passed)
        r.add(
            f"| {n} | {' '.join(map(str, values))} | {total} | {band} | {yes_no(referral)}"
            f" | {yes_no(risk)} | {scale.score} | {scale.band_label}"
            f" | {yes_no(res.referral_flag)} | {yes_no(res.risk_item_flag)} | {result} |"
        )
    r.add(
        "",
        "Cases 11 and 12 have a low total but a non-zero answer on item 9, so the"
        " referral comes from the risk rule, not from the total.",
        "",
    )

    passed_all = 0
    for total in range(0, 28):
        responses = spread("phq9", [1, 2, 3, 4, 5, 6, 7, 8], min(total, 24))
        responses["phq9_9"] = total - 24 if total > 24 else 0
        scale = score(PHQ9, responses).scale("total")
        good = (
            scale.score == total
            and scale.band_label == expected_band(PHQ9_BANDS, total)
            and scale.referral is (total >= 10)
        )
        r.check(f"PHQ-9 total {total}", good)
        passed_all += good
    r.add(
        "### 2.2 Every possible total",
        "",
        f"Every total from 0 to 27 was scored and checked against the published"
        f" band and the referral threshold: {passed_all} of 28 match.",
        "",
    )


def gad7_section(r: Report) -> None:
    r.add(
        "## 3. GAD-7 (anxiety)",
        "",
        f"Instrument `gad7` version `{GAD7.version}`. Source: {GAD7.citation}",
        "",
        "Scoring: 7 items, each 0 to 3, total 0 to 21. Referral at 10 or above"
        " (SRS 4.1.3). GAD-7 has no risk item.",
        "",
        "Published bands:",
        "",
        "| Score | Band |",
        "|---|---|",
        *band_rows(GAD7_BANDS),
        "",
        "### 3.1 Representative cases",
        "",
        "| # | Answers, items 1 to 7 | Expected total | Expected band | Expected referral | Actual total | Actual band | Actual referral | Result |",
        "|---|---|---|---|---|---|---|---|---|",
    )
    for n, (values, total, band, referral) in enumerate(GAD7_GOLDEN, start=1):
        res = score(GAD7, answers("gad7", values))
        scale = res.scale("total")
        passed = (
            scale.score == total
            and scale.band_label == band
            and res.referral_flag is referral
            and res.risk_item_flag is False
        )
        result = r.check(f"GAD-7 case {n}", passed)
        r.add(
            f"| {n} | {' '.join(map(str, values))} | {total} | {band} | {yes_no(referral)}"
            f" | {scale.score} | {scale.band_label} | {yes_no(res.referral_flag)} | {result} |"
        )
    r.add("")

    passed_all = 0
    for total in range(0, 22):
        scale = score(GAD7, spread("gad7", list(range(1, 8)), total)).scale("total")
        good = (
            scale.score == total
            and scale.band_label == expected_band(GAD7_BANDS, total)
            and scale.referral is (total >= 10)
        )
        r.check(f"GAD-7 total {total}", good)
        passed_all += good
    r.add(
        "### 3.2 Every possible total",
        "",
        f"Every total from 0 to 21 was scored and checked against the published"
        f" band and the referral threshold: {passed_all} of 22 match.",
        "",
    )


def dass21_section(r: Report) -> None:
    r.add(
        "## 4. DASS-21 (depression, anxiety, stress)",
        "",
        "SRS section 6 lists DASS-21 validation as a stretch requirement for"
        " v1.0. It is validated to the same standard as PHQ-9 and GAD-7.",
        "",
        f"Instrument `dass21` version `{DASS21.version}`. Source: {DASS21.citation}",
        "",
        "Scoring: three subscales of 7 items each, items 0 to 3. Each subscale"
        " score is the item sum multiplied by 2 (range 0 to 42). Referral when"
        " any subscale is Severe or above (SRS 4.1.3).",
        "",
        "| Subscale | Items |",
        "|---|---|",
        *[
            f"| {DASS_LABEL[s]} | {', '.join(map(str, DASS_ITEMS[s]))} |"
            for s in DASS_ORDER
        ],
        "",
        "Published bands (scores after x2):",
        "",
        "| Band | Depression | Anxiety | Stress |",
        "|---|---|---|---|",
    )
    for idx in range(5):
        label = DASS_BANDS["depression"][idx][2]
        cells = []
        for s in DASS_ORDER:
            lo, hi, _ = DASS_BANDS[s][idx]
            cells.append(f"{lo}+" if idx == 4 else f"{lo} to {hi}")
        r.add(f"| {label} | {' | '.join(cells)} |")
    r.add(
        "",
        "### 4.1 Representative cases",
        "",
        "Raw sums are the item totals per subscale before x2, in the order"
        " Depression, Anxiety, Stress.",
        "",
        "| # | Raw sums | Expected scores | Expected bands | Expected referral | Actual scores | Actual bands | Actual referral | Result |",
        "|---|---|---|---|---|---|---|---|---|",
    )
    for n, (raw, scored, bands, referral) in enumerate(DASS21_GOLDEN, start=1):
        res = score(DASS21, dass(*raw))
        actual_scores = tuple(res.scale(s).score for s in DASS_ORDER)
        actual_bands = tuple(res.scale(s).band_label for s in DASS_ORDER)
        actual_raw = tuple(res.scale(s).raw_sum for s in DASS_ORDER)
        passed = (
            actual_raw == tuple(raw)
            and actual_scores == tuple(scored)
            and actual_bands == tuple(bands)
            and res.referral_flag is referral
            and res.risk_item_flag is False
        )
        result = r.check(f"DASS-21 case {n}", passed)
        r.add(
            f"| {n} | {' / '.join(map(str, raw))} | {' / '.join(map(str, scored))}"
            f" | {' / '.join(bands)} | {yes_no(referral)}"
            f" | {' / '.join(map(str, actual_scores))} | {' / '.join(actual_bands)}"
            f" | {yes_no(res.referral_flag)} | {result} |"
        )
    r.add("")

    passed_all = 0
    for scale_id in DASS_ORDER:
        for raw in range(0, 22):
            sums = {"depression": 0, "anxiety": 0, "stress": 0, scale_id: raw}
            res = score(DASS21, dass(sums["depression"], sums["anxiety"], sums["stress"]))
            scale = res.scale(scale_id)
            band = expected_band(DASS_BANDS[scale_id], raw * 2)
            good = (
                scale.score == raw * 2
                and scale.band_label == band
                and scale.referral is (band in ("Severe", "Extremely severe"))
            )
            r.check(f"DASS-21 {scale_id} raw {raw}", good)
            passed_all += good
    r.add(
        "### 4.2 Every possible subscale score",
        "",
        "Every raw sum from 0 to 21 on each subscale (66 scores) was scored and"
        f" checked against the published band and the referral rule: {passed_all}"
        " of 66 match.",
        "",
    )


INVALID_CASES = [
    ("Only 8 of 9 items answered", answers("phq9", [0] * 8), "Missing"),
    ("Unknown item id", {**answers("phq9", [0] * 9), "phq9_99": 0}, "Unknown"),
    ("Answer value 4 (above the scale)", answers("phq9", [0] * 8 + [4]), "not a valid option"),
    ("Answer value -1", answers("phq9", [0] * 8 + [-1]), "not a valid option"),
    ("Answer given as true/false", answers("phq9", [0] * 8 + [True]), "integer"),
    (
        "Difficulty question with value 7",
        {**answers("phq9", [0] * 9), "phq9_difficulty": 7},
        "not a valid option",
    ),
]


def invalid_section(r: Report) -> None:
    r.add(
        "## 5. Invalid input is rejected",
        "",
        "The engine refuses to score incomplete or out-of-range answers instead"
        " of returning a wrong number.",
        "",
        "| Input | Expected | Actual | Result |",
        "|---|---|---|---|",
    )
    for name, responses, message in INVALID_CASES:
        try:
            score(PHQ9, responses)
            actual, passed = "Scored (not rejected)", False
        except ScoringError as exc:
            passed = message in str(exc)
            actual = "Rejected" if passed else f"Rejected with another reason: {exc}"
        result = r.check(f"invalid: {name}", passed)
        r.add(f"| {name} | Rejected | {actual} | {result} |")

    base = answers("phq9", [1] * 9)
    with_difficulty = {**base, "phq9_difficulty": 3}
    same = (
        score(PHQ9, base).scale("total").score
        == score(PHQ9, with_difficulty).scale("total").score
        == 9
    )
    result = r.check("difficulty item not scored", same)
    r.add(
        "",
        "The PHQ-9 difficulty question (\"how difficult have these problems"
        " made it...\") is shown and stored but is not part of the score, as in"
        f" the published form. All 9 items at 1 give a total of 9 with or without"
        f" a difficulty answer of 3: {result}.",
        "",
    )


def build() -> Report:
    r = Report()
    body = Report()
    phq9_section(body)
    gad7_section(body)
    dass21_section(body)
    invalid_section(body)

    r.add(
        "# Tool 03 Psycho-Social Screening: Scoring Validation Report",
        "",
        "SRS section 7, deliverable 02. This file is generated by"
        " `backend/tests/screening/validation_report.py`. Do not edit it by hand.",
        "",
        "## 1. Summary",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| PHQ-9 representative cases | {len(PHQ9_GOLDEN)} (SRS asks for at least 5) |",
        f"| GAD-7 representative cases | {len(GAD7_GOLDEN)} (SRS asks for at least 5) |",
        f"| DASS-21 representative cases (stretch) | {len(DASS21_GOLDEN)} |",
        "| Every possible score checked | PHQ-9 0 to 27, GAD-7 0 to 21, DASS-21 each subscale 0 to 42 |",
        f"| Total checks | {body.cases} |",
        f"| Matching the published norms | {body.cases - len(body.failures)} of {body.cases} |",
        "",
        "How the expected values were set: they are typed by hand from the"
        " published papers listed in each section (the same sources as the SRS"
        " appendix) and kept in `backend/tests/screening/test_scoring.py`. They"
        " are never computed from the scoring code being tested. The actual"
        " values come from running each case through the production scoring"
        " function `app.screening.scoring.score`.",
        "",
        "Band label note: the lowest PHQ-9 and GAD-7 band is called"
        " \"None-minimal\", the wording of the original papers. The SRS table says"
        " \"None\". The score ranges are identical (S-D-008).",
        "",
        "Not compared yet: the SRS also points to `AV_Suite_Clinical_Reference_v1.xlsx`"
        " (Severity_Logic sheet) for referral thresholds. That file has not been"
        " provided (S-L-003, P-05). The thresholds here follow SRS 4.1.3 and the"
        " published norms.",
        "",
        "How to reproduce, from `backend/`:",
        "",
        "```",
        "python -m tests.screening.validation_report",
        "pytest tests/screening/test_scoring.py tests/screening/test_validation_report.py",
        "```",
        "",
    )
    r.lines.extend(body.lines)
    r.cases = body.cases
    r.failures = body.failures
    return r


def render() -> tuple[str, Report]:
    report = build()
    return "\n".join(report.lines).rstrip() + "\n", report


def main(argv: list[str]) -> int:
    text, report = render()
    if report.failures:
        print(f"{len(report.failures)} of {report.cases} checks FAILED:")
        for name in report.failures:
            print(f"  - {name}")
        return 1
    if "--write" in argv:
        REPORT_PATH.write_text(text, encoding="utf-8")
        print(f"Wrote {REPORT_PATH} ({report.cases} checks, all pass)")
    else:
        print(f"{report.cases} checks, all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
