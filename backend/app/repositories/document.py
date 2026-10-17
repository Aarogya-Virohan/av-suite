from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.document import DocumentCategory
from app.models.document import PatientDocument
from app.repositories.base import BaseRepository


class PatientDocumentRepository(BaseRepository[PatientDocument]):
    """Repository for clinic-scoped PatientDocument operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, PatientDocument)

    async def list_documents(
        self,
        *,
        clinic_id: UUID | None = None,
        patient_id: UUID | None = None,
        treatment_id: UUID | None = None,
        category: DocumentCategory | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PatientDocument]:
        """List patient documents with optional filters and clinic scoping."""

        effective_limit = min(limit, 500)
        statement = select(PatientDocument)

        if patient_id is not None:
            statement = statement.where(PatientDocument.patient_id == patient_id)

        if treatment_id is not None:
            statement = statement.where(PatientDocument.treatment_id == treatment_id)

        if category is not None:
            statement = statement.where(PatientDocument.category == category)

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())
