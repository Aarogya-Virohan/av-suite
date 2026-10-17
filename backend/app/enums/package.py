from __future__ import annotations

from enum import StrEnum


class PackageStatus(StrEnum):
    """Lifecycle states for package catalog and patient package records."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

