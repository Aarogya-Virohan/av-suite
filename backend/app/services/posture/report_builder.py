from typing import Any

from app.services.posture.classifier import SEVERITY_LABELS, is_borderline


# Direction wording, keyed on paramId rather than label so a label change
# cannot silently detach the copy from its parameter.
#
# Two kinds of finding. Some parameters say which way the patient deviates,
# others say which landmark sits higher. Reporting both in one shared phrasing
# was rejected: it reads as a contradiction when a head tilts one way and the
# ear on the other side sits higher, and it discards which side compensates.
# The deviation rows keep a preposition so the two kinds stay distinguishable
# at a glance, and the higher rows name the body part because two of them are
# shoulders in different sections of the report.
SIDE_WORDING: dict[str, dict[str, str]] = {
    "PT-A01": {"left": "Tilted to left", "right": "Tilted to right"},
    "PT-L01": {"anterior": "Head anterior to shoulder", "posterior": "Head posterior to shoulder"},
    "PT-A03": {"left": "Shifted to left", "right": "Shifted to right"},
    "PT-P01": {"left": "Shifted to left", "right": "Shifted to right"},
    "PT-A02": {"left": "Left shoulder higher", "right": "Right shoulder higher"},
    "PT-A10": {"left": "Left ear higher", "right": "Right ear higher"},
    "PT-A04": {"left": "Left hip higher", "right": "Right hip higher"},
    "PT-P02": {"left": "Left shoulder higher", "right": "Right shoulder higher"},
    # Founders, 11 October 2026: the knee row names its direction in plain
    # words under the "Knee Alignment (Hip-Knee-Ankle)" label.
    "PT-A05": {"valgus": "Knock-knee"},
    "PT-A06": {"varus": "Bow-leg"},
}


def measurement(
    param_id: str,
    label: str,
    value: float,
    unit: str,
    severity: str,
    side: str | None = None,
) -> dict[str, Any]:

    # A grade sitting within measurement noise of a boundary is reported as
    # provisional rather than as a settled tier. Checked here because every
    # parameter in the report passes through this function.
    borderline = severity in ("none", "mild", "moderate", "severe") and is_borderline(
        param_id, value, unit
    )

    return {
        "paramId": param_id,
        "label": label,
        "value": round(value, 2) if isinstance(value, (int, float)) else value,
        "unit": unit,
        "severityLabel": SEVERITY_LABELS.get(severity, severity.upper()),
        "severity": severity,
        "borderline": borderline,
        # Which way the deviation goes. Magnitude alone is not a clinical
        # finding: a left head tilt and a right head tilt carry different
        # muscle patterns and different corrections, and the report was
        # printing the same row for both. Thresholds stay on the magnitude,
        # so this adds information without moving any grade.
        "side": side,
        # The same direction as display copy. Kept here so the clinical
        # wording is defined once and every surface prints the identical
        # phrase; a consumer that renders side itself would be re-inventing
        # it. This is always populated when side is present, including at
        # severities a given surface chooses not to show it at. Whether to
        # display it is a presentation decision and belongs to the surface,
        # not to the report.
        "sideLabel": SIDE_WORDING.get(param_id, {}).get(side or ""),
    }


def summarise_view(measurements: list[dict[str, Any]]) -> str:
    """
    One-line summary under each view, built only from the grades in its rows.

    Until 11 October 2026 it listed MODERATE and SEVERE rows and otherwise
    printed "Posture appears within acceptable limits." That sentence was
    ours, not the founders', and it was wrong twice over: it appeared beside
    rows graded MILD DEVIATION, which the founders define as a deviation
    (10 October, answer 1), and beside rows that could not be measured at
    all. The summary now restates the rows and makes no judgement of its
    own: moderate or severe first, then mild, then anything not measured.
    """

    def labels(severities: tuple[str, ...]) -> list[str]:
        return [m["label"] for m in measurements if m.get("severity") in severities]

    major = labels(("moderate", "severe"))
    mild = labels(("mild",))
    unmeasured = labels(("insufficient_data", "not_available"))

    parts: list[str] = []

    if major:
        parts.append("Moderate or severe deviation in: " + ", ".join(major) + ".")
    elif mild:
        parts.append("No moderate or severe deviation.")

    if mild:
        parts.append("Mild deviation in: " + ", ".join(mild) + ".")

    if not major and not mild:
        parts.append(
            "All measured parameters graded normal."
            if len(unmeasured) < len(measurements)
            else "No parameter could be measured on this view."
        )

    if unmeasured and len(unmeasured) < len(measurements):
        parts.append("Not measured: " + ", ".join(unmeasured) + ".")

    return " ".join(parts)


def build_side_view_result(
    measurements: list[dict[str, Any]],
    photo_url: str,
    accuracy: float = 0.0,
    capture_source: str = "unknown",
) -> dict[str, Any]:

    interpretation = summarise_view(measurements)

    return {
        "photoUrl": photo_url,
        "accuracy": round(accuracy, 4),
        "measurements": measurements,
        "interpretation": interpretation,
        "captureSource": capture_source,
    }


# Which state of the analysis code produced a report.
#
# Grades move when thresholds, sign conventions or calibration change, so
# two reports for the same patient are only comparable if they came from
# the same version. Without this stamp there is no way to tell a real
# change in a patient from a change in our own bands, and the September
# work changed several: PT-A03 and PT-P01 onto one threshold set, PT-P03
# onto population-centred bands, PT-A01's normal ceiling above the noise
# floor, PT-L05 and PT-P03 signed.
#
# Bump this whenever a change moves a number or a grade on the report.
# Do not bump it for wording, layout or comments.
#
# Known still to come, which will each need a bump: the millimetre
# calibration constant in calculator.py (currently 0.97, which inflates
# every millimetre value by roughly 15 percent, and must be measured on
# our own photographs before it is changed), and any threshold the
# founders set from their own reference ranges.
# 2026-10-10: founder answers applied (CVA bands, head tilt from the
# pupillary line, shoulder level and trunk shift from the back view only,
# deviation labels, no global score). Also covers the 3 October PNG capture
# and captureSource, which changed what reaches the model without a bump.
# 2026-10-11: founders' answers of 11 October. Knee bands 5/9/13 for both
# directions with no female allowance, knee rows renamed, ear level removed.
# 2026-10-11.2: founders' second reply the same day. New bands for head
# tilt, pelvic obliquity, trunk shift and trunk lean; a bent knee now grades.
ANALYSIS_VERSION = "2026-10-11.2"


def build_report_response(
    patient: dict[str, Any],
    side_view: dict[str, Any],
    front_view: dict[str, Any],
    back_view: dict[str, Any],
    synthesis: dict[str, Any],
) -> dict[str, Any]:
    # globalIndex is no longer in the payload: Global Stability Index
    # removed from the report on 10 October 2026 by the founders (Q5): a single
    # score masks a localised finding behind an average, and its weights were
    # never sourced. calculate_global_index stays in scoring.py with nothing
    # calling it. The founders' replacement, a regional profile, is not built
    # yet. See docs/decisions.md, 10 October.

    return {
        "patient": patient,
        "analysisVersion": ANALYSIS_VERSION,
        "views": {
            "side": side_view,
            "front": front_view,
            "back": back_view,
        },
        "synthesis": synthesis,
    }
