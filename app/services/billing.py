from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.enums.billing import InvoiceStatus
from app.enums.package import PackageStatus
from app.models.billing import Invoice, Package, PatientPackage, Payment
from app.repositories.appointment import AppointmentRepository
from app.repositories.billing import (
    InvoiceItemRepository,
    InvoiceRepository,
    PackageRepository,
    PatientPackageRepository,
    PaymentRepository,
)
from app.repositories.patient import PatientRepository
from app.schemas.billing import (
    InvoiceCreate,
    InvoiceUpdate,
    PackageCreate,
    PackageUpdate,
    PatientPackageCreate,
    PatientPackageUpdate,
    PaymentCreate,
)


class BillingValidationError(Exception):
    """Raised when validation fails for billing operations."""


class BillingNotFoundError(Exception):
    """Raised when a billing resource is not found."""


class BillingService:
    """Service managing package catalogue, patient packages, invoices, line items, and payments with clinic isolation."""

    package_repository: PackageRepository
    patient_package_repository: PatientPackageRepository
    invoice_repository: InvoiceRepository
    invoice_item_repository: InvoiceItemRepository
    payment_repository: PaymentRepository
    patient_repository: PatientRepository
    appointment_repository: AppointmentRepository

    def __init__(
        self,
        package_repository: PackageRepository,
        patient_package_repository: PatientPackageRepository,
        invoice_repository: InvoiceRepository,
        invoice_item_repository: InvoiceItemRepository,
        payment_repository: PaymentRepository,
        patient_repository: PatientRepository,
        appointment_repository: AppointmentRepository,
    ) -> None:
        """Inject billing repositories and verification repositories."""

        self.package_repository = package_repository
        self.patient_package_repository = patient_package_repository
        self.invoice_repository = invoice_repository
        self.invoice_item_repository = invoice_item_repository
        self.payment_repository = payment_repository
        self.patient_repository = patient_repository
        self.appointment_repository = appointment_repository

    # --- Package Catalog Methods ---

    async def create_package(self, clinic_id: UUID, payload: PackageCreate) -> Package:
        """Create a new treatment package in the clinic catalogue."""

        package_data = payload.model_dump()
        package_data["clinic_id"] = clinic_id
        package_data["status"] = PackageStatus.ACTIVE
        return await self.package_repository.create(package_data)

    async def get_package(self, clinic_id: UUID, package_id: UUID) -> Package:
        """Retrieve a package from the catalogue ensuring clinic isolation."""

        package = await self.package_repository.get_by_id(package_id, clinic_id=clinic_id)
        if package is None:
            raise BillingNotFoundError(f"Package '{package_id}' not found for clinic '{clinic_id}'.")
        return package

    async def list_packages(
        self,
        clinic_id: UUID,
        *,
        status: PackageStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Package]:
        """List package catalogue items for a clinic."""

        return await self.package_repository.list_packages(
            clinic_id=clinic_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    async def update_package(self, clinic_id: UUID, package_id: UUID, payload: PackageUpdate) -> Package:
        """Update a package in the clinic catalogue."""

        package = await self.get_package(clinic_id, package_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return package
        return await self.package_repository.update(package, update_data)

    async def delete_package(self, clinic_id: UUID, package_id: UUID) -> None:
        """Delete a package from the catalogue for the clinic."""

        package = await self.get_package(clinic_id, package_id)
        await self.package_repository.delete(package)

    # --- Patient Package Methods ---

    async def sell_package(self, clinic_id: UUID, payload: PatientPackageCreate) -> PatientPackage:
        """Sell or assign a treatment package to a patient."""

        patient = await self.patient_repository.get_by_patient_id(payload.patient_id, clinic_id=clinic_id)
        if patient is None:
            raise BillingValidationError(
                f"Patient '{payload.patient_id}' does not exist or does not belong to clinic '{clinic_id}'."
            )

        if payload.package_id is not None:
            catalog_package = await self.package_repository.get_by_id(payload.package_id, clinic_id=clinic_id)
            if catalog_package is None:
                raise BillingValidationError(
                    f"Catalogue package '{payload.package_id}' does not exist or does not belong to clinic '{clinic_id}'."
                )

        package_data = payload.model_dump()
        package_data.update(
            {
                "clinic_id": clinic_id,
                "completed_sessions": 0,
                "status": PackageStatus.ACTIVE,
            }
        )

        return await self.patient_package_repository.create(package_data)

    async def get_patient_package(self, clinic_id: UUID, patient_package_id: UUID) -> PatientPackage:
        """Retrieve a patient package ensuring clinic scoping."""

        package = await self.patient_package_repository.get_by_id(patient_package_id, clinic_id=clinic_id)
        if package is None:
            raise BillingNotFoundError(f"Patient package '{patient_package_id}' not found for clinic '{clinic_id}'.")
        return package

    async def list_patient_packages(
        self,
        clinic_id: UUID,
        *,
        patient_id: UUID | None = None,
        status: PackageStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PatientPackage]:
        """List patient packages for a clinic with optional filters."""

        return await self.patient_package_repository.list_packages(
            clinic_id=clinic_id,
            patient_id=patient_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    async def update_patient_package(
        self, clinic_id: UUID, patient_package_id: UUID, payload: PatientPackageUpdate
    ) -> PatientPackage:
        """Update a patient treatment package."""

        package = await self.get_patient_package(clinic_id, patient_package_id)
        update_data = payload.model_dump(exclude_unset=True)

        if payload.completed_sessions is not None:
            if payload.completed_sessions > package.total_sessions:
                raise BillingValidationError(
                    f"Completed sessions ({payload.completed_sessions}) cannot exceed total sessions ({package.total_sessions})."
                )
            if payload.completed_sessions == package.total_sessions:
                update_data["status"] = PackageStatus.COMPLETED

        if not update_data:
            return package

        return await self.patient_package_repository.update(package, update_data)

    async def delete_patient_package(self, clinic_id: UUID, patient_package_id: UUID) -> None:
        """Delete a patient package record for the clinic."""

        package = await self.get_patient_package(clinic_id, patient_package_id)
        await self.patient_package_repository.delete(package)

    # --- Invoice Methods ---

    async def create_invoice(self, clinic_id: UUID, payload: InvoiceCreate) -> Invoice:
        """Create a clinic-scoped invoice with line items, calculating subtotal and total."""

        patient = await self.patient_repository.get_by_patient_id(payload.patient_id, clinic_id=clinic_id)
        if patient is None:
            raise BillingValidationError(
                f"Patient '{payload.patient_id}' does not exist or does not belong to clinic '{clinic_id}'."
            )

        if payload.appointment_id is not None:
            appointment = await self.appointment_repository.get_by_id(payload.appointment_id, clinic_id=clinic_id)
            if appointment is None:
                raise BillingValidationError(
                    f"Appointment '{payload.appointment_id}' does not exist or does not belong to clinic '{clinic_id}'."
                )

        subtotal = Decimal("0.00")
        items_data: list[dict[str, object]] = []
        json_line_items: list[dict[str, object]] = []

        if payload.items:
            for item in payload.items:
                item_total = Decimal(item.quantity) * item.unit_price
                subtotal += item_total
                items_data.append(
                    {
                        "clinic_id": clinic_id,
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total_price": item_total,
                    }
                )
                json_line_items.append(
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "total_price": str(item_total),
                    }
                )
        elif payload.line_items:
            json_line_items = list(payload.line_items)
            for li in payload.line_items:
                qty = int(li.get("quantity", 1))
                price = Decimal(str(li.get("unit_price", li.get("amount", "0.00"))))
                item_total = Decimal(qty) * price
                subtotal += item_total
                items_data.append(
                    {
                        "clinic_id": clinic_id,
                        "description": str(li.get("description", "Line item")),
                        "quantity": qty,
                        "unit_price": price,
                        "total_price": item_total,
                    }
                )

        total_amount = subtotal - payload.discount_amount + payload.tax_amount
        if total_amount < Decimal("0.00"):
            raise BillingValidationError("Total invoice amount cannot be negative.")

        invoice_data = payload.model_dump(exclude={"items", "line_items"})
        invoice_data.update(
            {
                "clinic_id": clinic_id,
                "subtotal": subtotal,
                "total_amount": total_amount,
                "paid_amount": Decimal("0.00"),
                "status": InvoiceStatus.ISSUED,
                "line_items": json_line_items,
            }
        )

        invoice = await self.invoice_repository.create(invoice_data)

        for item_dict in items_data:
            item_dict["invoice_id"] = invoice.id
            await self.invoice_item_repository.create(item_dict)

        loaded_invoice = await self.invoice_repository.get_by_id_with_items(invoice.id, clinic_id=clinic_id)
        if loaded_invoice is None:
            raise BillingNotFoundError(f"Created invoice '{invoice.id}' could not be reloaded.")
        return loaded_invoice

    async def get_invoice(self, clinic_id: UUID, invoice_id: UUID) -> Invoice:
        """Retrieve a clinic-scoped invoice."""

        invoice = await self.invoice_repository.get_by_id_with_items(invoice_id, clinic_id=clinic_id)
        if invoice is None:
            raise BillingNotFoundError(f"Invoice '{invoice_id}' not found for clinic '{clinic_id}'.")
        return invoice

    async def list_invoices(
        self,
        clinic_id: UUID,
        *,
        patient_id: UUID | None = None,
        status: InvoiceStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        """List clinic-scoped invoices with optional filters."""

        return await self.invoice_repository.list_invoices(
            clinic_id=clinic_id,
            patient_id=patient_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    async def update_invoice(self, clinic_id: UUID, invoice_id: UUID, payload: InvoiceUpdate) -> Invoice:
        """Update an invoice for the clinic."""

        invoice = await self.get_invoice(clinic_id, invoice_id)
        update_data = payload.model_dump(exclude_unset=True)

        if payload.appointment_id is not None:
            appointment = await self.appointment_repository.get_by_id(payload.appointment_id, clinic_id=clinic_id)
            if appointment is None:
                raise BillingValidationError(
                    f"Appointment '{payload.appointment_id}' does not exist or does not belong to clinic '{clinic_id}'."
                )

        if not update_data:
            return invoice

        return await self.invoice_repository.update(invoice, update_data)

    async def delete_invoice(self, clinic_id: UUID, invoice_id: UUID) -> None:
        """Delete or cancel an invoice for the clinic."""

        invoice = await self.get_invoice(clinic_id, invoice_id)
        await self.invoice_repository.delete(invoice)

    # --- Payment Methods ---

    async def record_payment(self, clinic_id: UUID, payload: PaymentCreate) -> Payment:
        """Record a payment against an invoice and update invoice status."""

        invoice = await self.get_invoice(clinic_id, payload.invoice_id)
        patient = await self.patient_repository.get_by_patient_id(payload.patient_id, clinic_id=clinic_id)

        if patient is None:
            raise BillingValidationError(
                f"Patient '{payload.patient_id}' does not exist or does not belong to clinic '{clinic_id}'."
            )

        if invoice.patient_id != payload.patient_id:
            raise BillingValidationError(
                f"Invoice '{payload.invoice_id}' belongs to patient '{invoice.patient_id}', not '{payload.patient_id}'."
            )

        payment_data = payload.model_dump()
        payment_data["clinic_id"] = clinic_id
        payment = await self.payment_repository.create(payment_data)

        new_paid_amount = invoice.paid_amount + payload.amount
        new_status = invoice.status

        if new_paid_amount >= invoice.total_amount:
            new_status = InvoiceStatus.PAID
        elif new_paid_amount > Decimal("0.00"):
            new_status = InvoiceStatus.PARTIAL

        await self.invoice_repository.update(
            invoice,
            {"paid_amount": new_paid_amount, "status": new_status},
        )

        return payment

    async def get_payment(self, clinic_id: UUID, payment_id: UUID) -> Payment:
        """Retrieve a single payment by ID ensuring clinic scoping."""

        payment = await self.payment_repository.get_by_id(payment_id, clinic_id=clinic_id)
        if payment is None:
            raise BillingNotFoundError(f"Payment '{payment_id}' not found for clinic '{clinic_id}'.")
        return payment

    async def list_payments(
        self,
        clinic_id: UUID,
        *,
        invoice_id: UUID | None = None,
        patient_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        """List clinic-scoped payments with optional filters."""

        return await self.payment_repository.list_payments(
            clinic_id=clinic_id,
            invoice_id=invoice_id,
            patient_id=patient_id,
            offset=offset,
            limit=limit,
        )

    async def delete_payment(self, clinic_id: UUID, payment_id: UUID) -> None:
        """Delete a payment record for the clinic."""

        payment = await self.get_payment(clinic_id, payment_id)
        await self.payment_repository.delete(payment)

    async def generate_invoice_pdf(self, clinic_id: UUID, invoice_id: UUID) -> bytes:
        """Generate PDF representation of a clinic invoice."""

        invoice = await self.get_invoice(clinic_id, invoice_id)
        pdf_content = (
            f"%PDF-1.4\n"
            f"% INVOICE {invoice.invoice_number}\n"
            f"Clinic: {clinic_id}\n"
            f"Patient: {invoice.patient_id}\n"
            f"Total: {invoice.total_amount}\n"
        ).encode("utf-8")
        return pdf_content
