from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, UploadFile, File, Form
from app.core.dependencies import require_permission
from app.enums.user import UserRole

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

def check_documents_enabled(clinic: Clinic = Depends(get_current_clinic)) -> None:
    if not clinic.is_documents_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Documents bucket is disabled for this clinic.")

router = APIRouter(dependencies=[Depends(require_permission("documents")), Depends(check_documents_enabled)])


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
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
    label: Annotated[str, Form(min_length=1, max_length=255)],
    category: Annotated[DocumentCategory, Form()],
    notes: Annotated[str | None, Form(max_length=2000)] = None,
    treatment_id: Annotated[UUID | None, Form()] = None,
    file: UploadFile = File(...),
) -> PatientDocumentResponse:
    """Upload and register a document for a specific patient."""

    try:
        from app.core.storage import storage_client
        import uuid
        
        file_bytes = await file.read()
        file_ext = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'bin'
        path = f"{clinic.id}/{patient_id}/{uuid.uuid4()}.{file_ext}"
        
        storage_client.upload_file(path, file_bytes, file.content_type or 'application/octet-stream')
        
        payload = PatientDocumentCreate(
            patient_id=patient_id,
            label=label,
            category=category,
            notes=notes,
            treatment_id=treatment_id,
            file_url=path,
            file_type=file.content_type or 'application/octet-stream',
            file_size=len(file_bytes),
        )
        
        document = await service.create_document(clinic.id, payload)
        return PatientDocumentResponse.model_validate(document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


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
        
        # Determine URL
        if document.file_url.startswith("http"):
            url = document.file_url
        else:
            from app.core.storage import storage_client
            url = storage_client.create_signed_download_url(document.file_url, expires_in=60)
            
        headers = {"Location": url}
        return Response(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers=headers)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


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
