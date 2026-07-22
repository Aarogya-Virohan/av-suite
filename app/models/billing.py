from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base
from app.common.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.enums.billing import InvoiceStatus, PaymentMethod
from app.enums.package import PackageStatus
from app.models.appointment import Appointment
from app.models.clinic import Clinic
from app.models.patient import Patient


def _invoice_status_values(enum_cls: type[InvoiceStatus]) -> list[str]:
    """Return database enum values for invoice status."""

    return [member.value for member in enum_cls]


def _payment_method_values(enum_cls: type[PaymentMethod]) -> list[str]:
    """Return database enum values for payment method."""

    return [member.value for member in enum_cls]


def _package_status_values(enum_cls: type[PackageStatus]) -> list[str]:
    """Return database enum values for package status."""

    return [member.value for member in enum_cls]


class Package(UUIDMixin, TimestampMixin, Base):
    """Clinic package catalogue entity."""

    __tablename__: str = "packages"
    __table_args__: tuple[Index, ...] = (
        Index("ix_packages_clinic_id", "clinic_id"),
        Index("ix_packages_status", "status"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[PackageStatus] = mapped_column(
        Enum(
            PackageStatus,
            name="package_status",
            values_callable=_package_status_values,
        ),
        nullable=False,
        default=PackageStatus.ACTIVE,
    )

    patient_packages: Mapped[list[PatientPackage]] = relationship("PatientPackage", back_populates="package")


class PatientPackage(UUIDMixin, TimestampMixin, Base):
    """Multi-session treatment package purchased by a patient."""

    __tablename__: str = "patient_packages"
    __table_args__: tuple[Index, ...] = (
        Index("ix_patient_packages_clinic_id", "clinic_id"),
        Index("ix_patient_packages_patient_id", "patient_id"),
        Index("ix_patient_packages_package_id", "package_id"),
        Index("ix_patient_packages_status", "status"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    patient: Mapped[Patient] = relationship()

    package_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id"),
        nullable=True,
    )
    package: Mapped[Package | None] = relationship("Package", back_populates="patient_packages")

    package_name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)

    status: Mapped[PackageStatus] = mapped_column(
        Enum(
            PackageStatus,
            name="package_status",
            values_callable=_package_status_values,
        ),
        nullable=False,
        default=PackageStatus.ACTIVE,
    )

    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def sessions_remaining(self) -> int:
        """Calculate remaining unused sessions."""

        return max(0, self.total_sessions - self.completed_sessions)


class Invoice(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Clinic-scoped billing invoice."""

    __tablename__: str = "invoices"
    __table_args__: tuple[Index, ...] = (
        Index("ix_invoices_clinic_id", "clinic_id"),
        Index("ix_invoices_patient_id", "patient_id"),
        Index("ix_invoices_appointment_id", "appointment_id"),
        Index("ix_invoices_invoice_number", "invoice_number"),
        Index("ix_invoices_status", "status"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    patient: Mapped[Patient] = relationship()

    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id"),
        nullable=True,
    )
    appointment: Mapped[Appointment | None] = relationship()

    invoice_number: Mapped[str] = mapped_column(String(length=64), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False, default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False, default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False, default=Decimal("0.00")
    )

    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(
            InvoiceStatus,
            name="invoice_status",
            values_callable=_invoice_status_values,
        ),
        nullable=False,
        default=InvoiceStatus.ISSUED,
    )

    line_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[InvoiceItem]] = relationship(
        "InvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="invoice")


class InvoiceItem(UUIDMixin, TimestampMixin, Base):
    """Individual line item within an invoice."""

    __tablename__: str = "invoice_items"
    __table_args__: tuple[Index, ...] = (
        Index("ix_invoice_items_clinic_id", "clinic_id"),
        Index("ix_invoice_items_invoice_id", "invoice_id"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    invoice_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=False,
    )
    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="items")

    description: Mapped[str] = mapped_column(String(length=255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)


class Payment(UUIDMixin, TimestampMixin, Base):
    """Payment transaction recorded against an invoice."""

    __tablename__: str = "payments"
    __table_args__: tuple[Index, ...] = (
        Index("ix_payments_clinic_id", "clinic_id"),
        Index("ix_payments_invoice_id", "invoice_id"),
        Index("ix_payments_patient_id", "patient_id"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    invoice_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=False,
    )
    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payments")

    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    patient: Mapped[Patient] = relationship()

    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(
            PaymentMethod,
            name="payment_method",
            values_callable=_payment_method_values,
        ),
        nullable=False,
    )
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transaction_reference: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
