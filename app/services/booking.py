from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from app.enums.appointment import AppointmentStatus
from app.enums.booking import AppointmentRequestStatus
from app.enums.patient import PatientStatus
from app.models.appointment import Appointment
from app.models.booking import AppointmentRequest
from app.repositories.appointment import AppointmentRepository
from app.repositories.booking import AppointmentRequestRepository
from app.repositories.patient import PatientRepository
from app.schemas.booking import (
    AppointmentRequestApprovePayload,
    AppointmentRequestCreate,
)


class BookingValidationError(Exception):
    """Raised when validation fails for appointment requests or booking operations."""


class BookingNotFoundError(Exception):
    """Raised when an appointment request resource is not found."""


class BookingService:
    """Service managing public appointment requests, approval flows, and clinic branding."""

    request_repository: AppointmentRequestRepository
    appointment_repository: AppointmentRepository
    patient_repository: PatientRepository

    def __init__(
        self,
        request_repository: AppointmentRequestRepository,
        appointment_repository: AppointmentRepository,
        patient_repository: PatientRepository,
    ) -> None:
        """Inject repositories required for booking operations."""

        self.request_repository = request_repository
        self.appointment_repository = appointment_repository
        self.patient_repository = patient_repository

    async def create_request(self, clinic_id: UUID, payload: AppointmentRequestCreate) -> AppointmentRequest:
        """Create a new public appointment request for a clinic."""

        req_data = payload.model_dump()
        req_data.update(
            {
                "clinic_id": clinic_id,
                "status": AppointmentRequestStatus.PENDING,
            }
        )
        return await self.request_repository.create(req_data)

    async def get_request(self, clinic_id: UUID, request_id: UUID) -> AppointmentRequest:
        """Retrieve an appointment request ensuring clinic scoping."""

        req = await self.request_repository.get_by_id(request_id, clinic_id=clinic_id)
        if req is None:
            raise BookingNotFoundError(f"Appointment request '{request_id}' not found for clinic '{clinic_id}'.")
        return req

    async def list_requests(
        self,
        clinic_id: UUID,
        *,
        status: AppointmentRequestStatus | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AppointmentRequest]:
        """List appointment requests for a clinic with optional status and search filters."""

        return await self.request_repository.list_requests(
            clinic_id=clinic_id,
            status=status,
            search=search,
            offset=offset,
            limit=limit,
        )

    async def approve_request(
        self,
        clinic_id: UUID,
        request_id: UUID,
        payload: AppointmentRequestApprovePayload,
    ) -> tuple[AppointmentRequest, Appointment]:
        """Approve an appointment request, ensuring or creating a patient, and scheduling an appointment."""

        req = await self.get_request(clinic_id, request_id)
        if req.status == AppointmentRequestStatus.APPROVED:
            raise BookingValidationError(f"Appointment request '{request_id}' has already been approved.")

        # Find or create patient record
        matching_patients = await self.patient_repository.search_by_phone(req.phone, clinic_id=clinic_id)
        if matching_patients:
            patient = matching_patients[0]
        else:
            patient = await self.patient_repository.create(
                {
                    "clinic_id": clinic_id,
                    "full_name": req.name,
                    "phone": req.phone,
                    "age": req.age,
                    "gender": req.gender,
                    "chief_complaint": req.chief_complaint,
                    "status": PatientStatus.ACTIVE,
                }
            )

        sched_date = payload.scheduled_date or req.preferred_date or date.today()
        start_t = time(hour=9, minute=0)
        if payload.start_time:
            try:
                parts = [int(p) for p in payload.start_time.split(":")]
                start_t = time(hour=parts[0], minute=parts[1], second=parts[2] if len(parts) > 2 else 0)
            except (ValueError, IndexError):
                start_t = time(hour=9, minute=0)

        start_dt = datetime.combine(sched_date, start_t, tzinfo=timezone.utc)

        appointment_data = {
            "clinic_id": clinic_id,
            "patient_id": patient.id,
            "therapist_id": payload.therapist_id,
            "scheduled_date": start_dt,
            "status": AppointmentStatus.SCHEDULED,
            "notes": payload.notes or req.notes,
        }
        appointment = await self.appointment_repository.create(appointment_data)

        updated_req = await self.request_repository.update(
            req,
            {"status": AppointmentRequestStatus.APPROVED},
        )

        return updated_req, appointment

    async def reject_request(
        self, clinic_id: UUID, request_id: UUID, notes: str | None = None
    ) -> AppointmentRequest:
        """Reject an appointment request while preserving the request record."""

        req = await self.get_request(clinic_id, request_id)
        update_data: dict[str, object] = {"status": AppointmentRequestStatus.REJECTED}
        if notes:
            update_data["notes"] = f"{req.notes or ''}\nRejection notes: {notes}".strip()

        return await self.request_repository.update(req, update_data)
