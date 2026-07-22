from __future__ import annotations

from enum import StrEnum


class InvoiceStatus(StrEnum):
    """Payment states for invoices."""

    UNPAID = "unpaid"
    PAID = "paid"
    PARTIAL = "partial"


class PaymentMethod(StrEnum):
    """Supported payment collection methods."""

    CASH = "cash"
    UPI = "upi"
    CARD = "card"


class PaymentStatus(StrEnum):
    """Processing states for payment records."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
