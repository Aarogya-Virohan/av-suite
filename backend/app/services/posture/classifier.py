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
    "PT-L08": {
        "direction": "range_centered",
        "normal_min": 8,
        "normal_max": 15,
        "mild_min_low": 5,
        "moderate_min_low": 3,
        "mild_max_high": 20,
        "moderate_max_high": 25,
    },
}


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

    if direction == "range_centered":

        normal_min = rule["normal_min"]
        normal_max = rule["normal_max"]

        if normal_min <= value <= normal_max:
            return "none"

        if value < normal_min:

            if value >= rule["mild_min_low"]:
                return "mild"

            if value >= rule["moderate_min_low"]:
                return "moderate"

            return "severe"

        # value > normal_max

        if value <= rule["mild_max_high"]:
            return "mild"

        if value <= rule["moderate_max_high"]:
            return "moderate"

        return "severe"

    raise ValueError(f"Unknown direction: {direction}")
