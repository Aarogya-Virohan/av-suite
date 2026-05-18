from typing import Literal

Severity = Literal["none", "mild", "moderate", "severe"]


THRESHOLDS = {
    # PT-L01
    # Craniovertebral Angle (lower worse)
    "PT-L01": {
        "direction": "lower_worse",
        "none_min": 50,
        "mild_min": 45,
        "moderate_min": 40,
    },
    # PT-A02
    # Shoulder asymmetry mm (higher worse)
    "PT-A02": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 20,
    },
}


def classify(param_id: str, value: float) -> Severity:

    rule = THRESHOLDS[param_id]

    direction = rule["direction"]

    # LOWER WORSE
    if direction == "lower_worse":

        if value >= rule["none_min"]:
            return "none"

        if value >= rule["mild_min"]:
            return "mild"

        if value >= rule["moderate_min"]:
            return "moderate"

        return "severe"

    # HIGHER WORSE
    if direction == "higher_worse":

        if value <= rule["none_max"]:
            return "none"

        if value <= rule["mild_max"]:
            return "mild"

        if value <= rule["moderate_max"]:
            return "moderate"

        return "severe"

    raise ValueError(f"Unknown direction: {direction}")
