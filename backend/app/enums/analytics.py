from __future__ import annotations

from enum import StrEnum


class AnalyticsPeriod(StrEnum):
    """Supported UTC calendar periods for analytics reports."""

    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
