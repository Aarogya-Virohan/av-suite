from __future__ import annotations

from enum import StrEnum


class CapabilityScope(StrEnum):
    """Allowed Rev3 capability scopes."""

    NONE = "none"
    OWN = "own"
    ALL = "all"
