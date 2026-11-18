"""Score trends across sessions (SRS 4.1.2 longitudinal view, SRS 3.5).

Pure: takes completed sessions (anything with ``id``, ``instrument_id``,
``instrument_version``, ``completed_at`` and the stored ``result``) and
returns one series per scored scale, oldest point first. The API and the
PDF summary both use it, so the chart and the report never disagree.

Points use the score stored at submit time. Band shading comes from the
instrument definition of the newest point, so a future definition change
shows the current published bands while old points keep their own labels.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
import uuid

from app.screening.registry import get_instrument

# Display order on screen and in the report.
INSTRUMENT_ORDER = ("phq9", "gad7", "dass21")


class SessionLike(Protocol):
    id: uuid.UUID
    instrument_id: str
    instrument_version: str
    completed_at: datetime | None
    result: dict[str, Any] | None


@dataclass(frozen=True)
class TrendBand:
    min_score: int
    max_score: int
    label: str
    level: int


@dataclass(frozen=True)
class TrendPoint:
    session_id: uuid.UUID
    completed_at: datetime
    score: int
    band_label: str
    band_level: int
    referral: bool


@dataclass
class TrendSeries:
    instrument_id: str
    short_name: str
    scale_id: str
    label: str
    max_score: int
    # Lowest score that suggests referral on this scale.
    referral_from: int | None
    bands: tuple[TrendBand, ...]
    points: list[TrendPoint] = field(default_factory=list)


def build_series(sessions: Iterable[SessionLike]) -> list[TrendSeries]:
    """One series per (instrument, scale) with at least one completed point."""
    completed = sorted(
        (s for s in sessions if s.completed_at is not None and s.result),
        key=lambda s: s.completed_at,
    )
    newest_version: dict[str, str] = {}
    for session in completed:
        newest_version[session.instrument_id] = session.instrument_version

    series: dict[tuple[str, str], TrendSeries] = {}
    for instrument_id, version in newest_version.items():
        instrument = get_instrument(instrument_id, version)
        for scale in instrument.scales:
            bands = tuple(
                TrendBand(
                    min_score=b.min_score,
                    max_score=b.max_score if b.max_score is not None else scale.max_score,
                    label=b.label,
                    level=b.level,
                )
                for b in sorted(scale.bands, key=lambda b: b.min_score)
            )
            referral_from = next(
                (b.min_score for b in bands if b.level >= scale.referral_min_level), None
            )
            series[(instrument_id, scale.id)] = TrendSeries(
                instrument_id=instrument_id,
                short_name=instrument.short_name,
                scale_id=scale.id,
                label=scale.label,
                max_score=scale.max_score,
                referral_from=referral_from,
                bands=bands,
            )

    for session in completed:
        for scale in session.result.get("scales", []):
            target = series.get((session.instrument_id, scale["scale_id"]))
            if target is None:
                continue
            target.points.append(
                TrendPoint(
                    session_id=session.id,
                    completed_at=session.completed_at,
                    score=scale["score"],
                    band_label=scale["band_label"],
                    band_level=scale["band_level"],
                    referral=scale["referral"],
                )
            )

    def order(key: tuple[str, str]) -> tuple[int, int]:
        instrument_id, scale_id = key
        rank = INSTRUMENT_ORDER.index(instrument_id) if instrument_id in INSTRUMENT_ORDER else 99
        scale_ids = [s.id for s in get_instrument(instrument_id, newest_version[instrument_id]).scales]
        return rank, scale_ids.index(scale_id)

    return [series[key] for key in sorted(series, key=order) if series[key].points]
