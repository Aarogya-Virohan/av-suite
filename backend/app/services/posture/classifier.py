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
        "centred",
    ]


# SOURCE STATUS, read this before changing any number below.
#
# Each rule carries a source line. "No published source" means exactly
# that: the number is inherited from an earlier build and nobody has been
# able to point at a reference range for it. Do not attach a citation to
# one of those rows unless the citation actually publishes that band.
THRESHOLDS: dict[str, dict] = {
    # Bands from the published craniovertebral angle literature, but the
    # tool measures ear to shoulder rather than tragus to C7 because
    # MediaPipe returns no C7 landmark, so the reference range does not
    # transfer directly. Open with the founders.
    "PT-L01": {
        "direction": "lower_worse",
        "none_min": 50,
        "mild_min": 45,
        "moderate_min": 40,
    },
    # No published source.
    "PT-A02": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 20,
    },
    # No published source. Asymmetric with PT-A05 and has no female band.
    "PT-A06": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 7,
        "moderate_max": 12,
    },
    # PT-A03 and PT-P01 are the same calculation on two views. They used
    # to carry different bands (10/20/30 here, 5/15/25 on the back view),
    # so one patient could get two contradictory grades for one number on
    # one report. Harmonised onto the tighter set on 18 Sept. Neither set
    # had a published source; the tighter one was kept because it is the
    # more conservative of two unsourced options.
    "PT-A03": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 15,
        "moderate_max": 25,
    },
    # No published source.
    "PT-A04": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 5,
        "moderate_max": 10,
    },
    # No published source.
    "PT-A10": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 6,
        "moderate_max": 10,
    },
    # No published source. The value is signed since 18 Sept, positive
    # forward and negative backward, so the bands are mirrored rather
    # than one sided; a backward lean would otherwise grade NONE at any
    # size. The tier boundaries themselves are unchanged.
    "PT-L05": {
        "direction": "centred",
        "none_low": -3,
        "none_high": 3,
        "mild_low": -6,
        "mild_high": 6,
        "moderate_low": -10,
        "moderate_high": 10,
    },
    # No published source for the tier boundaries themselves. The normal
    # ceiling was 2 degrees against a reported 2D frontal angle error of
    # roughly 1.5 to 2 degrees for this method, so a perfectly level head
    # could grade MILD on measurement noise alone. Moved to 3 degrees on
    # 18 Sept, above the method's own error band rather than inside it.
    # mild_max moved from 5 to 7 to keep the mild band a similar width;
    # moderate_max is unchanged. This is still not a clinical reference
    # range, it is a noise-floor correction, and should be revisited once
    # real photo data exists.
    "PT-A01": {
        "direction": "higher_worse",
        "none_max": 3,
        "mild_max": 7,
        "moderate_max": 10,
    },
    # No published source. 2D validity unverified, direction logic not yet
    # checked against real photographs.
    "PT-A05": {
        "direction": "higher_worse",
        "none_max": 5,
        "none_max_female": 7,
        "mild_max": 9,
        "moderate_max": 13,
    },
    # Same measurement as PT-A03, same bands since 18 Sept. See PT-A03.
    "PT-P01": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 15,
        "moderate_max": 25,
    },
    # No published source. Identical calculation to PT-A02.
    "PT-P02": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 10,
        "moderate_max": 20,
    },
    # Rearfoot / calcaneal alignment, signed: positive is valgus
    # (eversion), negative is varus (inversion).
    #
    # This parameter is graded as deviation from the healthy population
    # mean, not as deviation from zero. In 88 healthy adults the mean
    # relaxed calcaneal stance position was 6.07 degrees of valgus with a
    # standard deviation of 2.71, and 95 percent of adults fell between 3
    # and 9 degrees of valgus. The same study found the long assumed
    # normal of 0 plus or minus 2 degrees held for under 2 percent of
    # adults.
    #
    # The previous 0 to 5 normal band therefore graded the population mean
    # as MILD and a perfectly ordinary foot as abnormal. Bands below are
    # the study's own 95 percent range for normal, then one standard
    # deviation per tier in both directions. Every number here comes from
    # that one study; none of them is an estimate.
    "PT-P03": {
        "direction": "centred",
        "none_low": 3.0,
        "none_high": 9.0,
        "mild_low": 0.6,
        "mild_high": 11.8,
        "moderate_low": -2.1,
        "moderate_high": 14.5,
    },
    # No published source. The definition itself is unsettled: the code
    # computes shoulder line angle minus hip line angle, which reduces to
    # pelvic obliquity when the shoulders are level, and pelvic obliquity
    # is already reported as PT-A04.
    "PT-P04": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 8,
        "moderate_max": 12,
    },
    # No published source. Normative data exists for the foot progression
    # angle itself but not for the difference between one person's two
    # feet, which is what this grades.
    "PT-P05": {
        "direction": "higher_worse",
        "none_max": 5,
        "mild_max": 8,
        "moderate_max": 12,
    },
    # Grades the hyperextension side only. Any non negative value grades
    # NONE, so a flexion contracture of any size reads as normal. Flexion
    # bands are outstanding.
    "PT-L06": {
        "direction": "lower_worse",
        "none_min": -5,
        "mild_min": -10,
        "moderate_min": -15,
    },
    # A separate hardcoded rule outside this table grades any negative
    # carrying angle as SEVERE with a discontinuity at -1.5 degrees. That
    # rule is not reachable from here, and the parameter's validity from a
    # standing photograph is with the founders.
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

# Per-parameter overrides where a published minimum detectable change is
# wider than the flat default above. A validated smartphone application
# for measuring the craniovertebral angle reported an MDC of 4.96 degrees
# within a rater and 5.52 between raters. PT-L01's own bands are 5 degrees
# wide, narrower than that MDC, so the flat 2.0 degree margin understates
# how much a repeat measurement can move. Set to the between-rater figure,
# the more conservative of the two.
#
# No other parameter here has a reported MDC, so no other override exists.
# Do not add one without a citation.
BORDERLINE_MARGIN_OVERRIDES_DEGREES: dict[str, float] = {
    "PT-L01": 5.52,
}

# Some severity rules contain a boundary that is not a key in THRESHOLDS,
# because the rule is partly hardcoded outside this table (see PT-A08's
# handling in posture.py). Those boundaries are invisible to the
# THRESHOLDS-only scan below, so they are listed here explicitly. This is
# not a substitute for moving the rule into THRESHOLDS, it only makes sure
# the value nearest that hardcoded cliff still gets flagged as provisional.
_EXTRA_BOUNDARIES: dict[str, list[float]] = {
    # posture.py grades any carrying angle at or below -1.5 degrees as
    # SEVERE outright, and anything with |value| < 1.5 as NONE. -1.5 is
    # therefore a hard decision point this table has no key for.
    "PT-A08": [-1.5, 1.5],
}

# Any rule key ending in one of these is a severity boundary. Collected by
# suffix rather than by a fixed list so a new rule shape cannot silently
# add a boundary the borderline check never looks at.
_BOUNDARY_SUFFIXES = ("_min", "_max", "_low", "_high")


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

    if unit == "mm":
        margin = BORDERLINE_MARGIN_MM
    else:
        margin = BORDERLINE_MARGIN_OVERRIDES_DEGREES.get(
            param_id, BORDERLINE_MARGIN_DEGREES
        )

    rule = THRESHOLDS[param_id]

    boundaries = [
        v
        for key, v in rule.items()
        if key.endswith(_BOUNDARY_SUFFIXES) and isinstance(v, (int, float))
    ]

    boundaries.extend(_EXTRA_BOUNDARIES.get(param_id, []))

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
        normal ranges (currently PT-A05 Knee Valgus and PT-A08 Elbow
        Carrying Angle, which has separate female bands in THRESHOLDS).

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

    if direction == "centred":
        # Normal is a band around a population mean, not a ceiling above
        # zero, and the value is signed. Deviation in either direction is
        # graded on the same tiers.

        if rule["none_low"] <= value <= rule["none_high"]:
            return "none"

        if rule["mild_low"] <= value <= rule["mild_high"]:
            return "mild"

        if rule["moderate_low"] <= value <= rule["moderate_high"]:
            return "moderate"

        return "severe"

    raise ValueError(f"Unknown direction: {direction}")
