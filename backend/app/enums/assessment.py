from __future__ import annotations

from enum import StrEnum


class AssessmentStatus(StrEnum):
    """Lifecycle states for clinical assessment and SOAP records."""

    DRAFT = "draft"
    FINALIZED = "finalized"
    ARCHIVED = "archived"
