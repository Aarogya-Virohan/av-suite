from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import require_roles
from app.enums.user import UserRole

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.enums.booking import AppointmentRequestStatus
from app.models.clinic import Clinic
from app.repositories.appointment import AppointmentRepository
from app.repositories.booking import AppointmentRequestRepository
from app.repositories.clinic import ClinicRepository
from app.repositories.patient import PatientRepository
from app.schemas.booking import (
    AppointmentRequestApprovalResponse,
    AppointmentRequestApprovePayload,
    AppointmentRequestCreate,
    AppointmentRequestResponse,
    AppointmentRequestUpdate,
    PublicClinicBrandingResponse,
)
from app.services.booking import BookingNotFoundError, BookingService, BookingValidationError

from app.schemas.envelope import ResponseEnvelope

router = APIRouter()
ProtectedRouterDep = Depends(require_roles(UserRole.ADMIN, UserRole.THERAPIST))


async def get_booking_service(
    session: AsyncSession = Depends(get_async_session),
) -> BookingService:
    """Inject BookingService with session-bound repositories."""

    return BookingService(
        request_repository=AppointmentRequestRepository(session),
        appointment_repository=AppointmentRepository(session),
        patient_repository=PatientRepository(session),
        clinic_repository=ClinicRepository(session),
    )


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


# --- Public Unauthenticated Booking Endpoints ---

@router.get("/booking/branding/{clinic_slug}", response_model=ResponseEnvelope[PublicClinicBrandingResponse])
async def get_public_clinic_branding(
    clinic_slug: str,
    service: BookingServiceDep,
) -> ResponseEnvelope[PublicClinicBrandingResponse]:
    """Public unauthenticated endpoint returning clinic branding details."""

    try:
        result = await service.get_clinic_branding(clinic_slug)
        return ResponseEnvelope(data=result)
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/booking/request", response_model=ResponseEnvelope[AppointmentRequestResponse], status_code=status.HTTP_201_CREATED)
async def create_public_appointment_request(
    payload: AppointmentRequestCreate,
    service: BookingServiceDep,
    clinic_id: Annotated[UUID | None, Query(alias="clinic_id")] = None,
) -> ResponseEnvelope[AppointmentRequestResponse]:
    """Public unauthenticated endpoint to submit an appointment request."""

    target_clinic_id = clinic_id
    if target_clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="clinic_id query parameter is required for public booking request.",
        )

    try:
        request_record = await service.create_request(target_clinic_id, payload)
        return ResponseEnvelope(data=AppointmentRequestResponse.model_validate(request_record))
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BookingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/booking/{id}", response_model=ResponseEnvelope[AppointmentRequestResponse], dependencies=[ProtectedRouterDep])
async def update_booking_request(
    id: UUID,
    payload: AppointmentRequestUpdate,
    clinic: CurrentClinicDep,
    service: BookingServiceDep,
) -> ResponseEnvelope[AppointmentRequestResponse]:
    """Update an appointment request for the authenticated clinic."""

    try:
        req = await service.update_request(clinic.id, id, payload)
        return ResponseEnvelope(data=AppointmentRequestResponse.model_validate(req))
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BookingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/booking/{id}", response_model=ResponseEnvelope[dict[str, str]], dependencies=[ProtectedRouterDep])
async def delete_booking_request(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BookingServiceDep,
) -> ResponseEnvelope[dict[str, str]]:
    """Delete an appointment request for the authenticated clinic."""

    try:
        await service.delete_request(clinic.id, id)
        return ResponseEnvelope(data={"message": "Appointment request deleted successfully."})
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# --- Authenticated Staff Appointment Request Queue Endpoints ---

@router.get("/appointment-requests", response_model=ResponseEnvelope[list[AppointmentRequestResponse]], dependencies=[ProtectedRouterDep])
async def list_appointment_requests(
    clinic: CurrentClinicDep,
    service: BookingServiceDep,
    status_filter: Annotated[AppointmentRequestStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(alias="search")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ResponseEnvelope[list[AppointmentRequestResponse]]:
    """Authenticated staff endpoint listing appointment requests for the clinic."""

    requests = await service.list_requests(
        clinic.id,
        status=status_filter,
        search=search,
        offset=offset,
        limit=limit,
    )
    items = [AppointmentRequestResponse.model_validate(req) for req in requests]
    return ResponseEnvelope(
        data=items,
        meta={"total": len(requests) if len(requests) < limit else len(items) + offset, "offset": offset, "limit": limit}
    )


@router.get("/appointment-requests/{id}", response_model=ResponseEnvelope[AppointmentRequestResponse], dependencies=[ProtectedRouterDep])
async def get_appointment_request(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BookingServiceDep,
) -> ResponseEnvelope[AppointmentRequestResponse]:
    """Authenticated staff endpoint retrieving details of a single appointment request."""

    try:
        req = await service.get_request(clinic.id, id)
        return ResponseEnvelope(data=AppointmentRequestResponse.model_validate(req))
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/appointment-requests/{id}/approve", response_model=ResponseEnvelope[AppointmentRequestApprovalResponse], status_code=status.HTTP_200_OK, dependencies=[ProtectedRouterDep])
async def approve_appointment_request(
    id: UUID,
    payload: AppointmentRequestApprovePayload,
    clinic: CurrentClinicDep,
    service: BookingServiceDep,
) -> ResponseEnvelope[AppointmentRequestApprovalResponse]:
    """Authenticated staff endpoint approving an appointment request and scheduling an appointment."""

    try:
        response = await service.approve_request(clinic.id, id, payload)
        return ResponseEnvelope(data=AppointmentRequestApprovalResponse.model_validate(response))
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BookingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/appointment-requests/{id}/reject", response_model=ResponseEnvelope[AppointmentRequestResponse], status_code=status.HTTP_200_OK, dependencies=[ProtectedRouterDep])
async def reject_appointment_request(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BookingServiceDep,
    notes: Annotated[str | None, Query(alias="notes")] = None,
) -> ResponseEnvelope[AppointmentRequestResponse]:
    """Authenticated staff endpoint rejecting an appointment request."""

    try:
        rejected_req = await service.reject_request(clinic.id, id, notes=notes)
        return ResponseEnvelope(data=AppointmentRequestResponse.model_validate(rejected_req))
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
