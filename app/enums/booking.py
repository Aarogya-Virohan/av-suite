from __future__ import annotations

from enum import StrEnum


class AppointmentRequestStatus(StrEnum):
    """Status options for public appointment requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
