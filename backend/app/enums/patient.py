from __future__ import annotations

from enum import StrEnum


class PatientStatus(StrEnum):
    """Lifecycle states for a clinic patient."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCHARGED = "discharged"
