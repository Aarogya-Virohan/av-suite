from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

from app.enums.clinic import ClinicPlanTier


class ClinicSettingsResponse(BaseModel):
    """Schema representing clinic branding and configuration settings."""

    id: UUID
    name: str = Field(..., description="Clinic organization name.")
    branding_logo_url: str | None = Field(default=None, description="URL of clinic logo image asset.")
    branding_color: str | None = Field(default=None, description="Primary branding color hex code (e.g. #008080).")
    plan_tier: ClinicPlanTier = Field(..., description="Read-only subscription plan tier.")
    is_partner_clinic: bool = Field(..., description="Read-only partner clinic designation flag.")
    is_documents_enabled: bool = Field(..., description="Whether document storage is enabled for the clinic.")
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    registration_number: str | None = None
    gstin: str | None = None
    authorised_person: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicSettingsUpdate(BaseModel):
    """Schema for updating clinic settings and branding."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Updated clinic name.")
    branding_logo_url: str | None = Field(default=None, description="Updated branding logo URL.")
    branding_color: str | None = Field(default=None, max_length=32, description="Updated branding color hex string.")
    is_documents_enabled: bool | None = Field(default=None, description="Toggle document storage bucket on/off.")
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    registration_number: str | None = None
    gstin: str | None = None
    authorised_person: str | None = None

    @field_validator("pincode")
    @classmethod
    def valid_pincode(cls, value):
        if value is not None and (len(value) != 6 or not value.isdigit()):
            raise ValueError("pincode must contain exactly 6 digits")
        return value

    @field_validator("gstin")
    @classmethod
    def valid_gstin(cls, value):
        if value is not None and len(value) != 15:
            raise ValueError("gstin must contain exactly 15 characters")
        return value
