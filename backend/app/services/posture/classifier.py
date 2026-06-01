from typing import Literal, TypedDict

Severity = Literal[
    "none",
    "mild",
    "moderate",
    "severe",
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
    "PT-L04": {
        "direction": "higher_worse",
        "none_max": 10,
        "mild_max": 15,
        "moderate_max": 20,
    },
    "PT-L05": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 15,
    },
}


def classify(
    param_id: str,
    value: float,
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

    Returns
    -------
    Severity
    """

    if param_id not in THRESHOLDS:
        raise ValueError(f"Unknown parameter: {param_id}")

    rule = THRESHOLDS[param_id]

    direction = rule["direction"]

    if direction == "lower_worse":

        if value >= rule["none_min"]:
            return "none"

        if value >= rule["mild_min"]:
            return "mild"

        if value >= rule["moderate_min"]:
            return "moderate"

        return "severe"

    if direction == "higher_worse":

        if value <= rule["none_max"]:
            return "none"

        if value <= rule["mild_max"]:
            return "mild"

        if value <= rule["moderate_max"]:
            return "moderate"

        return "severe"

    raise ValueError(f"Unknown direction: {direction}")
