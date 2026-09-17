from app.services.posture.scoring import calculate_global_index


def test_nothing_graded_is_not_reported_as_optimal() -> None:
    """
    The defect this guards against: an assessment in which every parameter
    failed on landmark visibility printed 100 percent and "Optimal
    Alignment" on a patient-facing report.
    """

    result = calculate_global_index([])

    assert result["score"] is None
    assert result["descriptor"] == "Not assessable"
    assert result["graded"] == 0


def test_ungraded_severities_do_not_count_as_zero() -> None:
    """
    "insufficient_data" is the absence of a grade, not a grade of zero.
    Counting it would credit a parameter that was never measured and would
    pull the score upward exactly when the data is worst.
    """

    result = calculate_global_index(
        ["insufficient_data", "not_available", "unknown_string"]
    )

    assert result["score"] is None
    assert result["graded"] == 0


def test_ungraded_severities_are_excluded_from_the_denominator() -> None:

    graded_only = calculate_global_index(["severe", "none"])
    with_noise = calculate_global_index(
        ["severe", "none", "insufficient_data", "not_available"]
    )

    assert graded_only["score"] == with_noise["score"]
    assert with_noise["graded"] == 2


def test_score_is_unchanged_for_a_fully_graded_assessment() -> None:
    """The weighting is deliberately untouched by this change."""

    assert calculate_global_index(["none"] * 18)["score"] == 100
    assert calculate_global_index(["severe"] * 18)["score"] == 0
    assert calculate_global_index(["severe"] * 3 + ["none"] * 15)["score"] == 83


def test_descriptor_bands() -> None:

    assert calculate_global_index(["none"] * 18)["descriptor"] == "Optimal Alignment"
    assert (
        calculate_global_index(["severe"] * 3 + ["none"] * 15)["descriptor"]
        == "Minor Compensation"
    )
    assert (
        calculate_global_index(["severe"] * 8 + ["none"] * 10)["descriptor"]
        == "Compensatory Pattern"
    )
    assert (
        calculate_global_index(["severe"] * 18)["descriptor"]
        == "Significant Dysfunction"
    )


def test_attempted_is_carried_through_and_defaults_to_graded() -> None:
    """
    Identical findings on a different number of computed parameters give
    the same score today. The counts are recorded so a consumer can see
    that, rather than having to infer it.
    """

    partial = calculate_global_index(["severe"] * 3, attempted=18)
    full = calculate_global_index(["severe"] * 3 + ["none"] * 15, attempted=18)

    assert partial["score"] == 0
    assert full["score"] == 83
    assert partial["attempted"] == full["attempted"] == 18
    assert partial["graded"] == 3
    assert full["graded"] == 18

    assert calculate_global_index(["none"] * 4)["attempted"] == 4
