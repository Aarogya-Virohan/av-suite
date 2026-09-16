from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Treatment Session Schemas ---

class TreatmentSessionBase(BaseModel):
    """Base fields for Treatment Session."""

    patient_id: UUID
    appointment_id: UUID | None = None
    therapist_id: UUID
    treatment_date: datetime
    pain_score: int | None = Field(default=None, ge=0, le=10)
    treatment: str
    home_advice: str | None = None
    notes: str | None = None
    finalized: bool = False


class TreatmentSessionCreate(TreatmentSessionBase):
    """Payload for creating a Treatment Session."""

    pass


class TreatmentSessionUpdate(BaseModel):
    """Payload for updating a Treatment Session."""

    appointment_id: UUID | None = None
    therapist_id: UUID | None = None
    treatment_date: datetime | None = None
    pain_score: int | None = Field(default=None, ge=0, le=10)
    treatment: str | None = None
    home_advice: str | None = None
    notes: str | None = None
    finalized: bool | None = None


class TreatmentSessionResponse(TreatmentSessionBase):
    """Response model for Treatment Session."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    created_at: datetime
    updated_at: datetime


class TreatmentSessionListResponse(BaseModel):
    """Paginated list response for Treatment Sessions."""

    items: list[TreatmentSessionResponse]
    total: int
    offset: int
    limit: int


# --- SOAP Assessment Schemas ---

class SoapAssessmentBase(BaseModel):
    """Base fields for SOAP Assessment."""

    patient_id: UUID
    appointment_id: UUID | None = None
    therapist_id: UUID | None = None
    specialty: str
    diagnosis: str | None = None
    is_reassessment: bool = False
    finalized: bool = False
    form_data: dict[str, Any] = Field(default_factory=dict)


class SoapAssessmentCreate(SoapAssessmentBase):
    """Payload for creating a SOAP Assessment."""

    pass


class SoapAssessmentUpdate(BaseModel):
    """Payload for updating a SOAP Assessment."""

    appointment_id: UUID | None = None
    therapist_id: UUID | None = None
    specialty: str | None = None
    diagnosis: str | None = None
    is_reassessment: bool | None = None
    finalized: bool | None = None
    form_data: dict[str, Any] | None = None


class SoapAssessmentResponse(SoapAssessmentBase):
    """Response model for SOAP Assessment."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    created_at: datetime
    updated_at: datetime


class SoapAssessmentListResponse(BaseModel):
    """Paginated list response for SOAP Assessments."""

    items: list[SoapAssessmentResponse]
    total: int
    offset: int
    limit: int
