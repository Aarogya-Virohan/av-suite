from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    patient_name: str | None = None
    therapist_name: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("patient"):
                data["patient_name"] = f"{data['patient']['first_name']} {data['patient']['last_name']}"
            if data.get("therapist"):
                data["therapist_name"] = f"{data['therapist']['first_name']} {data['therapist']['last_name']}"
            return data

        # Check __dict__ to avoid triggering async lazy loads on SQLAlchemy models
        state = getattr(data, "__dict__", {})
        if "patient" in state and state["patient"]:
            data.patient_name = f"{state['patient'].first_name} {state['patient'].last_name}"
        if "therapist" in state and state["therapist"]:
            data.therapist_name = f"{state['therapist'].first_name} {state['therapist'].last_name}"
        return data


class AppointmentListResponse(BaseModel):
    """Paginated list response model for appointments."""

    items: list[AppointmentResponse]
    total: int
    offset: int
    limit: int
