from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums.clinic import ClinicPlanTier


class ClinicSettingsResponse(BaseModel):
    """Schema representing clinic branding and configuration settings."""

    id: UUID
    name: str = Field(..., description="Clinic organization name.")
    branding_logo_url: str | None = Field(default=None, description="URL of clinic logo image asset.")
    branding_color: str | None = Field(default=None, description="Primary branding color hex code (e.g. #008080).")
    plan_tier: ClinicPlanTier = Field(..., description="Read-only subscription plan tier.")
    is_partner_clinic: bool = Field(..., description="Read-only partner clinic designation flag.")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicSettingsUpdate(BaseModel):
    """Schema for updating clinic settings and branding."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Updated clinic name.")
    branding_logo_url: str | None = Field(default=None, max_length=2048, description="Updated branding logo URL.")
    branding_color: str | None = Field(default=None, max_length=32, description="Updated branding color hex string.")
