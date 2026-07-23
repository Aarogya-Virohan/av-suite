from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.models.clinic import Clinic
from app.repositories.appointment import AppointmentRepository
from app.repositories.patient import PatientRepository
from app.repositories.treatment import TreatmentSessionRepository
from app.repositories.user import UserRepository
from app.schemas.treatment import (
    TreatmentSessionCreate,
    TreatmentSessionListResponse,
    TreatmentSessionResponse,
    TreatmentSessionUpdate,
)
from app.services.treatment import (
    TreatmentNotFoundError,
    TreatmentSessionService,
    TreatmentValidationError,
)

router = APIRouter()


async def get_treatment_service(
    session: AsyncSession = Depends(get_async_session),
) -> TreatmentSessionService:
    """Inject TreatmentSessionService bound to active session."""

    return TreatmentSessionService(
        repository=TreatmentSessionRepository(session),
        patient_repository=PatientRepository(session),
        appointment_repository=AppointmentRepository(session),
        user_repository=UserRepository(session),
    )


TreatmentServiceDep = Annotated[TreatmentSessionService, Depends(get_treatment_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


@router.post("", response_model=TreatmentSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_treatment_session(
    payload: TreatmentSessionCreate,
    clinic: CurrentClinicDep,
    service: TreatmentServiceDep,
) -> TreatmentSessionResponse:
    """Create a new treatment session for the authenticated clinic."""

    try:
        session = await service.create_session(clinic.id, payload)
        return TreatmentSessionResponse.model_validate(session)
    except TreatmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=TreatmentSessionListResponse)
async def list_treatment_sessions(
    clinic: CurrentClinicDep,
    service: TreatmentServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    patient_id: Annotated[UUID | None, Query(alias="patient_id")] = None,
    appointment_id: Annotated[UUID | None, Query(alias="appointment_id")] = None,
    therapist_id: Annotated[UUID | None, Query(alias="therapist_id")] = None,
    start_date: Annotated[date | None, Query(alias="start_date")] = None,
    end_date: Annotated[date | None, Query(alias="end_date")] = None,
) -> TreatmentSessionListResponse:
    """List treatment sessions for the authenticated clinic with optional filtering."""

    sessions = await service.list_sessions(
        clinic.id,
        patient_id=patient_id,
        appointment_id=appointment_id,
        therapist_id=therapist_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )

    items = [TreatmentSessionResponse.model_validate(s) for s in sessions]
    return TreatmentSessionListResponse(
        items=items,
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.get("/{id}", response_model=TreatmentSessionResponse)
async def get_treatment_session(
    id: UUID,
    clinic: CurrentClinicDep,
    service: TreatmentServiceDep,
) -> TreatmentSessionResponse:
    """Retrieve a treatment session by ID for the authenticated clinic."""

    try:
        session = await service.get_session(clinic.id, id)
        return TreatmentSessionResponse.model_validate(session)
    except TreatmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{id}", response_model=TreatmentSessionResponse)
async def update_treatment_session(
    id: UUID,
    payload: TreatmentSessionUpdate,
    clinic: CurrentClinicDep,
    service: TreatmentServiceDep,
) -> TreatmentSessionResponse:
    """Update a treatment session for the authenticated clinic."""

    try:
        session = await service.update_session(clinic.id, id, payload)
        return TreatmentSessionResponse.model_validate(session)
    except TreatmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TreatmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_treatment_session(
    id: UUID,
    clinic: CurrentClinicDep,
    service: TreatmentServiceDep,
) -> None:
    """Delete a treatment session for the authenticated clinic."""

    try:
        await service.delete_session(clinic.id, id)
    except TreatmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
