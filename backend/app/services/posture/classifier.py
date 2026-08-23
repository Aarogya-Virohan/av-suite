from typing import Literal, TypedDict

Severity = Literal[
    "none",
    "mild",
    "moderate",
    "severe",
    "insufficient_data",
    "not_available",
]


class ThresholdRule(TypedDict):
    direction: Literal[
        "lower_worse",
        "higher_worse",
    ]


THRESHOLDS: dict[str, dict] = {
    "PT-L01": {
        "direction": "lower_worse",
        "none_min": 50,
        "mild_min": 45,
        "moderate_min": 40,
    },
    "PT-A02": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 20,
    },
    "PT-A06": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 7,
        "moderate_max": 12,
    },
    "PT-A03": {
        "direction": "higher_worse",
        "none_max": 10,
        "mild_max": 20,
        "moderate_max": 30,
    },
    "PT-A04": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 5,
        "moderate_max": 10,
    },
    "PT-A10": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 6,
        "moderate_max": 10,
    },
    "PT-L04": {
        "direction": "higher_worse",
        "none_max": 10,
        "mild_max": 15,
        "moderate_max": 20,
    },
    "PT-L05": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 6,
        "moderate_max": 10,
    },
    "PT-A01": {
        "direction": "higher_worse",
        "none_max": 2,
        "mild_max": 5,
        "moderate_max": 10,
    },
    "PT-A05": {
        "direction": "higher_worse",
        "none_max": 5,
        "none_max_female": 7,
        "mild_max": 9,
        "moderate_max": 13,
    },
    "PT-P01": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 15,
        "moderate_max": 25,
    },
    "PT-P02": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 20,
    },
    "PT-P03": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 8,
        "moderate_max": 12,
    },
    "PT-P04": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 8,
        "moderate_max": 12,
    },
    "PT-P05": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 8,
        "moderate_max": 12,
    },
    "PT-L06": {
        "direction": "lower_worse",
        "none_min": -5,
        "mild_min": -10,
        "moderate_min": -15,
    },
    "PT-A08": {
        "direction": "higher_worse",
        "none_max": 10,
        "none_max_female": 15,
        "mild_max": 15,
        "mild_max_female": 20,
        "moderate_max": 20,
        "moderate_max_female": 25,
    },
}


# Measurement noise near a hard cut-off can flip a patient's grade. A value
# of 5.02 against a 5.00 boundary is not meaningfully different from 4.98,
# but one grades MILD and the other NONE. The pose model's own error is
# reported at roughly 1.5-2 degrees for 2D frontal angles, so any value
# sitting within that distance of a boundary cannot be assigned to a tier
# with confidence.
#
# These margins are provisional. Per clinical review, the severity tiers
# themselves have no published basis for most parameters and will be set
# from collected data; these buffers should be revised at the same time.
BORDERLINE_MARGIN_DEGREES = 2.0
BORDERLINE_MARGIN_MM = 2.0


def is_borderline(param_id: str, value: float, unit: str) -> bool:
    """
    True when `value` sits close enough to any severity boundary that
    measurement noise could move it into an adjacent tier.

    This does not change the assigned severity. It marks the grade as
    provisional so a clinician knows not to lean on it.
    """

    if param_id not in THRESHOLDS:
        return False

    if not isinstance(value, (int, float)):
        return False

    margin = BORDERLINE_MARGIN_MM if unit == "mm" else BORDERLINE_MARGIN_DEGREES

    rule = THRESHOLDS[param_id]

    boundaries = [
        rule.get(key)
        for key in (
            "none_min",
            "mild_min",
            "moderate_min",
            "none_max",
            "mild_max",
            "moderate_max",
            "none_max_female",
            "mild_max_female",
            "moderate_max_female",
        )
        if rule.get(key) is not None
    ]

    return any(abs(value - b) <= margin for b in boundaries)


SEVERITY_LABELS: dict[str, str] = {
    "none": "NONE",
    "mild": "MILD",
    "moderate": "MODERATE",
    "severe": "SEVERE",
    "insufficient_data": "INSUFFICIENT DATA \u2013 RETAKE PHOTO",
    "not_available": "PATIENT HEIGHT REQUIRED",
}


def classify(
    param_id: str,
    value: float,
    gender: str | None = None,
) -> Severity:
    """
    Classify a posture measurement into a severity band.

    Parameters
    ----------
    param_id:
        Clinical posture parameter identifier
        e.g. PT-L01

    value:
        Raw measurement value

    gender:
        Patient gender, only used for parameters with gender-dependent
        normal ranges (currently PT-A05 — Knee Valgus).

    Returns
    -------
    Severity
    """

    if param_id not in THRESHOLDS:
        raise ValueError(f"Unknown parameter: {param_id}")

    rule = THRESHOLDS[param_id]

    direction = rule["direction"]

    none_max = rule.get("none_max")
    mild_max = rule.get("mild_max")
    moderate_max = rule.get("moderate_max")

    is_female = bool(gender) and gender.strip().lower().startswith("f")

    if is_female:
        none_max = rule.get("none_max_female", none_max)
        mild_max = rule.get("mild_max_female", mild_max)
        moderate_max = rule.get("moderate_max_female", moderate_max)

    if direction == "lower_worse":

        if value >= rule["none_min"]:
            return "none"

        if value >= rule["mild_min"]:
            return "mild"

        if value >= rule["moderate_min"]:
            return "moderate"

        return "severe"

    if direction == "higher_worse":

        if value <= none_max:
            return "none"

        if value <= mild_max:
            return "mild"

        if value <= moderate_max:
            return "moderate"

        return "severe"

    raise ValueError(f"Unknown direction: {direction}")
