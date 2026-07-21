from __future__ import annotations

from enum import StrEnum


class ClinicPlanTier(StrEnum):
    """Subscription tiers available to a clinic."""

    FREE = "free"
    PRACTICE = "practice"
    CLINICAL_PRO = "clinical_pro"
