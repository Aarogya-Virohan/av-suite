from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.enums.analytics import AnalyticsPeriod


@dataclass(frozen=True)
class DateRange:
    """A half-open UTC date/time range: ``start <= value < end``."""

    start: datetime
    end: datetime


@dataclass(frozen=True)
class AnalyticsPeriods:
    """Calendar periods used by analytics, all expressed in UTC."""

    today: DateRange
    this_week: DateRange
    this_month: DateRange
    this_year: DateRange

    def for_period(self, period: AnalyticsPeriod) -> DateRange:
        """Return the shared UTC date range selected by the API period value."""

        return {
            AnalyticsPeriod.TODAY: self.today,
            AnalyticsPeriod.WEEK: self.this_week,
            AnalyticsPeriod.MONTH: self.this_month,
            AnalyticsPeriod.YEAR: self.this_year,
        }[period]

    @classmethod
    def containing(cls, now: datetime) -> AnalyticsPeriods:
        """Build calendar periods containing ``now`` (naive values are treated as UTC)."""

        utc_now = (
            now.replace(tzinfo=timezone.utc)
            if now.tzinfo is None
            else now.astimezone(timezone.utc)
        )
        today_start = datetime(
            utc_now.year, utc_now.month, utc_now.day, tzinfo=timezone.utc
        )
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = datetime(utc_now.year, utc_now.month, 1, tzinfo=timezone.utc)
        next_month_start = (
            datetime(utc_now.year + 1, 1, 1, tzinfo=timezone.utc)
            if utc_now.month == 12
            else datetime(utc_now.year, utc_now.month + 1, 1, tzinfo=timezone.utc)
        )

        return cls(
            today=DateRange(today_start, today_start + timedelta(days=1)),
            this_week=DateRange(week_start, week_start + timedelta(days=7)),
            this_month=DateRange(month_start, next_month_start),
            this_year=DateRange(
                datetime(utc_now.year, 1, 1, tzinfo=timezone.utc),
                datetime(utc_now.year + 1, 1, 1, tzinfo=timezone.utc),
            ),
        )
