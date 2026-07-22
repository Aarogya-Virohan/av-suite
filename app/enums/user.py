from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType


class UserRole(StrEnum):
    """Application roles available to CRM users."""

    ADMIN = "admin"
    THERAPIST = "therapist"
    FRONT_DESK = "front_desk"


LEGACY_USER_ROLE_ALIASES = MappingProxyType(
    {
        "physio": UserRole.THERAPIST,
    }
)


def normalize_user_role(value: UserRole | str) -> UserRole:
    """Return the canonical CRM user role for SRS and AV Suite role values."""

    if isinstance(value, UserRole):
        return value

    normalized_value = value.strip().lower()
    try:
        return UserRole(normalized_value)
    except ValueError:
        legacy_role = LEGACY_USER_ROLE_ALIASES.get(normalized_value)
        if legacy_role is not None:
            return legacy_role

    raise ValueError(f"Unsupported user role: {value}")
