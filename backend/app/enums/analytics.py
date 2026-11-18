from __future__ import annotations

from enum import StrEnum


class AnalyticsPeriod(StrEnum):
    """Supported calendar periods for analytics reports."""

    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"


class PatientRevenueSort(StrEnum):
    """Financial measure used to order patient revenue analytics."""

    COLLECTED_AMOUNT = "collected_amount"
    BILLED_AMOUNT = "billed_amount"
