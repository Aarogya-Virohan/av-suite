from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums.billing import InvoiceStatus
from app.enums.package import PackageStatus
from app.models.billing import Invoice, InvoiceItem, Package, PatientPackage, Payment
from app.repositories.base import BaseRepository


class PackageRepository(BaseRepository[Package]):
    """Repository for clinic-scoped Package catalogue operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, Package)

    async def count_packages(self, *, clinic_id: UUID, status: PackageStatus | None = None) -> int:
        statement = select(func.count()).select_from(Package)
        if status is not None: statement = statement.where(Package.status == status)
        statement = self._apply_clinic_scope(statement, clinic_id)
        return int(await self.session.scalar(statement) or 0)

    async def list_packages(
        self,
        *,
        clinic_id: UUID | None = None,
        status: PackageStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Package]:
        """List package catalogue items with optional filters."""

        effective_limit = min(limit, 500)
        statement = select(Package)

        if status is not None:
            statement = statement.where(Package.status == status)

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())


class PatientPackageRepository(BaseRepository[PatientPackage]):
    """Repository for clinic-scoped PatientPackage operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, PatientPackage)

    async def count_packages(self, *, clinic_id: UUID, patient_id: UUID | None = None,
                             package_id: UUID | None = None, status: PackageStatus | None = None) -> int:
        statement = select(func.count()).select_from(PatientPackage)
        if patient_id is not None: statement = statement.where(PatientPackage.patient_id == patient_id)
        if package_id is not None: statement = statement.where(PatientPackage.package_id == package_id)
        if status is not None: statement = statement.where(PatientPackage.status == status)
        statement = self._apply_clinic_scope(statement, clinic_id)
        return int(await self.session.scalar(statement) or 0)

    async def list_packages(
        self,
        *,
        clinic_id: UUID | None = None,
        patient_id: UUID | None = None,
        package_id: UUID | None = None,
        status: PackageStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PatientPackage]:
        """List patient packages with optional filters."""

        effective_limit = min(limit, 500)
        statement = select(PatientPackage)

        if patient_id is not None:
            statement = statement.where(PatientPackage.patient_id == patient_id)

        if package_id is not None:
            statement = statement.where(PatientPackage.package_id == package_id)

        if status is not None:
            statement = statement.where(PatientPackage.status == status)

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for clinic-scoped Invoice operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, Invoice)

    async def count_invoices(self, *, clinic_id: UUID, patient_id: UUID | None = None,
                             status: InvoiceStatus | None = None, start_date: date | None = None,
                             end_date: date | None = None) -> int:
        statement = select(func.count()).select_from(Invoice)
        if patient_id is not None: statement = statement.where(Invoice.patient_id == patient_id)
        if status is not None: statement = statement.where(Invoice.status == status)
        if start_date is not None:
            statement = statement.where(Invoice.issue_date >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        if end_date is not None:
            statement = statement.where(Invoice.issue_date <= datetime.combine(end_date, time.max, tzinfo=timezone.utc))
        statement = self._apply_clinic_scope(statement, clinic_id)
        return int(await self.session.scalar(statement) or 0)

    async def get_by_id_with_items(
        self,
        invoice_id: UUID,
        *,
        clinic_id: UUID | None = None,
        for_update: bool = False,
    ) -> Invoice | None:
        """Retrieve an invoice with loaded items and payments ensuring clinic isolation."""

        statement = (
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments), selectinload(Invoice.patient))
            .where(Invoice.id == invoice_id)
        )
        statement = self._apply_clinic_scope(statement, clinic_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.scalars(statement)
        return result.first()

    async def list_invoices(
        self,
        *,
        clinic_id: UUID | None = None,
        patient_id: UUID | None = None,
        status: InvoiceStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        """List invoices with optional patient, status, and date range filters."""

        effective_limit = min(limit, 500)
        statement = select(Invoice).options(selectinload(Invoice.items), selectinload(Invoice.patient))

        if patient_id is not None:
            statement = statement.where(Invoice.patient_id == patient_id)

        if status is not None:
            statement = statement.where(Invoice.status == status)

        if start_date is not None:
            start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            statement = statement.where(Invoice.issue_date >= start_dt)

        if end_date is not None:
            end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
            statement = statement.where(Invoice.issue_date <= end_dt)

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())


class InvoiceItemRepository(BaseRepository[InvoiceItem]):
    """Repository for clinic-scoped InvoiceItem operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, InvoiceItem)


class PaymentRepository(BaseRepository[Payment]):
    """Repository for clinic-scoped Payment operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, Payment)

    async def count_payments(self, *, clinic_id: UUID, invoice_id: UUID | None = None,
                             patient_id: UUID | None = None, start_date: date | None = None,
                             end_date: date | None = None) -> int:
        statement = select(func.count()).select_from(Payment)
        if invoice_id is not None: statement = statement.where(Payment.invoice_id == invoice_id)
        if patient_id is not None: statement = statement.where(Payment.patient_id == patient_id)
        if start_date is not None:
            statement = statement.where(Payment.payment_date >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        if end_date is not None:
            statement = statement.where(Payment.payment_date <= datetime.combine(end_date, time.max, tzinfo=timezone.utc))
        statement = self._apply_clinic_scope(statement, clinic_id)
        return int(await self.session.scalar(statement) or 0)

    async def list_payments(
        self,
        *,
        clinic_id: UUID | None = None,
        invoice_id: UUID | None = None,
        patient_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        """List payments with optional invoice, patient, and date range filters."""

        effective_limit = min(limit, 500)
        statement = select(Payment).options(selectinload(Payment.patient))

        if invoice_id is not None:
            statement = statement.where(Payment.invoice_id == invoice_id)

        if patient_id is not None:
            statement = statement.where(Payment.patient_id == patient_id)

        if start_date is not None:
            start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            statement = statement.where(Payment.payment_date >= start_dt)

        if end_date is not None:
            end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
            statement = statement.where(Payment.payment_date <= end_dt)

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())
