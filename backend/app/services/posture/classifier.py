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
    "PT-A03": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 20,
    },
    "PT-A04": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 20,
    },
    "PT-A10": {
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
    # Knee hyperextension — negative values are worse (lower_worse on absolute scale).
    # none:  > -6 deg  (positive = flexion, harmless)
    # mild:  -6 to -10
    # moderate: -11 to -15
    # severe: < -15
    "PT-L06": {
        "direction": "lower_worse",
        "none_min": -6,
        "mild_min": -10,
        "moderate_min": -15,
    },
    # Elbow carrying angle — gender-specific (handled separately in classify()).
    "PT-A08": {
        "direction": "higher_worse",
        "none_max": {"male": 11, "female": 15},
        "mild_max": {"male": 16, "female": 20},
        "moderate_max": {"male": 22, "female": 26},
    },
}


def classify(
    param_id: str,
    value: float,
    gender: str = "male",
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

        # Support gender-keyed thresholds (dict) or plain scalars.
        def _threshold(key: str) -> float:
            v = rule[key]
            if isinstance(v, dict):
                g = gender.lower() if gender else "male"
                return v.get(g, v.get("male"))
            return v

        if value <= _threshold("none_max"):
            return "none"

        if value <= _threshold("mild_max"):
            return "mild"

        if value <= _threshold("moderate_max"):
            return "moderate"

        return "severe"

    raise ValueError(f"Unknown direction: {direction}")
