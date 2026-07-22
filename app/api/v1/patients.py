from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.models.clinic import Clinic
from app.repositories.patient import PatientRepository
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient import PatientNotFoundError, PatientService, PatientValidationError

router = APIRouter()


async def get_patient_service(
    session: AsyncSession = Depends(get_async_session),
) -> PatientService:
    """Inject PatientService with a session-bound repository."""

    return PatientService(PatientRepository(session))


PatientServiceDep = Annotated[PatientService, Depends(get_patient_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    payload: PatientCreate,
    clinic: CurrentClinicDep,
    service: PatientServiceDep,
) -> PatientResponse:
    """Create a new patient record scoped to the authenticated clinic."""

    try:
        patient = await service.create_patient(clinic.id, payload)
        return PatientResponse.model_validate(patient)
    except PatientValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=PatientListResponse)
async def list_patients(
    clinic: CurrentClinicDep,
    service: PatientServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    query: Annotated[str | None, Query()] = None,
    active_only: Annotated[bool, Query()] = False,
) -> PatientListResponse:
    """List or search patients for the authenticated clinic with pagination."""

    if query:
        patients = await service.search_patients(
            clinic.id, query=query, offset=offset, limit=limit
        )
    else:
        patients = await service.list_patients(
            clinic.id, offset=offset, limit=limit, active_only=active_only
        )

    items = [PatientResponse.model_validate(p) for p in patients]
    return PatientListResponse(
        items=items,
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.get("/{id}", response_model=PatientResponse)
async def get_patient(
    id: UUID,
    clinic: CurrentClinicDep,
    service: PatientServiceDep,
) -> PatientResponse:
    """Retrieve a single patient record by ID for the authenticated clinic."""

    try:
        patient = await service.get_patient(clinic.id, id)
        return PatientResponse.model_validate(patient)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{id}", response_model=PatientResponse)
async def update_patient(
    id: UUID,
    payload: PatientUpdate,
    clinic: CurrentClinicDep,
    service: PatientServiceDep,
) -> PatientResponse:
    """Update a patient record by ID for the authenticated clinic."""

    try:
        patient = await service.update_patient(clinic.id, id, payload)
        return PatientResponse.model_validate(patient)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PatientValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    id: UUID,
    clinic: CurrentClinicDep,
    service: PatientServiceDep,
) -> None:
    """Delete a patient record by ID for the authenticated clinic."""

    try:
        await service.delete_patient(clinic.id, id)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
