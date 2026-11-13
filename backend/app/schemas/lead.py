from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums.lead import LeadStage, LeadSource, LeadLostReason
from pydantic import model_validator


class LeadBase(BaseModel):
    """Base schema for lead payload data."""

    name: str = Field(..., min_length=1, max_length=255, description="Full name of prospective patient lead.")
    phone: str = Field(..., min_length=1, max_length=50, description="Contact phone number.")
    email: EmailStr | str | None = Field(default=None, max_length=255, description="Contact email address.")
    source: LeadSource | None = Field(default=None, description="Lead acquisition source.")
    stage: LeadStage = Field(default=LeadStage.NEW, description="Lifecycle stage of lead.")
    notes: str | None = Field(default=None, max_length=2000, description="Internal notes regarding lead.")
    lost_reason: LeadLostReason | None = None
    lost_remark: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_lost_reason_remark(self):
        if self.stage == LeadStage.LOST and self.lost_reason == LeadLostReason.OTHER and not self.lost_remark:
            raise ValueError("lost_remark is required when lost_reason is 'other'")
        return self


class LeadCreate(LeadBase):
    """Schema for creating a new lead."""

    assigned_to: UUID | None = Field(default=None, description="Assigned staff member user UUID.")


class LeadUpdate(BaseModel):
    """Schema for updating an existing lead."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | str | None = Field(default=None, max_length=255)
    source: LeadSource | None = Field(default=None)
    stage: LeadStage | None = Field(default=None)
    assigned_to: UUID | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=2000)
    lost_reason: LeadLostReason | None = None
    lost_remark: str | None = Field(default=None, max_length=500)


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
