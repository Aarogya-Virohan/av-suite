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

from app.services.posture.classifier import THRESHOLDS

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

# Footnote lead line, shared by the PDF and the web report.
SCREENING_NOTE = (
    "Ranges are those the AV screening grade treats as Normal; not "
    "population reference values."
)

# One footnote entry per row on the report. Pelvic obliquity, the longest
# entry, is last so the footnote columns balance. "basis" is the
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
    {
        "params": "PT-A04",
        "basis": f"{AV_TEAM}, informed by Ferreira et al. 2011.",
        "note": "Published reference 0 to 5.6\u00b0 (Moharrami et al. 2023, "
        "standing pelvic radiographs); not directly comparable.",
    },
]

# Footnote names, so a footnote line reads the same as the row it explains.
SOURCE_NAMES: dict[str, str] = {
    "PT-L01": LABELS["PT-L01"],
    "PT-L05": "Trunk Lean",
    "PT-L06": "Knee Flexion / Hyperextension",
    "PT-A01": "Head Lateral Tilt",
    "PT-A04": "Pelvic Obliquity",
    "PT-A05,PT-A06": "Knee Alignment (Hip-Knee-Ankle)",
    "PT-P01": "Trunk Lateral Deviation",
    "PT-P02": "Shoulder Level Asymmetry",
}


def _num(value: float) -> str:
    return f"{value:g}"


def screening_range(param_id: str) -> str:
    """
    The Normal band of `param_id` as printed text, read from THRESHOLDS.
    Empty when the parameter has no band or no unit here.
    """
    rule = THRESHOLDS.get(param_id)
    unit = UNITS.get(param_id)
    if not rule or unit is None:
        return ""
    sep = "" if unit == "°" else " "
    direction = rule.get("direction")
    if direction == "higher_worse" and "none_max" in rule:
        return f"0 to {_num(rule['none_max'])}{sep}{unit}"
    if direction == "lower_worse" and "none_min" in rule:
        return f"{_num(rule['none_min'])}{sep}{unit} or more"
    if direction == "centred" and "none_low" in rule and "none_high" in rule:
        low, high = rule["none_low"], rule["none_high"]
        if low == -high:
            # These rows print the size only and name the direction in the
            # label (report_builder.DIRECTION_NAMED_PARAMS).
            return f"Up to {_num(high)}{sep}{unit} either way"
        return f"{_num(low)} to {_num(high)}{sep}{unit}"
    return ""


def source_lines() -> list[tuple[str, str]]:
    """
    (row names, footnote text) for the sources footnote, in report order.
    Rows with the same source share one line, so the footnote fits the
    last page (the report stays three pages).
    """
    grouped: dict[str, list[str]] = {}
    for entry in SOURCES:
        text = entry["basis"].rstrip(".") + "."
        if entry["note"]:
            text += " " + entry["note"]
        grouped.setdefault(text, []).append(SOURCE_NAMES[entry["params"]])
    return [(", ".join(names), text) for text, names in grouped.items()]
