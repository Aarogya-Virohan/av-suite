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

    if (
        param_id == "PT-A05"
        and gender
        and gender.strip().lower().startswith("f")
        and "none_max_female" in rule
    ):
        none_max = rule["none_max_female"]

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

        if value <= rule["mild_max"]:
            return "mild"

        if value <= rule["moderate_max"]:
            return "moderate"

        return "severe"

    raise ValueError(f"Unknown direction: {direction}")
