from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.enums.analytics import AnalyticsPeriod
from app.core.timezone import CLINIC_TZ


@dataclass(frozen=True)
class DateRange:
    """A half-open India-local date/time range: ``start <= value < end``."""

    start: datetime
    end: datetime


@dataclass(frozen=True)
class AnalyticsPeriods:
    """Calendar periods used by analytics, expressed in India time."""

    today: DateRange
    this_week: DateRange
    this_month: DateRange
    this_year: DateRange

    def for_period(self, period: AnalyticsPeriod) -> DateRange:
        """Return the India calendar range selected by the API period value."""

        return {
            AnalyticsPeriod.TODAY: self.today,
            AnalyticsPeriod.WEEK: self.this_week,
            AnalyticsPeriod.MONTH: self.this_month,
            AnalyticsPeriod.YEAR: self.this_year,
        }[period]

    @classmethod
    def containing(cls, now: datetime) -> AnalyticsPeriods:
        """Build calendar periods containing ``now`` (naive values are India local)."""
        local_now = now.replace(tzinfo=CLINIC_TZ) if now.tzinfo is None else now.astimezone(CLINIC_TZ)
        today_start = datetime.combine(local_now.date(), time.min, tzinfo=CLINIC_TZ)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = datetime(local_now.year, local_now.month, 1, tzinfo=CLINIC_TZ)
        next_month_start = (
            datetime(local_now.year + 1, 1, 1, tzinfo=CLINIC_TZ)
            if local_now.month == 12
            else datetime(local_now.year, local_now.month + 1, 1, tzinfo=CLINIC_TZ)
        )

        return cls(
            today=DateRange(today_start, today_start + timedelta(days=1)),
            this_week=DateRange(week_start, week_start + timedelta(days=7)),
            this_month=DateRange(month_start, next_month_start),
            this_year=DateRange(
                datetime(local_now.year, 1, 1, tzinfo=CLINIC_TZ),
                datetime(local_now.year + 1, 1, 1, tzinfo=CLINIC_TZ),
            ),
        )

    @staticmethod
    def explicit(start: date, end: date) -> DateRange:
        return DateRange(
            datetime.combine(start, time.min, tzinfo=CLINIC_TZ),
            datetime.combine(end + timedelta(days=1), time.min, tzinfo=CLINIC_TZ),
        )
