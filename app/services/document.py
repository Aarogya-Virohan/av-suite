from __future__ import annotations

from uuid import UUID

from app.enums.document import DocumentCategory
from app.models.document import PatientDocument
from app.repositories.document import PatientDocumentRepository
from app.repositories.patient import PatientRepository
from app.repositories.treatment import TreatmentSessionRepository
from app.schemas.document import PatientDocumentCreate, PatientDocumentUpdate


class DocumentValidationError(Exception):
    """Raised when validation fails for document operations."""


class DocumentNotFoundError(Exception):
    """Raised when a document resource is not found."""


class DocumentService:
    """Service managing patient documents and medical attachments with clinic isolation."""

    document_repository: PatientDocumentRepository
    patient_repository: PatientRepository
    treatment_repository: TreatmentSessionRepository

    def __init__(
        self,
        document_repository: PatientDocumentRepository,
        patient_repository: PatientRepository,
        treatment_repository: TreatmentSessionRepository,
    ) -> None:
        """Inject repositories required for document management."""

        self.document_repository = document_repository
        self.patient_repository = patient_repository
        self.treatment_repository = treatment_repository

    async def create_document(self, clinic_id: UUID, payload: PatientDocumentCreate) -> PatientDocument:
        """Register document metadata for a patient ensuring clinic ownership."""

        patient = await self.patient_repository.get_by_patient_id(payload.patient_id, clinic_id=clinic_id)
        if patient is None:
            raise DocumentValidationError(
                f"Patient '{payload.patient_id}' does not exist or does not belong to clinic '{clinic_id}'."
            )

        if payload.treatment_id is not None:
            treatment = await self.treatment_repository.get_by_id(payload.treatment_id, clinic_id=clinic_id)
            if treatment is None:
                raise DocumentValidationError(
                    f"Treatment '{payload.treatment_id}' does not exist or does not belong to clinic '{clinic_id}'."
                )

        doc_data = payload.model_dump()
        doc_data["clinic_id"] = clinic_id
        return await self.document_repository.create(doc_data)

    async def get_document(self, clinic_id: UUID, document_id: UUID) -> PatientDocument:
        """Retrieve a patient document ensuring clinic scoping."""

        document = await self.document_repository.get_by_id(document_id, clinic_id=clinic_id)
        if document is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found for clinic '{clinic_id}'.")
        return document

    async def list_documents(
        self,
        clinic_id: UUID,
        *,
        patient_id: UUID | None = None,
        treatment_id: UUID | None = None,
        category: DocumentCategory | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PatientDocument]:
        """List patient documents for a clinic with optional filters."""

        return await self.document_repository.list_documents(
            clinic_id=clinic_id,
            patient_id=patient_id,
            treatment_id=treatment_id,
            category=category,
            offset=offset,
            limit=limit,
        )

    async def update_document(
        self, clinic_id: UUID, document_id: UUID, payload: PatientDocumentUpdate
    ) -> PatientDocument:
        """Update a document metadata record."""

        document = await self.get_document(clinic_id, document_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return document
        return await self.document_repository.update(document, update_data)

    async def delete_document(self, clinic_id: UUID, document_id: UUID) -> None:
        """Delete a document metadata record for the clinic."""

        document = await self.get_document(clinic_id, document_id)
        await self.document_repository.delete(document)
