"""
AV screening ranges and their sources on the posture report, 17 November 2026.

The founders' feedback asked for a range next to every value, as on a blood
report. Onkar's decision (17 Nov): each row shows the value, the range our
own grading already treats as Normal ("AV screening range"), and the
existing grade. Nothing here grades anything and no band moves: the range
is read from classifier.THRESHOLDS, the one source of truth, so the number
printed can never drift from the number that graded the patient.

Published reference values are not shown next to the values. Most measures
have no published norm for a photograph and these landmarks (research,
17 Nov), and the one that does (pelvic obliquity) was measured on
radiographs. Sources go in the footnote on the last page instead: the
published basis where there is one, otherwise the AV clinical team.

Labels: "Forward Head (CVA)" was renamed on the same date. The tool measures
the ear to the shoulder point, not the C7 to tragus craniovertebral angle,
so the report must not call it CVA. PT-L01 and calc_cva keep their names so
saved reports and the synthesis mapping are unchanged.
"""

from __future__ import annotations

from typing import Any

from app.services.posture.classifier import BANDS_UNDER_REVIEW, THRESHOLDS

# Report labels that are not built from the measurement itself. The knee
# and trunk rows pick their labels from the sign in api/v1/posture.py.
LABELS: dict[str, str] = {
    "PT-L01": "Head Position (ear–shoulder angle)",
}

UNITS: dict[str, str] = {
    "PT-L01": "°",
    "PT-L05": "°",
    "PT-L06": "°",
    "PT-A01": "°",
    "PT-A04": "°",
    "PT-A05": "°",
    "PT-A06": "°",
    "PT-P01": "mm",
    "PT-P02": "mm",
}

AV_TEAM = "AV clinical team, Oct 2026"

# Shared by the PDF and the web report (Onkar's review, 17 Nov: the column
# is "Normal range", the section below explains the basis).
RANGE_HEADING = "Normal range"
SOURCES_HEADING = "Normal ranges: basis and sources"
SCREENING_NOTE = (
    "Normal range is the band the AV screening grade treats as Normal. "
    "It is a screening range, not a population reference value."
)

# POS-4 (21 Nov 2026): printed in the range cell of a band with no
# published basis, and added to its line in the sources section.
UNDER_REVIEW_RANGE = "Under review"
UNDER_REVIEW_NOTE = (
    "Normal band under review with the AV clinical team; this row is "
    "measured but not graded."
)

# One entry per report row, in report order. "basis" is the
# published work the AV clinical team cited when setting the band (code
# comments in classifier.py); "AV_TEAM" alone where none was given.
SOURCES: list[dict[str, str]] = [
    {
        "params": "PT-L01",
        "basis": AV_TEAM,
        "note": "Ear to shoulder point, not the C7-based craniovertebral angle.",
    },
    {
        "params": "PT-L05",
        "basis": f"{AV_TEAM}, informed by Ferreira et al. 2011 (photographs).",
        "note": "",
    },
    {
        "params": "PT-L06",
        "basis": f"{AV_TEAM}; recurvatum is commonly defined as over 5\u00b0 "
        "(cited in Dierick et al. 2020).",
        "note": "",
    },
    {
        "params": "PT-A01",
        "basis": f"{AV_TEAM}, informed by Ferreira et al. 2011 (photographs).",
        "note": "",
    },
    {
        "params": "PT-A04",
        "basis": f"{AV_TEAM}, informed by Ferreira et al. 2011.",
        "note": "Published reference 0 to 5.6\u00b0 (Moharrami et al. 2023, J Exp "
        "Orthop; standing pelvic radiographs, 134 adults); not directly "
        "comparable with this photograph-based angle.",
    },
    {
        "params": "PT-A05,PT-A06",
        "basis": f"{AV_TEAM}, informed by Bellemans et al. 2012 (standing "
        "radiographs).",
        "note": "",
    },
    {
        "params": "PT-P01",
        "basis": AV_TEAM,
        "note": "",
    },
    {
        "params": "PT-P02",
        "basis": AV_TEAM,
        "note": "",
    },
]

def _num(value: float) -> str:
    return f"{value:g}"


def screening_range(param_id: str) -> str:
    """
    The Normal band of `param_id` as printed text, read from THRESHOLDS, in
    one format on every surface: "\u2264 5\u00b0", "\u2265 50\u00b0",
    "\u00b1 4\u00b0", "\u2264 10 mm" (Onkar's review, 17 November 2026).
    Empty when the parameter has no band or no unit here.
    """
    if param_id in BANDS_UNDER_REVIEW:
        return UNDER_REVIEW_RANGE
    rule = THRESHOLDS.get(param_id)
    unit = UNITS.get(param_id)
    if not rule or unit is None:
        return ""
    sep = "" if unit == "\u00b0" else " "
    direction = rule.get("direction")
    if direction == "higher_worse" and "none_max" in rule:
        return f"\u2264 {_num(rule['none_max'])}{sep}{unit}"
    if direction == "lower_worse" and "none_min" in rule:
        return f"\u2265 {_num(rule['none_min'])}{sep}{unit}"
    if direction == "centred" and "none_low" in rule and "none_high" in rule:
        low, high = rule["none_low"], rule["none_high"]
        if low == -high:
            # These rows print the size only and name the direction in the
            # label (report_builder.DIRECTION_NAMED_PARAMS).
            return f"\u00b1 {_num(high)}{sep}{unit}"
        return f"{_num(low)} to {_num(high)}{sep}{unit}"
    return ""


# Row order of the report, so the sources read in the order of the tables.
VIEW_ORDER = ("side", "front", "back")


def row_labels(views: dict[str, Any] | None) -> dict[str, list[str]]:
    """
    The label each report row carries, by paramId, in report order. This is
    the one place a measure's printed name comes from (the label the route
    put on the row, api/v1/posture.py), so the sources section and the radar
    chart name a measure exactly as its table row does, including the knee
    and trunk rows whose names follow the sign (Onkar's review, 17 Nov 2026).
    """
    names: dict[str, list[str]] = {}
    for view_name in VIEW_ORDER:
        view = (views or {}).get(view_name) or {}
        for m in view.get("measurements") or []:
            label = m.get("label")
            pid = m.get("paramId")
            if not label or not pid:
                continue
            seen = names.setdefault(pid, [])
            if label not in seen:
                seen.append(label)
    return names


def source_lines(views: dict[str, Any] | None) -> list[tuple[str, str]]:
    """
    (row name, basis) for the sources section, one line per measure, named
    with the report's own row labels. A measure with no row in this report
    gets no line: there is nothing in the tables for it to explain.
    """
    labels = row_labels(views)
    lines = []
    for entry in SOURCES:
        names: list[str] = []
        for pid in entry["params"].split(","):
            for label in labels.get(pid, []):
                if label not in names:
                    names.append(label)
        if not names:
            continue
        text = entry["basis"].rstrip(".") + "."
        if entry["note"]:
            text += " " + entry["note"]
        if any(pid in BANDS_UNDER_REVIEW for pid in entry["params"].split(",")):
            text += " " + UNDER_REVIEW_NOTE
        lines.append((", ".join(names), text))
    return lines
