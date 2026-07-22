from __future__ import annotations

from enum import StrEnum


class LeadStage(StrEnum):
    """Kanban stages for CRM leads."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"
