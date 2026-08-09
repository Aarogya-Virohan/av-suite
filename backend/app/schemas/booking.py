from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums.booking import AppointmentRequestStatus


class AppointmentRequestBase(BaseModel):
    """Base schema for public booking appointment request data."""

    name: str = Field(..., min_length=1, max_length=255, description="Full name of requesting patient.")
    phone: str = Field(..., min_length=1, max_length=50, description="Contact phone number.")
    age: int | None = Field(default=None, ge=0, le=150, description="Patient age.")
    gender: str | None = Field(default=None, max_length=20, description="Patient gender.")
    chief_complaint: str | None = Field(default=None, max_length=2000, description="Chief medical complaint.")
    notes: str | None = Field(default=None, max_length=2000, description="Additional notes or preferences.")
    preferred_date: date | None = Field(default=None, description="Preferred appointment date.")
    preferred_slot: str | None = Field(default=None, max_length=50, description="Preferred time slot e.g. morning/afternoon.")


class AppointmentRequestCreate(AppointmentRequestBase):
    """Schema for submitting a public appointment request."""


class AppointmentRequestUpdate(BaseModel):
    """Schema for updating an appointment request status or notes."""

    status: AppointmentRequestStatus | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentRequestApprovePayload(BaseModel):
    """Payload for approving an appointment request and scheduling an appointment."""

    therapist_id: UUID | None = Field(default=None, description="Assigned therapist staff user UUID.")
    scheduled_date: date | None = Field(default=None, description="Confirmed appointment date.")
    start_time: str | None = Field(default=None, description="Confirmed start time (HH:MM:SS format).")
    notes: str | None = Field(default=None, max_length=2000, description="Staff notes.")


class AppointmentRequestResponse(AppointmentRequestBase):
    """Schema representing a complete appointment request record."""

    id: UUID
    clinic_id: UUID
    status: AppointmentRequestStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentRequestListResponse(BaseModel):
    """Schema representing a paginated list of appointment requests."""

    items: list[AppointmentRequestResponse]
    total: int
    offset: int
    limit: int


class AppointmentRequestApprovalResponse(BaseModel):
    """Schema representing an approved booking response with WhatsApp deep link."""

    request: AppointmentRequestResponse
    appointment_id: str
    patient_id: str
    message: str
    whatsapp_link: str


class PublicClinicBrandingResponse(BaseModel):
    """Schema for public unauthenticated clinic branding endpoint."""

    clinic_id: UUID
    name: str
    slug: str | None = None
    logo_url: str | None = None
    brand_color: str | None = None
