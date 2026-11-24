from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_async_session,
    get_current_clinic,
    get_current_user,
    require_capability,
)
from app.enums.document import DocumentCategory
from app.enums.permission import CapabilityScope
from app.models.clinic import Clinic
from app.models.user import User
from app.repositories.document import PatientDocumentRepository
from app.repositories.patient import PatientRepository
from app.repositories.treatment import TreatmentSessionRepository
from app.schemas.document import (
    PatientDocumentCreate,
    PatientDocumentListResponse,
    PatientDocumentResponse,
    PatientDocumentUpdate,
)
from app.services.document import (
    DocumentNotFoundError,
    DocumentService,
    DocumentValidationError,
)
from app.core.upload_limits import MAX_DOCUMENT_BYTES, read_capped, reject_oversized_request
from app.services.audit import log_event_safely


def check_documents_enabled(clinic: Clinic = Depends(get_current_clinic)) -> None:
    if not clinic.is_documents_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Documents bucket is disabled for this clinic.",
        )


router = APIRouter(dependencies=[Depends(check_documents_enabled)])


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
CurrentUserDep = Annotated[User, Depends(get_current_user)]


# --- Patient Document Endpoints ---


@router.post(
    "/patients/{patient_id}/documents",
    response_model=PatientDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_patient_document(
    request: Request,
    patient_id: UUID,
    clinic: CurrentClinicDep,
    user: CurrentUserDep,
    service: DocumentServiceDep,
    label: Annotated[str, Form(min_length=1, max_length=255)],
    category: Annotated[DocumentCategory, Form()],
    notes: Annotated[str | None, Form(max_length=2000)] = None,
    treatment_id: Annotated[UUID | None, Form()] = None,
    file: UploadFile = File(...),
    scope: CapabilityScope = Depends(require_capability("documents.upload")),
) -> PatientDocumentResponse:
    """Upload and register a document for a specific patient."""

    try:
        from app.core.storage import StorageUnavailableError, storage_client
        import uuid

        reject_oversized_request(request, MAX_DOCUMENT_BYTES, "The file")
        file_bytes = await read_capped(file, MAX_DOCUMENT_BYTES, "The file")
        file_ext = (
            file.filename.split(".")[-1]
            if file.filename and "." in file.filename
            else "bin"
        )
        path = f"{clinic.id}/{patient_id}/{uuid.uuid4()}.{file_ext}"

        # Blocking Supabase client: run it in a thread, not on the event loop.
        await asyncio.to_thread(
            storage_client.upload_file,
            path, file_bytes, file.content_type or "application/octet-stream",
        )

        payload = PatientDocumentCreate(
            patient_id=patient_id,
            label=label,
            category=category,
            notes=notes,
            treatment_id=treatment_id,
            file_url=path,
            file_type=file.content_type or "application/octet-stream",
            file_size=len(file_bytes),
        )

        document = await service.create_document(clinic.id, payload)
        # Ids, category and size only: never the label, notes or file content.
        await log_event_safely(
            service.document_repository.session, clinic.id, user.id,
            "upload", "document", document.id,
            {
                "patient_id": str(patient_id),
                "category": category.value,
                "file_type": payload.file_type,
                "file_size": payload.file_size,
            },
        )
        return PatientDocumentResponse.model_validate(document)
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except StorageUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is temporarily unavailable.",
        ) from exc


@router.post(
    "/documents",
    response_model=PatientDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    payload: PatientDocumentCreate,
    clinic: CurrentClinicDep,
    user: CurrentUserDep,
    service: DocumentServiceDep,
    scope: CapabilityScope = Depends(require_capability("documents.upload")),
) -> PatientDocumentResponse:
    """Register document metadata."""

    try:
        document = await service.create_document(clinic.id, payload)
        await log_event_safely(
            service.document_repository.session, clinic.id, user.id,
            "upload", "document", document.id,
            {
                "patient_id": str(payload.patient_id),
                "category": payload.category.value,
                "file_type": payload.file_type,
                "file_size": payload.file_size,
            },
        )
        return PatientDocumentResponse.model_validate(document)
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "/patients/{patient_id}/documents",
    response_model=PatientDocumentListResponse,
)
async def list_patient_documents_by_patient(
    patient_id: UUID,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
    treatment_id: Annotated[UUID | None, Query(alias="treatment_id")] = None,
    category: Annotated[DocumentCategory | None, Query(alias="category")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    scope: CapabilityScope = Depends(require_capability("documents.view")),
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
    total = await service.document_repository.count_documents(
        clinic_id=clinic.id, patient_id=patient_id, treatment_id=treatment_id, category=category
    )
    return PatientDocumentListResponse(
        items=items, total=total, offset=offset, limit=limit
    )


@router.get("/documents", response_model=PatientDocumentListResponse)
async def list_documents(
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
    patient_id: Annotated[UUID | None, Query(alias="patient_id")] = None,
    treatment_id: Annotated[UUID | None, Query(alias="treatment_id")] = None,
    category: Annotated[DocumentCategory | None, Query(alias="category")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    scope: CapabilityScope = Depends(require_capability("documents.view")),
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
    total = await service.document_repository.count_documents(
        clinic_id=clinic.id, patient_id=patient_id, treatment_id=treatment_id, category=category
    )
    return PatientDocumentListResponse(
        items=items, total=total, offset=offset, limit=limit
    )


@router.get("/documents/{id}", response_model=PatientDocumentResponse)
async def get_document(
    id: UUID,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
    scope: CapabilityScope = Depends(require_capability("documents.view")),
) -> PatientDocumentResponse:
    """Retrieve document metadata by ID."""

    try:
        document = await service.get_document(clinic.id, id)
        return PatientDocumentResponse.model_validate(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/documents/{id}/download")
async def download_document(
    id: UUID,
    clinic: CurrentClinicDep,
    user: CurrentUserDep,
    service: DocumentServiceDep,
    scope: CapabilityScope = Depends(require_capability("documents.view")),
) -> Response:
    """Download or retrieve private document location (authenticated, clinic-scoped)."""

    from app.core.storage import StorageUnavailableError

    try:
        document = await service.get_document(clinic.id, id)

        # Determine URL
        if document.file_url.startswith("http"):
            url = document.file_url
            headers = {"Location": url}
            await log_event_safely(
                service.document_repository.session, clinic.id, user.id,
                "download", "document", document.id,
            )
            return Response(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers=headers
            )
        else:
            from app.core.storage import storage_client

            file_bytes = await asyncio.to_thread(storage_client.download_file, document.file_url)

            await log_event_safely(
                service.document_repository.session, clinic.id, user.id,
                "download", "document", document.id,
            )

            headers = {
                "Content-Disposition": f'attachment; filename="{document.label}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            }
            return Response(
                content=file_bytes,
                media_type=document.file_type or "application/octet-stream",
                headers=headers,
            )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except StorageUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is temporarily unavailable.",
        ) from exc


@router.patch("/documents/{id}", response_model=PatientDocumentResponse)
async def update_document(
    id: UUID,
    payload: PatientDocumentUpdate,
    clinic: CurrentClinicDep,
    service: DocumentServiceDep,
    scope: CapabilityScope = Depends(require_capability("documents.edit")),
) -> PatientDocumentResponse:
    """Update document metadata."""

    try:
        document = await service.update_document(clinic.id, id, payload)
        return PatientDocumentResponse.model_validate(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete(
    "/documents/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_document(
    id: UUID,
    clinic: CurrentClinicDep,
    user: CurrentUserDep,
    service: DocumentServiceDep,
    scope: CapabilityScope = Depends(require_capability("documents.delete")),
) -> None:
    """Delete a patient document record."""

    try:
        document = await service.get_document(clinic.id, id)
        details = {
            "patient_id": str(document.patient_id),
            "category": getattr(document.category, "value", str(document.category)),
        }
        await service.delete_document(clinic.id, id, deleted_by=user.id)
        await log_event_safely(
            service.document_repository.session, clinic.id, user.id,
            "delete", "document", id, details,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
