from __future__ import annotations

from enum import StrEnum


class ClinicType(StrEnum):
    """Workspace type used by the platform membership foundation."""

    CLINIC = "clinic"
    SOLO = "solo"
    PERSONAL = "personal"


class ClinicPlanTier(StrEnum):
    """Subscription tiers available to a clinic."""

    FREE = "free"
    PRACTICE = "practice"
    CLINICAL_PRO = "clinical_pro"
