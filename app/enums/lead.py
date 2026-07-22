from __future__ import annotations

from enum import StrEnum


class LeadStage(StrEnum):
    """Lifecycle stages for CRM sales leads."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"
