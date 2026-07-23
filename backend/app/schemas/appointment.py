from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums.appointment import AppointmentSource, AppointmentStatus


class AppointmentBase(BaseModel):
    """Shared appointment fields for API contracts."""

    patient_id: UUID
    therapist_id: UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, gt=0)
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    source: AppointmentSource = AppointmentSource.MANUAL


class AppointmentCreate(AppointmentBase):
    """Payload for creating a new appointment."""

    patient_id: UUID
    therapist_id: UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, gt=0)


class AppointmentUpdate(BaseModel):
    """Payload for updating an existing appointment."""

    patient_id: UUID | None = None
    therapist_id: UUID | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    status: AppointmentStatus | None = None
    source: AppointmentSource | None = None


class AppointmentResponse(AppointmentBase):
    """Response model for an appointment."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    created_at: datetime
    updated_at: datetime


class AppointmentListResponse(BaseModel):
    """Paginated list response model for appointments."""

    items: list[AppointmentResponse]
    total: int
    offset: int
    limit: int
