from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.enums.document import DocumentCategory
from app.models.clinic import Clinic
from app.repositories.document import PatientDocumentRepository
from app.repositories.patient import PatientRepository
from app.repositories.treatment import TreatmentSessionRepository
from app.schemas.document import (
    PatientDocumentCreate,
    PatientDocumentListResponse,
    PatientDocumentResponse,
    PatientDocumentUpdate,
)
from app.services.document import DocumentNotFoundError, DocumentService, DocumentValidationError

router = APIRouter()


async def get_document_service(
    session: AsyncSession = Depends(get_async_session),
) -> DocumentService:
    """Inject DocumentService with session-bound repositories."""

    return DocumentService(
        document_repository=PatientDocumentRepository(session),
        patient_repository=PatientRepository(session),
        treatment_repository=TreatmentSessionRepository(session),
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


# --- Patient Document Endpoints ---

@router.post("/patients/{patient_id}/documents", response_model=PatientDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_patient_document(
    patient_id: UUID,
    payload: PatientDocumentCreate,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
) -> PatientDocumentResponse:
    """Register document metadata for a specific patient."""

    if payload.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id in path does not match payload patient_id.",
        )

    try:
        document = await service.create_document(clinic.id, payload)
        return PatientDocumentResponse.model_validate(document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/documents", response_model=PatientDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: PatientDocumentCreate,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
) -> PatientDocumentResponse:
    """Register document metadata."""

    try:
        document = await service.create_document(clinic.id, payload)
        return PatientDocumentResponse.model_validate(document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/patients/{patient_id}/documents", response_model=PatientDocumentListResponse)
async def list_patient_documents_by_patient(
    patient_id: UUID,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
    treatment_id: Annotated[UUID | None, Query(alias="treatment_id")] = None,
    category: Annotated[DocumentCategory | None, Query(alias="category")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PatientDocumentListResponse:
    """List documents for a specific patient with optional filtering."""

    documents = await service.list_documents(
        clinic.id,
        patient_id=patient_id,
        treatment_id=treatment_id,
        category=category,
        offset=offset,
        limit=limit,
    )
    items = [PatientDocumentResponse.model_validate(doc) for doc in documents]
    return PatientDocumentListResponse(items=items, total=len(items), offset=offset, limit=limit)


@router.get("/documents", response_model=PatientDocumentListResponse)
async def list_documents(
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
    patient_id: Annotated[UUID | None, Query(alias="patient_id")] = None,
    treatment_id: Annotated[UUID | None, Query(alias="treatment_id")] = None,
    category: Annotated[DocumentCategory | None, Query(alias="category")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PatientDocumentListResponse:
    """List documents for the authenticated clinic with optional filtering."""

    documents = await service.list_documents(
        clinic.id,
        patient_id=patient_id,
        treatment_id=treatment_id,
        category=category,
        offset=offset,
        limit=limit,
    )
    items = [PatientDocumentResponse.model_validate(doc) for doc in documents]
    return PatientDocumentListResponse(items=items, total=len(items), offset=offset, limit=limit)


@router.get("/documents/{id}", response_model=PatientDocumentResponse)
async def get_document(
    id: UUID,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
) -> PatientDocumentResponse:
    """Retrieve document metadata by ID."""

    try:
        document = await service.get_document(clinic.id, id)
        return PatientDocumentResponse.model_validate(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/documents/{id}/download")
async def download_document(
    id: UUID,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
) -> Response:
    """Download or retrieve private document location (authenticated, clinic-scoped)."""

    try:
        document = await service.get_document(clinic.id, id)
        headers = {"Location": document.file_url}
        return Response(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers=headers)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/documents/{id}", response_model=PatientDocumentResponse)
async def update_document(
    id: UUID,
    payload: PatientDocumentUpdate,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
) -> PatientDocumentResponse:
    """Update document metadata."""

    try:
        document = await service.update_document(clinic.id, id, payload)
        return PatientDocumentResponse.model_validate(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/documents/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_document(
    id: UUID,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
) -> None:
    """Delete a patient document record."""

    try:
        await service.delete_document(clinic.id, id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
