from typing import Iterable

SEVERITY_POINTS = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}

# Only these four contribute to the index. Anything else that reaches this
# function -- "insufficient_data", "not_available", or a string this module
# has not seen -- is not a grade of zero. It is the absence of a grade, and
# scoring it as zero would credit a parameter that was never measured.
GRADED_SEVERITIES = frozenset(SEVERITY_POINTS)


def calculate_global_index(
    severities: Iterable[str],
    attempted: int | None = None,
) -> dict:
    """
    Composite index over the parameters that actually produced a grade.

    Returns a score of None when nothing was graded. The previous behaviour
    was to return 100 with the descriptor "Optimal Alignment", so an
    assessment in which every parameter failed on landmark visibility
    printed a perfect result on a patient-facing report. Of the two ways
    this function can be wrong, that is the one that cannot be allowed:
    it fails in the reassuring direction.

    graded and attempted are carried in the returned payload so a consumer
    can see how much of the assessment the score rests on. Neither the PDF
    nor the frontend renders them yet. How an incomplete index should be
    presented to a clinician is an open question and is not decided here.

    The weighting is deliberately unchanged. Every parameter still carries
    equal weight, and that remains unsourced.
    """

    severities = [s for s in severities if s in GRADED_SEVERITIES]

    graded = len(severities)

    if attempted is None:
        attempted = graded

    if graded == 0:
        return {
            "score": None,
            "descriptor": "Not assessable",
            "graded": 0,
            "attempted": attempted,
        }

    total = sum(SEVERITY_POINTS[severity] for severity in severities)

    max_possible = graded * 3

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
        "graded": graded,
        "attempted": attempted,
    }
