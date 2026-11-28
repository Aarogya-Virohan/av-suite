from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select

from app.services.invoice_pdf import (
    InvoiceDoc,
    InvoiceLine,
    ReceiptPayment,
    document_number,
    pdf_filename,
    render_invoice_pdf,
)
from app.enums.billing import InvoiceStatus, PaymentStatus
from app.enums.package import PackageStatus
from app.models.billing import Invoice, Package, PatientPackage, Payment
from app.services.document_numbers import INV, RCP, next_financial_number
from app.models.clinic import Clinic
from app.services.usage_events import record_usage
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
from app.services.patient_number import format_patient_id
from app.utils.whatsapp import build_whatsapp_link


class BillingValidationError(Exception):
    """Raised when validation fails for billing operations."""


class BillingPayloadValidationError(BillingValidationError):
    """Raised when calculated payload fields contradict their percentages."""


AMOUNT_ROUNDING_TOLERANCE = Decimal("0.005")
DISCOUNT_REASON_THRESHOLD = 20


class BillingNotFoundError(Exception):
    """Raised when a billing resource is not found."""


class BillingConflictError(Exception):
    """Raised when a billing action conflicts with the resource's current state."""


def _validated_discount_reason(
    subtotal: Decimal,
    discount_amount: Decimal,
    discount_percent: Decimal | None,
    reason: str | None,
) -> str | None:
    normalized = reason.strip() if reason is not None else None
    # A percent discount is judged by its percent: the rupee amount is rounded
    # to paise and can sit a fraction above 20% of the subtotal (20% of 333.33
    # is 66.67), which must not ask for a reason at exactly 20%.
    if discount_percent is not None:
        reason_required = discount_percent > DISCOUNT_REASON_THRESHOLD
    else:
        reason_required = (
            discount_amount > subtotal * Decimal(DISCOUNT_REASON_THRESHOLD) / Decimal("100")
        )
    if reason_required and not normalized:
        raise BillingPayloadValidationError(
            "discount_reason is required for discounts greater than 20%."
        )
    return normalized or None


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
        package = await self.package_repository.create(package_data)
        await self.package_repository.session.commit()
        return package

    async def get_package(self, clinic_id: UUID, package_id: UUID) -> Package:
        """Retrieve a package from the catalogue ensuring clinic isolation."""

        package = await self.package_repository.get_by_id(
            package_id, clinic_id=clinic_id
        )
        if package is None:
            raise BillingNotFoundError(
                f"Package '{package_id}' not found for clinic '{clinic_id}'."
            )
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

    async def update_package(
        self, clinic_id: UUID, package_id: UUID, payload: PackageUpdate
    ) -> Package:
        """Update a package in the clinic catalogue."""

        package = await self.get_package(clinic_id, package_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return package
        updated = await self.package_repository.update(package, update_data)
        await self.package_repository.session.commit()
        return updated

    async def delete_package(self, clinic_id: UUID, package_id: UUID) -> None:
        """Delete a package from the catalogue for the clinic."""

        package = await self.get_package(clinic_id, package_id)
        await self.package_repository.delete(package)
        await self.package_repository.session.commit()

    # --- Patient Package Methods ---

    async def sell_package(
        self, clinic_id: UUID, payload: PatientPackageCreate
    ) -> PatientPackage:
        """Sell or assign a treatment package to a patient."""

        patient = await self.patient_repository.get_by_patient_id(
            payload.patient_id, clinic_id=clinic_id
        )
        if patient is None:
            raise BillingValidationError(
                f"Patient '{payload.patient_id}' does not exist or does not belong to clinic '{clinic_id}'."
            )

        if payload.package_id is not None:
            catalog_package = await self.package_repository.get_by_id(
                payload.package_id, clinic_id=clinic_id
            )
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

        sold = await self.patient_package_repository.create(package_data)
        await self.patient_package_repository.session.commit()
        return sold

    async def get_patient_package(
        self, clinic_id: UUID, patient_package_id: UUID
    ) -> PatientPackage:
        """Retrieve a patient package ensuring clinic scoping."""

        package = await self.patient_package_repository.get_by_id(
            patient_package_id, clinic_id=clinic_id
        )
        if package is None:
            raise BillingNotFoundError(
                f"Patient package '{patient_package_id}' not found for clinic '{clinic_id}'."
            )
        return package

    async def list_patient_packages(
        self,
        clinic_id: UUID,
        *,
        patient_id: UUID | None = None,
        package_id: UUID | None = None,
        status: PackageStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PatientPackage]:
        """List patient packages for a clinic with optional filters."""

        return await self.patient_package_repository.list_packages(
            clinic_id=clinic_id,
            patient_id=patient_id,
            package_id=package_id,
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

        updated = await self.patient_package_repository.update(package, update_data)
        await self.patient_package_repository.session.commit()
        return updated

    async def delete_patient_package(
        self, clinic_id: UUID, patient_package_id: UUID
    ) -> None:
        """Delete a patient package record for the clinic."""

        package = await self.get_patient_package(clinic_id, patient_package_id)
        await self.patient_package_repository.delete(package)
        await self.patient_package_repository.session.commit()

    # --- Invoice Methods ---

    async def create_invoice(self, clinic_id: UUID, payload: InvoiceCreate, user_id: UUID | None = None) -> Invoice:
        """Create a clinic-scoped invoice with line items, calculating subtotal and total."""

        patient = await self.patient_repository.get_by_patient_id(
            payload.patient_id, clinic_id=clinic_id
        )
        if patient is None:
            raise BillingValidationError(
                f"Patient '{payload.patient_id}' does not exist or does not belong to clinic '{clinic_id}'."
            )

        if payload.appointment_id is not None:
            appointment = await self.appointment_repository.get_by_id(
                payload.appointment_id, clinic_id=clinic_id
            )
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

        discount_amount = payload.discount_amount
        tax_amount = payload.tax_amount
        if payload.discount_percent is not None:
            expected_discount = (subtotal * payload.discount_percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if "discount_amount" in payload.model_fields_set and abs(discount_amount - expected_discount) > AMOUNT_ROUNDING_TOLERANCE:
                raise BillingPayloadValidationError("discount_amount does not match discount_percent.")
            discount_amount = expected_discount
        taxable_subtotal = subtotal - discount_amount
        if payload.tax_percent is not None:
            expected_tax = (taxable_subtotal * payload.tax_percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if "tax_amount" in payload.model_fields_set and abs(tax_amount - expected_tax) > AMOUNT_ROUNDING_TOLERANCE:
                raise BillingPayloadValidationError("tax_amount does not match tax_percent.")
            tax_amount = expected_tax
        total_amount = subtotal - discount_amount + tax_amount
        if total_amount < Decimal("0.00"):
            raise BillingValidationError("Total invoice amount cannot be negative.")

        discount_reason = _validated_discount_reason(
            subtotal, discount_amount, payload.discount_percent, payload.discount_reason
        )

        invoice_data = payload.model_dump(
            exclude={"items", "line_items", "invoice_number"}
        )
        invoice_data.update(
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            discount_reason=discount_reason,
        )
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

        # D-043: INV-<FY>-<6 digits>, counted per clinic per Indian financial
        # year of the issue date, from the shared server-side counter
        # (services/document_numbers.py). Invoices issued before 27 Nov 2026
        # keep their INV-0001 style number. The clinic-scoped unique
        # constraint remains the final guard.
        for attempt in range(3):
            invoice_data["invoice_number"] = await next_financial_number(
                self.invoice_repository.session,
                clinic_id,
                INV,
                invoice_data.get("issue_date"),
            )
            invoice_id = uuid4()
            invoice_data.update(
                {
                    "id": invoice_id,
                    # Keep the invoice_number from the counter, only update the ID
                }
            )
            try:
                invoice = await self.invoice_repository.create(invoice_data)
                break
            except IntegrityError as exc:
                if not self._is_invoice_number_conflict(exc):
                    raise
                await self.invoice_repository.session.rollback()
                if attempt == 2:
                    raise BillingValidationError(
                        "Could not allocate a unique invoice number. Please retry."
                    ) from exc

        for item_dict in items_data:
            item_dict["invoice_id"] = invoice.id
            await self.invoice_item_repository.create(item_dict)

        loaded_invoice = await self.invoice_repository.get_by_id_with_items(
            invoice.id, clinic_id=clinic_id
        )
        if loaded_invoice is None:
            raise BillingNotFoundError(
                f"Created invoice '{invoice.id}' could not be reloaded."
            )
        await self.invoice_repository.session.flush()
        clinic = await self.invoice_repository.session.get(Clinic, clinic_id)
        if clinic is not None:
            await record_usage(self.invoice_repository.session, clinic, user_id, "crm", "invoice_created")
        await self.invoice_repository.session.commit()
        return loaded_invoice

    async def get_invoice(self, clinic_id: UUID, invoice_id: UUID) -> Invoice:
        """Retrieve a clinic-scoped invoice."""

        invoice = await self.invoice_repository.get_by_id_with_items(
            invoice_id, clinic_id=clinic_id
        )
        if invoice is None:
            raise BillingNotFoundError(
                f"Invoice '{invoice_id}' not found for clinic '{clinic_id}'."
            )
        return invoice

    async def list_invoices(
        self,
        clinic_id: UUID,
        *,
        patient_id: UUID | None = None,
        status: InvoiceStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        """List clinic-scoped invoices with optional filters."""

        return await self.invoice_repository.list_invoices(
            clinic_id=clinic_id,
            patient_id=patient_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

    async def update_invoice(
        self, clinic_id: UUID, invoice_id: UUID, payload: InvoiceUpdate
    ) -> Invoice:
        """Update an invoice for the clinic."""

        invoice = await self.get_invoice(clinic_id, invoice_id)
        update_data = payload.model_dump(exclude_unset=True)
        # Keys the caller actually sent. update_data gains derived keys below
        # (discount_amount from a stored percent), so decisions about what the
        # caller changed must use this set.
        sent = set(update_data)
        if (
            update_data.get("status") == InvoiceStatus.DRAFT
            and invoice.status != InvoiceStatus.DRAFT
        ):
            # Only drafts can be deleted; moving an issued invoice back to
            # draft would reopen that path for paid or cancelled invoices.
            raise BillingConflictError("An issued invoice cannot be moved back to draft.")
        if "cancel_reason" in update_data and update_data["cancel_reason"] is not None:
            update_data["cancel_reason"] = update_data["cancel_reason"].strip() or None

        discount_percent = update_data.get("discount_percent", invoice.discount_percent)
        tax_percent = update_data.get("tax_percent", invoice.tax_percent)
        discount_amount = update_data.get("discount_amount", invoice.discount_amount)
        tax_amount = update_data.get("tax_amount", invoice.tax_amount)
        if discount_percent is not None:
            expected = (invoice.subtotal * discount_percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if "discount_amount" in update_data and abs(discount_amount - expected) > AMOUNT_ROUNDING_TOLERANCE:
                raise BillingPayloadValidationError("discount_amount does not match discount_percent.")
            discount_amount = expected
            update_data["discount_amount"] = expected
        if tax_percent is not None:
            expected = ((invoice.subtotal - discount_amount) * tax_percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if "tax_amount" in update_data and abs(tax_amount - expected) > AMOUNT_ROUNDING_TOLERANCE:
                raise BillingPayloadValidationError("tax_amount does not match tax_percent.")
            tax_amount = expected
            update_data["tax_amount"] = expected
        # The reason rule applies when this request sets or changes the
        # discount. Invoices issued before the rule existed may carry a large
        # discount with no reason; editing notes or cancelling them must work.
        if sent & {"discount_amount", "discount_percent", "discount_reason"}:
            update_data["discount_reason"] = _validated_discount_reason(
                invoice.subtotal,
                discount_amount,
                discount_percent,
                update_data.get("discount_reason", invoice.discount_reason),
            )
        if any(k in update_data for k in ("discount_amount", "tax_amount", "discount_percent", "tax_percent")):
            update_data["total_amount"] = invoice.subtotal - discount_amount + tax_amount

        if payload.appointment_id is not None:
            appointment = await self.appointment_repository.get_by_id(
                payload.appointment_id, clinic_id=clinic_id
            )
            if appointment is None:
                raise BillingValidationError(
                    f"Appointment '{payload.appointment_id}' does not exist or does not belong to clinic '{clinic_id}'."
                )

        if not update_data:
            return invoice

        updated = await self.invoice_repository.update(invoice, update_data)
        await self.invoice_repository.session.commit()
        # Re-load the eager response relationships after commit. The repository
        # update returns the changed ORM row with unloaded relationships, which
        # cannot be serialized safely from an async endpoint.
        return await self.get_invoice(clinic_id, updated.id)

    async def delete_invoice(
        self, clinic_id: UUID, invoice_id: UUID, deleted_by: UUID | None = None
    ) -> None:
        """Delete or cancel an invoice for the clinic."""

        invoice = await self.get_invoice(clinic_id, invoice_id)
        if invoice.status != InvoiceStatus.DRAFT:
            raise BillingConflictError("Only draft invoices can be deleted.")
        await self.invoice_repository.delete(invoice, deleted_by=deleted_by)
        await self.invoice_repository.session.commit()

    # --- Payment Methods ---

    @staticmethod
    def _is_invoice_number_conflict(exc: IntegrityError) -> bool:
        """Recognize only the clinic-scoped invoice-number unique violation."""
        original = exc.orig
        constraint_name = getattr(
            getattr(original, "diag", None), "constraint_name", None
        )
        constraint_name = constraint_name or getattr(original, "constraint_name", None)
        if constraint_name == "uq_invoices_clinic_invoice_number":
            return True
        return (
            "unique constraint failed: invoices.clinic_id, invoices.invoice_number"
            in str(original).lower()
            or 'unique constraint "uq_invoices_clinic_invoice_number"'
            in str(original).lower()
        )

    async def record_payment(self, clinic_id: UUID, payload: PaymentCreate, user_id: UUID | None = None) -> Payment:
        """Record a payment against an invoice and update invoice status."""

        invoice = await self.invoice_repository.get_by_id_with_items(
            payload.invoice_id, clinic_id=clinic_id, for_update=True
        )
        if invoice is None:
            raise BillingNotFoundError(
                f"Invoice '{payload.invoice_id}' not found for clinic '{clinic_id}'."
            )
        patient = await self.patient_repository.get_by_patient_id(
            payload.patient_id, clinic_id=clinic_id
        )

        if patient is None:
            raise BillingValidationError(
                f"Patient '{payload.patient_id}' does not exist or does not belong to clinic '{clinic_id}'."
            )

        if invoice.patient_id != payload.patient_id:
            raise BillingValidationError(
                f"Invoice '{payload.invoice_id}' belongs to patient '{invoice.patient_id}', not '{payload.patient_id}'."
            )

        remaining_balance = invoice.total_amount - invoice.paid_amount
        if payload.amount > remaining_balance:
            raise BillingValidationError(
                f"Payment amount ({payload.amount}) exceeds the remaining invoice balance ({remaining_balance})."
            )

        payment_data = payload.model_dump()
        payment_data["clinic_id"] = clinic_id
        # D-043: one receipt per payment, RCP-<FY>-<6 digits> by payment date.
        payment_data["receipt_number"] = await next_financial_number(
            self.payment_repository.session,
            clinic_id,
            RCP,
            payment_data.get("payment_date"),
        )
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
        # Build the response object, including its patient, before committing.
        # A failed reload/serialization must not leave a payment that a caller
        # may retry and accidentally duplicate.
        loaded_payment = await self.payment_repository.get_by_id_with_patient(
            payment.id, clinic_id=clinic_id
        )
        if loaded_payment is None:
            raise BillingNotFoundError(f"Created payment '{payment.id}' could not be reloaded.")
        await self.payment_repository.session.flush()
        clinic = await self.payment_repository.session.get(Clinic, clinic_id)
        if clinic is not None:
            await record_usage(self.payment_repository.session, clinic, user_id, "crm", "payment_recorded")
        await self.payment_repository.session.commit()
        return loaded_payment

    async def get_payment(self, clinic_id: UUID, payment_id: UUID) -> Payment:
        """Retrieve a single payment by ID ensuring clinic scoping."""

        payment = await self.payment_repository.get_by_id_with_patient(
            payment_id, clinic_id=clinic_id
        )
        if payment is None:
            raise BillingNotFoundError(
                f"Payment '{payment_id}' not found for clinic '{clinic_id}'."
            )
        return payment

    async def list_payments(
        self,
        clinic_id: UUID,
        *,
        invoice_id: UUID | None = None,
        patient_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        """List clinic-scoped payments with optional filters."""

        return await self.payment_repository.list_payments(
            clinic_id=clinic_id,
            invoice_id=invoice_id,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

    async def void_payment(
        self, clinic_id: UUID, payment_id: UUID, reason: str, voided_by: UUID
    ) -> tuple[Payment, Invoice, Decimal, Decimal]:
        """Void a payment and recalculate its invoice in one transaction."""

        normalized_reason = reason.strip()
        if len(normalized_reason) < 5:
            raise BillingPayloadValidationError(
                "reason must contain at least 5 non-whitespace characters."
            )
        payment_statement = (
            select(Payment)
            .where(Payment.id == payment_id, Payment.clinic_id == clinic_id)
            .with_for_update()
        )
        payment = await self.payment_repository.session.scalar(payment_statement)
        if payment is None:
            raise BillingNotFoundError(
                f"Payment '{payment_id}' not found for clinic '{clinic_id}'."
            )
        invoice = await self.invoice_repository.get_by_id_with_items(
            payment.invoice_id, clinic_id=clinic_id, for_update=True
        )
        if invoice is None:
            raise BillingNotFoundError(
                f"Invoice '{payment.invoice_id}' not found for clinic '{clinic_id}'."
            )
        if payment.status == PaymentStatus.VOIDED:
            raise BillingConflictError("Payment has already been voided.")

        previous_paid = invoice.paid_amount
        payment.status = PaymentStatus.VOIDED
        payment.void_reason = normalized_reason
        payment.voided_by = voided_by
        await self.payment_repository.session.flush()
        recalculated_paid = await self.payment_repository.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice.id,
                Payment.clinic_id == clinic_id,
                Payment.status != PaymentStatus.VOIDED,
            )
        )
        recalculated_paid = Decimal(recalculated_paid or 0)
        if invoice.status == InvoiceStatus.CANCELLED:
            updated_invoice = await self.invoice_repository.update(
                invoice, {"paid_amount": recalculated_paid}
            )
        else:
            recalculated_status = (
                InvoiceStatus.PAID
                if recalculated_paid >= invoice.total_amount and invoice.total_amount > 0
                else InvoiceStatus.PARTIAL
                if recalculated_paid > 0
                else InvoiceStatus.UNPAID
            )
            updated_invoice = await self.invoice_repository.update(
                invoice,
                {"paid_amount": recalculated_paid, "status": recalculated_status},
            )
        loaded_payment = await self.payment_repository.get_by_id_with_patient(
            payment.id, clinic_id=clinic_id
        )
        if loaded_payment is None:
            raise BillingNotFoundError(
                f"Voided payment '{payment_id}' could not be reloaded."
            )
        await self.payment_repository.session.commit()
        return loaded_payment, updated_invoice, previous_paid, recalculated_paid

    async def build_invoice_document(
        self,
        clinic_id: UUID,
        invoice_id: UUID,
        kind: str = "invoice",
        payment_id: UUID | None = None,
    ) -> InvoiceDoc:
        """Collect everything the invoice or receipt PDF prints (L-41)."""

        from app.models.clinic import Clinic

        invoice = await self.get_invoice(clinic_id, invoice_id)
        clinic = await self.invoice_repository.session.get(Clinic, clinic_id)
        patient = invoice.patient
        if patient is None:
            patient = await self.patient_repository.get_by_patient_id(
                invoice.patient_id, clinic_id=clinic_id
            )
        patient_name = (patient.full_name if patient else "").strip() or (
            f"Patient #{str(invoice.patient_id)[:8].upper()}"
        )
        if invoice.items:
            lines = [
                InvoiceLine(i.description, i.quantity, i.unit_price, i.total_price)
                for i in invoice.items
            ]
        else:
            lines = [
                InvoiceLine(
                    str(li.get("description", "")),
                    li.get("quantity", ""),
                    li.get("unit_price"),
                    li.get("total_price"),
                )
                for li in (invoice.line_items or [])
                if isinstance(li, dict)
            ]
        # Same source as the CRM receipt (GET /payments?invoice_id=), not the
        # invoice.payments relationship, which can be stale in a long session.
        receipt_rows = (
            await self.list_payments(clinic_id, invoice_id=invoice.id, limit=500)
            if kind == "receipt"
            else []
        )
        payments = [
            ReceiptPayment(
                p.payment_date,
                getattr(p.payment_method, "value", p.payment_method),
                p.transaction_reference,
                p.amount,
                getattr(p.status, "value", p.status),
                p.receipt_number,
            )
            for p in receipt_rows
        ]
        # D-043: one receipt per payment. Without payment_id the receipt is for
        # the latest completed payment, as the old receipt button did.
        selected = None
        if kind == "receipt" and payment_id is not None:
            match = [i for i, p in enumerate(receipt_rows) if p.id == payment_id]
            if not match:
                raise BillingNotFoundError(
                    f"Payment '{payment_id}' not found on invoice '{invoice_id}'."
                )
            selected = payments[match[0]]
        return InvoiceDoc(
            payment=selected,
            kind="receipt" if kind == "receipt" else "invoice",
            invoice_number=invoice.invoice_number,
            status=getattr(invoice.status, "value", invoice.status),
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            clinic_name=(clinic.name if clinic else "") or "Clinic",
            clinic_logo=clinic.branding_logo_url if clinic else None,
            address_line=clinic.address_line if clinic else None,
            city=clinic.city if clinic else None,
            state=clinic.state if clinic else None,
            pincode=clinic.pincode if clinic else None,
            phone=clinic.phone if clinic else None,
            email=clinic.email if clinic else None,
            registration_number=clinic.registration_number if clinic else None,
            gstin=clinic.gstin if clinic else None,
            authorised_person=clinic.authorised_person if clinic else None,
            patient_name=patient_name,
            patient_phone=patient.phone if patient else None,
            patient_id=format_patient_id(
                clinic.code if clinic else None, patient.display_number if patient else None
            ),
            subtotal=invoice.subtotal,
            discount_amount=invoice.discount_amount,
            discount_percent=invoice.discount_percent,
            tax_amount=invoice.tax_amount,
            tax_percent=invoice.tax_percent,
            total_amount=invoice.total_amount,
            paid_amount=invoice.paid_amount,
            notes=invoice.notes,
            items=lines,
            payments=payments,
        )

    async def generate_invoice_pdf(
        self,
        clinic_id: UUID,
        invoice_id: UUID,
        kind: str = "invoice",
        payment_id: UUID | None = None,
    ) -> tuple[bytes, str]:
        """Render the invoice (or payment receipt) PDF. Returns (bytes, file name).

        It was a fake five-line "%PDF" text until 31 Oct 2026 (L-41)."""

        doc = await self.build_invoice_document(clinic_id, invoice_id, kind, payment_id)
        pdf = await render_invoice_pdf(doc)
        return pdf, pdf_filename(doc.kind, document_number(doc))

    @staticmethod
    def _build_invoice_message(patient_name: str, pdf_url: str, patient_id: str = "") -> str:
        """Format the WhatsApp message that accompanies an invoice download."""

        id_line = f"Patient ID: {patient_id}\n\n" if patient_id else ""
        return (
            f"Hello {patient_name},\n\n"
            f"{id_line}"
            "Thank you for visiting.\n\n"
            "You can download your invoice here:\n\n"
            f"{pdf_url}"
        )

    async def generate_invoice_pdf_response(
        self, clinic_id: UUID, invoice_id: UUID
    ) -> dict[str, object]:
        """Generate an invoice PDF and return the download link plus WhatsApp deep link."""

        invoice = await self.get_invoice(clinic_id, invoice_id)
        patient = await self.patient_repository.get_by_patient_id(
            invoice.patient_id, clinic_id=clinic_id
        )
        if patient is None:
            raise BillingNotFoundError(
                f"Patient '{invoice.patient_id}' not found for clinic '{clinic_id}'."
            )

        # The route is /api/v1/invoices/..., not /api/v1/billing/... (L-41).
        # The download needs a signed-in clinic user, so a patient cannot open
        # this link yet (L-42); sharing with patients is C-20.
        # The PDF is rendered on download, not here, so this call stays fast.
        pdf_url = f"/api/v1/invoices/{invoice_id}/pdf/download"

        patient_name = getattr(patient, "full_name", "Patient")
        clinic = await self.invoice_repository.session.get(Clinic, clinic_id)
        patient_id = format_patient_id(
            clinic.code if clinic else None, getattr(patient, "display_number", None)
        )
        whatsapp_link = build_whatsapp_link(
            patient.phone or "", self._build_invoice_message(patient_name, pdf_url, patient_id)
        )

        return {
            "invoice_id": str(invoice.id),
            "status": "generated",
            "download_url": pdf_url,
            "whatsapp_link": whatsapp_link,
        }

    async def get_outstanding_balance(
        self, clinic_id: UUID, patient_id: UUID | None = None
    ) -> Decimal:
        """Calculate total outstanding unpaid balance for a patient or clinic."""

        invoices = await self.invoice_repository.list_invoices(
            clinic_id=clinic_id,
            patient_id=patient_id,
        )
        total_outstanding = Decimal("0.00")
        for inv in invoices:
            if inv.status in (
                InvoiceStatus.ISSUED,
                InvoiceStatus.UNPAID,
                InvoiceStatus.PARTIAL,
                InvoiceStatus.OVERDUE,
            ):
                outstanding = inv.total_amount - inv.paid_amount
                if outstanding > Decimal("0.00"):
                    total_outstanding += outstanding
        return total_outstanding
