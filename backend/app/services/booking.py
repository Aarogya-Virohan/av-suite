from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from app.enums.appointment import AppointmentSource, AppointmentStatus
from app.enums.booking import AppointmentRequestStatus
from app.enums.patient import PatientStatus
from app.models.appointment import Appointment
from app.models.booking import AppointmentRequest
from app.repositories.appointment import AppointmentRepository
from app.repositories.booking import AppointmentRequestRepository
from app.repositories.clinic import ClinicRepository
from app.repositories.patient import PatientRepository
from app.schemas.booking import (
    AppointmentRequestApprovePayload,
    AppointmentRequestCreate,
    AppointmentRequestResponse,
    AppointmentRequestUpdate,
    PublicClinicBrandingResponse,
)
from app.utils.whatsapp import build_whatsapp_link


class BookingValidationError(Exception):
    """Raised when validation fails for appointment requests or booking operations."""


class BookingNotFoundError(Exception):
    """Raised when an appointment request or clinic resource is not found."""


class BookingService:
    """Service managing public appointment requests, approval flows, and clinic branding."""

    request_repository: AppointmentRequestRepository
    appointment_repository: AppointmentRepository
    patient_repository: PatientRepository
    clinic_repository: ClinicRepository

    def __init__(
        self,
        request_repository: AppointmentRequestRepository,
        appointment_repository: AppointmentRepository,
        patient_repository: PatientRepository,
        clinic_repository: ClinicRepository,
    ) -> None:
        """Inject repositories required for booking operations."""

        self.request_repository = request_repository
        self.appointment_repository = appointment_repository
        self.patient_repository = patient_repository
        self.clinic_repository = clinic_repository

    async def get_clinic_branding(
        self, clinic_slug_or_id: str
    ) -> PublicClinicBrandingResponse:
        """Retrieve public branding details for a clinic without exposing patient or internal data."""

        clinic = await self.clinic_repository.get_by_slug_or_id(clinic_slug_or_id)
        if clinic is None:
            raise BookingNotFoundError(f"Clinic '{clinic_slug_or_id}' not found.")

        return PublicClinicBrandingResponse(
            clinic_id=clinic.id,
            name=clinic.name,
            slug=clinic_slug_or_id,
            logo_url=clinic.branding_logo_url,
            brand_color=clinic.branding_color,
        )

    async def create_request(
        self, clinic_id: UUID, payload: AppointmentRequestCreate
    ) -> AppointmentRequest:
        """Create a new public appointment request for a clinic."""

        clinic = await self.clinic_repository.get_by_id(clinic_id)
        if clinic is None:
            raise BookingNotFoundError(f"Clinic '{clinic_id}' does not exist.")

        req_data = payload.model_dump()
        req_data.update(
            {
                "clinic_id": clinic_id,
                "status": AppointmentRequestStatus.PENDING,
            }
        )
        req = await self.request_repository.create(req_data)
        await self.request_repository.session.commit()
        return req

    async def get_request(
        self, clinic_id: UUID, request_id: UUID
    ) -> AppointmentRequest:
        """Retrieve an appointment request ensuring clinic scoping."""

        req = await self.request_repository.get_by_id(request_id, clinic_id=clinic_id)
        if req is None:
            raise BookingNotFoundError(
                f"Appointment request '{request_id}' not found for clinic '{clinic_id}'."
            )
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

    @staticmethod
    def _build_approval_message(patient_name: str, scheduled_at: datetime) -> str:
        """Format the WhatsApp confirmation message for an approved appointment."""

        return (
            f"Hello {patient_name},\n\n"
            "Your appointment has been confirmed.\n\n"
            f"Date: {scheduled_at.strftime('%d %b %Y')}\n"
            f"Time: {scheduled_at.strftime('%I:%M %p')}\n\n"
            "Thank you."
        )

    async def approve_request(
        self,
        clinic_id: UUID,
        request_id: UUID,
        payload: AppointmentRequestApprovePayload,
    ) -> dict[str, object]:
        """Approve an appointment request, ensuring or creating a patient, and scheduling an appointment."""

        req = await self.get_request(clinic_id, request_id)
        if req.status == AppointmentRequestStatus.APPROVED:
            raise BookingValidationError(
                f"Appointment request '{request_id}' has already been approved."
            )

        # Find or create patient record
        matching_patients = await self.patient_repository.search_by_phone(
            req.phone, clinic_id=clinic_id
        )
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
                start_t = time(
                    hour=parts[0],
                    minute=parts[1],
                    second=parts[2] if len(parts) > 2 else 0,
                )
            except (ValueError, IndexError):
                start_t = time(hour=9, minute=0)

        start_dt = datetime.combine(sched_date, start_t, tzinfo=timezone.utc)

        therapist_id = payload.therapist_id
        if therapist_id is None:
            # Note: therapist_id is required on Appointment ORM model, fallback to placeholder if not supplied
            therapist_id = UUID("00000000-0000-0000-0000-000000000000")

        appointment_data = {
            "clinic_id": clinic_id,
            "patient_id": patient.id,
            "therapist_id": therapist_id,
            "scheduled_at": start_dt,
            "duration_minutes": 30,
            "status": AppointmentStatus.SCHEDULED,
            "source": AppointmentSource.PUBLIC_BOOKING,
        }
        appointment = await self.appointment_repository.create(appointment_data)

        updated_req = await self.request_repository.update(
            req,
            {"status": AppointmentRequestStatus.APPROVED},
        )
        await self.request_repository.session.commit()

        patient_name = getattr(patient, "full_name", req.name)
        whatsapp_link = build_whatsapp_link(
            req.phone,
            self._build_approval_message(patient_name, appointment.scheduled_at),
        )

        return {
            "request": AppointmentRequestResponse.model_validate(
                updated_req
            ).model_dump(mode="json"),
            "appointment_id": str(appointment.id),
            "patient_id": str(appointment.patient_id),
            "message": "Appointment request approved successfully.",
            "whatsapp_link": whatsapp_link,
        }

    async def reject_request(
        self, clinic_id: UUID, request_id: UUID, notes: str | None = None
    ) -> AppointmentRequest:
        """Reject an appointment request while preserving the request record."""

        req = await self.get_request(clinic_id, request_id)
        update_data: dict[str, object] = {"status": AppointmentRequestStatus.REJECTED}
        if notes:
            update_data["notes"] = (
                f"{req.notes or ''}\nRejection notes: {notes}".strip()
            )

        updated = await self.request_repository.update(req, update_data)
        await self.request_repository.session.commit()
        return updated

    async def update_request(
        self,
        clinic_id: UUID,
        request_id: UUID,
        payload: AppointmentRequestUpdate,
    ) -> AppointmentRequest:
        """Update appointment request fields for a clinic-scoped request."""

        request_obj = await self.get_request(clinic_id, request_id)
        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            return request_obj

        updated = await self.request_repository.update_request_by_id(
            clinic_id=clinic_id,
            request_id=request_id,
            update_data=update_data,
        )
        if updated is None:
            raise BookingNotFoundError(
                f"Appointment request '{request_id}' not found for clinic '{clinic_id}'."
            )

        await self.request_repository.session.commit()
        return updated

    async def delete_request(self, clinic_id: UUID, request_id: UUID) -> None:
        """Delete appointment request for the clinic."""

        request_obj = await self.get_request(clinic_id, request_id)
        await self.request_repository.delete_request(request_obj)
        await self.request_repository.session.commit()
