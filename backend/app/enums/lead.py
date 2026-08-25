from __future__ import annotations

from enum import StrEnum


class LeadStage(StrEnum):
    """Lifecycle stages for CRM sales leads."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


class LeadSource(StrEnum):
    """Sources where a lead originated."""

    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    WALK_IN = "walk_in"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"
