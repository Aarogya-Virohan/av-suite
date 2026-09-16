from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
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

        statement = (
            self._apply_clinic_scope(statement, clinic_id)
            .offset(offset)
            .limit(effective_limit)
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def list_documents_for_therapist(
        self,
        *,
        clinic_id: UUID,
        therapist_id: UUID,
        patient_id: UUID | None = None,
        treatment_id: UUID | None = None,
        category: DocumentCategory | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PatientDocument]:
        """List documents for patients scheduled with or treated by a therapist."""

        from app.models.appointment import Appointment
        from app.models.treatment import TreatmentSession

        statement = (
            select(PatientDocument)
            .outerjoin(
                Appointment,
                (Appointment.patient_id == PatientDocument.patient_id)
                & (Appointment.clinic_id == PatientDocument.clinic_id),
            )
            .outerjoin(
                TreatmentSession,
                (TreatmentSession.patient_id == PatientDocument.patient_id)
                & (TreatmentSession.clinic_id == PatientDocument.clinic_id),
            )
            .where(
                PatientDocument.clinic_id == clinic_id,
                or_(
                    Appointment.therapist_id == therapist_id,
                    TreatmentSession.therapist_id == therapist_id,
                ),
            )
            .distinct()
        )
        if patient_id is not None:
            statement = statement.where(PatientDocument.patient_id == patient_id)
        if treatment_id is not None:
            statement = statement.where(PatientDocument.treatment_id == treatment_id)
        if category is not None:
            statement = statement.where(PatientDocument.category == category)

        result = await self.session.scalars(
            statement.offset(offset).limit(min(limit, 500))
        )
        return list(result.all())

    async def belongs_to_therapist(
        self, *, clinic_id: UUID, document_id: UUID, therapist_id: UUID
    ) -> bool:
        """Return whether a document's patient is scheduled with or treated by a therapist."""

        from app.models.appointment import Appointment
        from app.models.treatment import TreatmentSession

        statement = (
            select(PatientDocument.id)
            .outerjoin(
                Appointment,
                (Appointment.patient_id == PatientDocument.patient_id)
                & (Appointment.clinic_id == PatientDocument.clinic_id),
            )
            .outerjoin(
                TreatmentSession,
                (TreatmentSession.patient_id == PatientDocument.patient_id)
                & (TreatmentSession.clinic_id == PatientDocument.clinic_id),
            )
            .where(
                PatientDocument.id == document_id,
                PatientDocument.clinic_id == clinic_id,
                or_(
                    Appointment.therapist_id == therapist_id,
                    TreatmentSession.therapist_id == therapist_id,
                ),
            )
        )
        return (await self.session.scalar(statement)) is not None

    async def patient_belongs_to_therapist(
        self, *, clinic_id: UUID, patient_id: UUID, therapist_id: UUID
    ) -> bool:
        """Return whether a patient is scheduled with or treated by a therapist."""

        from app.models.appointment import Appointment
        from app.models.treatment import TreatmentSession

        statement = (
            select(Appointment.patient_id)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.patient_id == patient_id,
                Appointment.therapist_id == therapist_id,
            )
            .union(
                select(TreatmentSession.patient_id).where(
                    TreatmentSession.clinic_id == clinic_id,
                    TreatmentSession.patient_id == patient_id,
                    TreatmentSession.therapist_id == therapist_id,
                )
            )
        )
        return (await self.session.scalar(statement)) is not None
