"""Clinic statistics for administrators (SRS 4.3.3, S-D-028).

Reads only completed sessions of one clinic in a date range and hands them to
the pure aggregator, which applies small-cell suppression. Nothing here
returns a patient id, a name or a single result. The CSV carries exactly what
the screen shows, hidden cells included.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.psychosocial import PsychosocialSession
from app.screening.aggregates import InstrumentAggregate, SessionRow, aggregate
from app.screening.registry import get_instrument, list_instruments

# Clinics are in India; a date range means Indian calendar days.
CLINIC_TZ = ZoneInfo("Asia/Kolkata")
DEFAULT_RANGE_DAYS = 90


def today_ist() -> date:
    return datetime.now(CLINIC_TZ).date()


def ist_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    """[start of date_from, start of the day after date_to) in IST."""
    start = datetime.combine(date_from, time.min, tzinfo=CLINIC_TZ)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=CLINIC_TZ)
    return start, end


async def clinic_aggregates(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    date_from: date,
    date_to: date,
    instrument_id: str | None,
) -> list[InstrumentAggregate]:
    start, end = ist_bounds(date_from, date_to)
    query = select(
        PsychosocialSession.instrument_id,
        PsychosocialSession.referral_flag,
        PsychosocialSession.result,
    ).where(
        PsychosocialSession.clinic_id == clinic_id,
        PsychosocialSession.status == "completed",
        PsychosocialSession.completed_at >= start,
        PsychosocialSession.completed_at < end,
    )
    if instrument_id is not None:
        query = query.where(PsychosocialSession.instrument_id == instrument_id)
    rows = [
        SessionRow(instrument_id=r.instrument_id, referral_flag=r.referral_flag, result=r.result)
        for r in (await db.execute(query)).all()
    ]
    instruments = [get_instrument(instrument_id)] if instrument_id else list(list_instruments())
    return aggregate(rows, instruments)


HIDDEN = "hidden"


def to_csv(aggregates: list[InstrumentAggregate], date_from: date, date_to: date) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(["From", "To", "Screener", "Scale", "Measure", "Value"])
    period = [date_from.isoformat(), date_to.isoformat()]

    def value(n: int | float | None) -> str:
        return HIDDEN if n is None else str(n)

    for agg in aggregates:
        writer.writerow([*period, agg.short_name, "", "Completed sessions", agg.completed])
        writer.writerow([*period, agg.short_name, "", "Referral recommended", value(agg.referral.count)])
        writer.writerow([*period, agg.short_name, "", "Referral recommended (%)", value(agg.referral.rate_percent)])
        for scale in agg.scales:
            for band in scale.bands:
                writer.writerow([*period, agg.short_name, scale.label, f"Band: {band.label}", value(band.count)])
    return buf.getvalue()


def csv_filename(date_from: date, date_to: date) -> str:
    return f"screening-statistics-{date_from.isoformat()}-to-{date_to.isoformat()}.csv"
