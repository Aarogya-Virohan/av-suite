"""Lookup of instrument definitions by (id, version).

Sessions store both values, so a result scored under an older version can
always be re-explained even after a definition changes. Tool 04 instruments
register here the same way.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from app.screening.instruments.dass21 import DASS21
from app.screening.instruments.gad7 import GAD7
from app.screening.instruments.phq9 import PHQ9
from app.screening.types import Instrument

_ALL: tuple[Instrument, ...] = (PHQ9, GAD7, DASS21)

INSTRUMENTS: Mapping[tuple[str, str], Instrument] = MappingProxyType(
    {(inst.id, inst.version): inst for inst in _ALL}
)

LATEST: Mapping[str, Instrument] = MappingProxyType({inst.id: inst for inst in _ALL})


def get_instrument(instrument_id: str, version: str | None = None) -> Instrument:
    if version is None:
        try:
            return LATEST[instrument_id]
        except KeyError:
            raise KeyError(f"Unknown instrument {instrument_id!r}") from None
    try:
        return INSTRUMENTS[(instrument_id, version)]
    except KeyError:
        raise KeyError(f"Unknown instrument {instrument_id!r} v{version}") from None


def list_instruments() -> tuple[Instrument, ...]:
    return tuple(LATEST.values())
