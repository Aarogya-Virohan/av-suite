"""Read-only view of the referral rules the engine applies (SRS 4.3.2).

Built from the instrument definitions themselves, so what the clinic admin
sees can never drift from what scoring does. Thresholds are fixed at the
published norms; clinic changes are not supported yet (S-D-027, P-13).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.screening.types import Instrument

# Where each rule comes from. Shown next to the rule so a reviewer can check it.
SOURCES: dict[str, str] = {
    "phq9": "Kroenke, Spitzer and Williams 2001. Referral at Moderate or above (SRS 4.1.3).",
    "gad7": "Spitzer, Kroenke, Williams and Lowe 2006. Referral at Moderate or above (SRS 4.1.3).",
    "dass21": "Lovibond and Lovibond 1995. Referral at Severe or above on any subscale (SRS 4.1.3).",
}


@dataclass(frozen=True, slots=True)
class BandView:
    label: str
    min_score: int
    max_score: int | None
    refers: bool


@dataclass(frozen=True, slots=True)
class ScaleThreshold:
    scale_id: str
    label: str
    max_score: int
    referral_band: str
    referral_min_score: int
    bands: tuple[BandView, ...]


@dataclass(frozen=True, slots=True)
class RiskRuleView:
    item_number: int
    min_value: int
    min_label: str
    description: str


@dataclass(frozen=True, slots=True)
class InstrumentThresholds:
    instrument_id: str
    instrument_version: str
    short_name: str
    source: str
    scales: tuple[ScaleThreshold, ...]
    risk_rules: tuple[RiskRuleView, ...]


def thresholds_for(instrument: Instrument) -> InstrumentThresholds:
    scales = []
    for scale in instrument.scales:
        bands = tuple(sorted(scale.bands, key=lambda b: b.min_score))
        first_referral = next(b for b in bands if b.level >= scale.referral_min_level)
        scales.append(
            ScaleThreshold(
                scale_id=scale.id,
                label=scale.label,
                max_score=scale.max_score,
                referral_band=first_referral.label,
                referral_min_score=first_referral.min_score,
                bands=tuple(
                    BandView(
                        label=b.label,
                        min_score=b.min_score,
                        max_score=b.max_score,
                        refers=b.level >= scale.referral_min_level,
                    )
                    for b in bands
                ),
            )
        )

    risk_rules = []
    for rule in instrument.risk_item_rules:
        item = instrument.item(rule.item_id)
        option = next(o for o in instrument.options_for(item) if o.value == rule.min_value)
        risk_rules.append(
            RiskRuleView(
                item_number=item.number,
                min_value=rule.min_value,
                min_label=option.label,
                description=rule.reason,
            )
        )

    return InstrumentThresholds(
        instrument_id=instrument.id,
        instrument_version=instrument.version,
        short_name=instrument.short_name,
        source=SOURCES.get(instrument.id, ""),
        scales=tuple(scales),
        risk_rules=tuple(risk_rules),
    )
