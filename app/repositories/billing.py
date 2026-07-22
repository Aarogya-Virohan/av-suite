from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
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

    async def list_packages(
        self,
        *,
        clinic_id: UUID | None = None,
        patient_id: UUID | None = None,
        status: PackageStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PatientPackage]:
        """List patient packages with optional filters."""

        effective_limit = min(limit, 500)
        statement = select(PatientPackage)

        if patient_id is not None:
            statement = statement.where(PatientPackage.patient_id == patient_id)

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

    async def get_by_id_with_items(self, invoice_id: UUID, *, clinic_id: UUID | None = None) -> Invoice | None:
        """Retrieve an invoice with loaded items and payments ensuring clinic isolation."""

        statement = (
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments))
            .where(Invoice.id == invoice_id)
        )
        statement = self._apply_clinic_scope(statement, clinic_id)
        result = await self.session.scalars(statement)
        return result.first()

    async def list_invoices(
        self,
        *,
        clinic_id: UUID | None = None,
        patient_id: UUID | None = None,
        status: InvoiceStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Invoice]:
        """List invoices with optional patient and status filters."""

        effective_limit = min(limit, 500)
        statement = select(Invoice).options(selectinload(Invoice.items))

        if patient_id is not None:
            statement = statement.where(Invoice.patient_id == patient_id)

        if status is not None:
            statement = statement.where(Invoice.status == status)

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

    async def list_payments(
        self,
        *,
        clinic_id: UUID | None = None,
        invoice_id: UUID | None = None,
        patient_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        """List payments with optional invoice and patient filters."""

        effective_limit = min(limit, 500)
        statement = select(Payment)

        if invoice_id is not None:
            statement = statement.where(Payment.invoice_id == invoice_id)

        if patient_id is not None:
            statement = statement.where(Payment.patient_id == patient_id)

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())
