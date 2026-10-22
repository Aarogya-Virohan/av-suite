"""Data types for the screening engine.

Instrument definitions are immutable, versioned data. Scoring reads them and
never touches the database or the network, so results are reproducible from
(instrument_id, instrument_version, raw responses) alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ResponseOption:
    value: int
    label: str


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    number: int
    text: str
    scored: bool = True
    # When set, this item uses its own options instead of the instrument's.
    options: tuple[ResponseOption, ...] | None = None


@dataclass(frozen=True, slots=True)
class Band:
    """Inclusive score range. ``max_score`` None means open-ended (e.g. 28+)."""

    min_score: int
    max_score: int | None
    label: str
    level: int  # ordinal, 0 = lowest severity

    def contains(self, score: int) -> bool:
        return score >= self.min_score and (
            self.max_score is None or score <= self.max_score
        )


@dataclass(frozen=True, slots=True)
class Scale:
    """A scored total (PHQ-9 total) or subscale (DASS-21 Depression)."""

    id: str
    label: str
    item_ids: tuple[str, ...]
    bands: tuple[Band, ...]
    referral_min_level: int
    multiplier: int = 1
    max_score: int = 0


@dataclass(frozen=True, slots=True)
class RiskItemRule:
    """Any response >= ``min_value`` on ``item_id`` raises the risk-item flag."""

    item_id: str
    min_value: int
    reason: str


@dataclass(frozen=True, slots=True)
class Instrument:
    id: str
    version: str
    name: str
    short_name: str
    instructions: str
    options: tuple[ResponseOption, ...]
    items: tuple[Item, ...]
    scales: tuple[Scale, ...]
    risk_item_rules: tuple[RiskItemRule, ...] = ()
    citation: str = ""
    licence_note: str = ""

    @property
    def scored_items(self) -> tuple[Item, ...]:
        return tuple(item for item in self.items if item.scored)

    def item(self, item_id: str) -> Item:
        for item in self.items:
            if item.id == item_id:
                return item
        raise KeyError(item_id)

    def options_for(self, item: Item) -> tuple[ResponseOption, ...]:
        return item.options if item.options is not None else self.options


@dataclass(frozen=True, slots=True)
class ScaleResult:
    scale_id: str
    label: str
    raw_sum: int
    score: int
    max_score: int
    band_label: str
    band_level: int
    referral: bool


@dataclass(frozen=True, slots=True)
class ScoreResult:
    instrument_id: str
    instrument_version: str
    scales: tuple[ScaleResult, ...]
    referral_flag: bool
    risk_item_flag: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def scale(self, scale_id: str) -> ScaleResult:
        for result in self.scales:
            if result.scale_id == scale_id:
                return result
        raise KeyError(scale_id)
