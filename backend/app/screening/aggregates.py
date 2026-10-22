"""Anonymised clinic statistics with small-cell suppression (SRS 4.3.3, S-D-028).

Pure: takes completed-session rows and returns counts that are safe to show
an administrator. No IO, so the suppression rules are pinned by unit tests.

Rules, applied per distribution (one scale of one screener):
1. Fewer than MIN_CELL completed sessions: no distribution and no referral
   figure at all, only the total.
2. Primary: any band count from 1 to MIN_CELL - 1 is hidden. Zero is shown.
3. Secondary: if exactly one band is hidden, the smallest other non-zero band
   is hidden too, so the hidden one cannot be worked out from the total.
4. Referral: hidden when the flagged count or the not-flagged count is from 1
   to MIN_CELL - 1 (a rate of 2 of 50, or 48 of 50, points at 2 people).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.screening.types import Instrument

MIN_CELL = 5


@dataclass(frozen=True, slots=True)
class SessionRow:
    """What the aggregator needs from a completed session. Nothing identifying."""

    instrument_id: str
    referral_flag: bool
    result: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class BandCount:
    label: str
    count: int | None  # None = hidden
    suppressed: bool


@dataclass(frozen=True, slots=True)
class ScaleDistribution:
    scale_id: str
    label: str
    bands: tuple[BandCount, ...]


@dataclass(frozen=True, slots=True)
class ReferralFigure:
    count: int | None
    rate_percent: float | None
    suppressed: bool


@dataclass(frozen=True, slots=True)
class InstrumentAggregate:
    instrument_id: str
    short_name: str
    completed: int
    too_few: bool  # rule 1: fewer than MIN_CELL completed
    referral: ReferralFigure
    scales: tuple[ScaleDistribution, ...]


def _small(n: int, min_cell: int) -> bool:
    return 0 < n < min_cell


def suppress(counts: list[int], min_cell: int = MIN_CELL) -> list[int | None]:
    """Rules 2 and 3 on one distribution. Returns None where a count is hidden."""
    hidden = {i for i, n in enumerate(counts) if _small(n, min_cell)}
    if len(hidden) == 1:
        others = [(n, i) for i, n in enumerate(counts) if i not in hidden and n > 0]
        if others:
            hidden.add(min(others)[1])
    return [None if i in hidden else n for i, n in enumerate(counts)]


def referral_figure(flagged: int, total: int, min_cell: int = MIN_CELL) -> ReferralFigure:
    if total < min_cell or _small(flagged, min_cell) or _small(total - flagged, min_cell):
        return ReferralFigure(count=None, rate_percent=None, suppressed=True)
    return ReferralFigure(count=flagged, rate_percent=round(100 * flagged / total, 1), suppressed=False)


def aggregate(
    rows: Iterable[SessionRow], instruments: Iterable[Instrument], min_cell: int = MIN_CELL
) -> list[InstrumentAggregate]:
    by_instrument: dict[str, list[SessionRow]] = {}
    for row in rows:
        by_instrument.setdefault(row.instrument_id, []).append(row)

    out: list[InstrumentAggregate] = []
    for inst in instruments:
        sessions = by_instrument.get(inst.id, [])
        total = len(sessions)
        too_few = total < min_cell
        scales = []
        for scale in inst.scales:
            # Labels in the published order, lowest band first. Results store
            # the label they were scored with (by version), counted by label.
            labels = [b.label for b in sorted(scale.bands, key=lambda b: b.min_score)]
            counts = dict.fromkeys(labels, 0)
            for s in sessions:
                for scored in (s.result or {}).get("scales", []):
                    if scored.get("scale_id") == scale.id and scored.get("band_label") in counts:
                        counts[scored["band_label"]] += 1
            raw = [counts[label] for label in labels]
            shown = [None] * len(raw) if too_few else suppress(raw, min_cell)
            scales.append(
                ScaleDistribution(
                    scale_id=scale.id,
                    label=scale.label,
                    bands=tuple(
                        BandCount(label=label, count=value, suppressed=value is None)
                        for label, value in zip(labels, shown)
                    ),
                )
            )
        flagged = sum(1 for s in sessions if s.referral_flag)
        out.append(
            InstrumentAggregate(
                instrument_id=inst.id,
                short_name=inst.short_name,
                completed=total,
                too_few=too_few,
                referral=referral_figure(flagged, total, min_cell),
                scales=tuple(scales),
            )
        )
    return out
