from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import require_roles
from app.enums.user import UserRole

from sqlalchemy.ext.asyncio import AsyncSession


from app.core.dependencies import get_async_session, get_current_clinic
from app.models.clinic import Clinic
from app.repositories.appointment import AppointmentRepository
from app.repositories.patient import PatientRepository
from app.repositories.treatment import SoapAssessmentRepository
from app.schemas.treatment import (
    SoapAssessmentCreate,
    SoapAssessmentListResponse,
    SoapAssessmentResponse,
    SoapAssessmentUpdate,
)
from app.services.treatment import (
    SoapAssessmentService,
    TreatmentNotFoundError,
    TreatmentValidationError,
)

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.THERAPIST))])


async def get_assessment_service(
    session: AsyncSession = Depends(get_async_session),
) -> SoapAssessmentService:
    """Inject SoapAssessmentService bound to active session."""

    return SoapAssessmentService(
        repository=SoapAssessmentRepository(session),
        patient_repository=PatientRepository(session),
        appointment_repository=AppointmentRepository(session),
    )



AssessmentServiceDep = Annotated[SoapAssessmentService, Depends(get_assessment_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


@router.post("", response_model=SoapAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_soap_assessment(
    payload: SoapAssessmentCreate,
    clinic: CurrentClinicDep,
    service: AssessmentServiceDep,
) -> SoapAssessmentResponse:
    """Create a new SOAP assessment for the authenticated clinic."""

    try:
        assessment = await service.create_assessment(clinic.id, payload)
        return SoapAssessmentResponse.model_validate(assessment)
    except TreatmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=SoapAssessmentListResponse)
async def list_soap_assessments(
    clinic: CurrentClinicDep,
    service: AssessmentServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    patient_id: Annotated[UUID | None, Query(alias="patient_id")] = None,
    appointment_id: Annotated[UUID | None, Query(alias="appointment_id")] = None,
    specialty: Annotated[str | None, Query()] = None,
    is_reassessment: Annotated[bool | None, Query()] = None,
) -> SoapAssessmentListResponse:
    """List SOAP assessments for the authenticated clinic with optional filtering."""

    assessments = await service.list_assessments(
        clinic.id,
        patient_id=patient_id,
        appointment_id=appointment_id,
        specialty=specialty,
        is_reassessment=is_reassessment,
        offset=offset,
        limit=limit,
    )

    items = [SoapAssessmentResponse.model_validate(a) for a in assessments]
    return SoapAssessmentListResponse(
        items=items,
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.get("/{id}", response_model=SoapAssessmentResponse)
async def get_soap_assessment(
    id: UUID,
    clinic: CurrentClinicDep,
    service: AssessmentServiceDep,
) -> SoapAssessmentResponse:
    """Retrieve a SOAP assessment by ID for the authenticated clinic."""

    try:
        assessment = await service.get_assessment(clinic.id, id)
        return SoapAssessmentResponse.model_validate(assessment)
    except TreatmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{id}", response_model=SoapAssessmentResponse)
async def update_soap_assessment(
    id: UUID,
    payload: SoapAssessmentUpdate,
    clinic: CurrentClinicDep,
    service: AssessmentServiceDep,
) -> SoapAssessmentResponse:
    """Update a SOAP assessment for the authenticated clinic."""

    try:
        assessment = await service.update_assessment(clinic.id, id, payload)
        return SoapAssessmentResponse.model_validate(assessment)
    except TreatmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TreatmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
