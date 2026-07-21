from __future__ import annotations

from enum import StrEnum


class ClinicStatus(StrEnum):
    """Status values for a clinic."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
