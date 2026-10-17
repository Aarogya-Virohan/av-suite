from __future__ import annotations

from enum import StrEnum


class AppointmentStatus(StrEnum):
    """Scheduling states for appointments."""

    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentSource(StrEnum):
    """Sources from which appointments are created."""

    MANUAL = "manual"
    PUBLIC_BOOKING = "public_booking"


class AppointmentRequestStatus(StrEnum):
    """Approval states for public booking requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
