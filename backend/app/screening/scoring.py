"""Pure, deterministic scoring for screening instruments.

No IO here. Every function takes an Instrument plus raw responses and returns
plain data, which is what the golden-value tests pin down.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.screening.types import Band, Instrument, Scale, ScaleResult, ScoreResult


class ScoringError(ValueError):
    """Responses are incomplete, unknown or out of range."""


def validate_responses(instrument: Instrument, responses: Mapping[str, int]) -> None:
    """Every scored item answered, every answer a valid option, no unknown ids.

    Unscored items (e.g. the PHQ-9 difficulty question) are optional, but if
    present they must still hold a valid option value.
    """
    known = {item.id for item in instrument.items}
    unknown = sorted(set(responses) - known)
    if unknown:
        raise ScoringError(f"Unknown item ids: {', '.join(unknown)}")

    missing = [item.id for item in instrument.scored_items if item.id not in responses]
    if missing:
        raise ScoringError(f"Missing responses for items: {', '.join(missing)}")

    for item_id, value in responses.items():
        item = instrument.item(item_id)
        # bool is an int subclass; reject it explicitly.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ScoringError(f"Response for {item_id} must be an integer")
        allowed = {option.value for option in instrument.options_for(item)}
        if value not in allowed:
            raise ScoringError(f"Response {value} for {item_id} is not a valid option")


def band_for(scale: Scale, score: int) -> Band:
    matches = [band for band in scale.bands if band.contains(score)]
    if len(matches) != 1:
        # Definitions are tested for full, non-overlapping coverage, so this
        # only fires on a broken definition.
        raise ScoringError(
            f"Score {score} on {scale.id} matched {len(matches)} bands"
        )
    return matches[0]


def score_scale(scale: Scale, responses: Mapping[str, int]) -> ScaleResult:
    raw_sum = sum(responses[item_id] for item_id in scale.item_ids)
    score = raw_sum * scale.multiplier
    band = band_for(scale, score)
    return ScaleResult(
        scale_id=scale.id,
        label=scale.label,
        raw_sum=raw_sum,
        score=score,
        max_score=scale.max_score,
        band_label=band.label,
        band_level=band.level,
        referral=band.level >= scale.referral_min_level,
    )


def score(instrument: Instrument, responses: Mapping[str, int]) -> ScoreResult:
    validate_responses(instrument, responses)

    scale_results = tuple(score_scale(scale, responses) for scale in instrument.scales)
    reasons: list[str] = [
        f"{result.label} score {result.score} is in the {result.band_label} band"
        for result in scale_results
        if result.referral
    ]

    risk_item_flag = False
    for rule in instrument.risk_item_rules:
        if responses.get(rule.item_id, 0) >= rule.min_value:
            risk_item_flag = True
            reasons.append(rule.reason)

    referral_flag = risk_item_flag or any(result.referral for result in scale_results)

    return ScoreResult(
        instrument_id=instrument.id,
        instrument_version=instrument.version,
        scales=scale_results,
        referral_flag=referral_flag,
        risk_item_flag=risk_item_flag,
        reasons=tuple(reasons),
    )
