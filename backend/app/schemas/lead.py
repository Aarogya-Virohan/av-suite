from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums.lead import LeadStage


class LeadBase(BaseModel):
    """Base schema for lead payload data."""

    name: str = Field(..., min_length=1, max_length=255, description="Full name of prospective patient lead.")
    phone: str = Field(..., min_length=1, max_length=50, description="Contact phone number.")
    email: EmailStr | str | None = Field(default=None, max_length=255, description="Contact email address.")
    source: str | None = Field(default=None, max_length=100, description="Lead acquisition source (e.g. google, meta).")
    stage: LeadStage = Field(default=LeadStage.NEW, description="Lifecycle stage of lead.")
    notes: str | None = Field(default=None, max_length=2000, description="Internal notes regarding lead.")


class LeadCreate(LeadBase):
    """Schema for creating a new lead."""

    assigned_to: UUID | None = Field(default=None, description="Assigned staff member user UUID.")


class LeadUpdate(BaseModel):
    """Schema for updating an existing lead."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    stage: LeadStage | None = Field(default=None)
    assigned_to: UUID | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=2000)


class LeadResponse(LeadBase):
    """Schema representing full details of a lead."""

    id: UUID
    clinic_id: UUID
    assigned_to: UUID | None
    converted_patient_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    """Schema representing a paginated list of leads."""

    items: list[LeadResponse]
    total: int
    offset: int
    limit: int


class LeadConvertResponse(BaseModel):
    """Response schema returned after converting a lead into a patient."""

    lead: LeadResponse
    patient_id: UUID
