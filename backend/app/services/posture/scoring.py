from typing import Iterable

SEVERITY_POINTS = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}


def calculate_global_index(severities: Iterable[str]) -> dict:

    severities = list(severities)

    if not severities:
        return {
            "score": 100,
            "descriptor": "Optimal Alignment",
        }

    total = sum(
        SEVERITY_POINTS.get(
            severity,
            0,
        )
        for severity in severities
    )

    max_possible = len(severities) * 3

    penalty = (total / max_possible) * 100

    score = round(100 - penalty)

    if score >= 85:
        descriptor = "Optimal Alignment"

    elif score >= 70:
        descriptor = "Minor Compensation"

    elif score >= 50:
        descriptor = "Compensatory Pattern"

    else:
        descriptor = "Significant Dysfunction"

    return {
        "score": score,
        "descriptor": descriptor,
    }
