from __future__ import annotations

from enum import StrEnum


class InvoiceStatus(StrEnum):
    """Lifecycle states for billing invoices."""

    UNPAID = "unpaid"
    PAID = "paid"
    PARTIAL = "partial"
    DRAFT = "draft"
    ISSUED = "issued"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class PaymentMethod(StrEnum):
    """Payment channels supported for billing settlement."""

    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    INSURANCE = "insurance"
    OTHER = "other"



class PackageStatus(StrEnum):
    """Status of patient treatment packages."""

    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
