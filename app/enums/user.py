from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    """Application roles available to CRM users."""

    ADMIN = "admin"
    THERAPIST = "therapist"
    FRONT_DESK = "front_desk"
