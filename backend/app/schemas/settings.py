from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

from app.enums.clinic import ClinicPlanTier


class ClinicSettingsResponse(BaseModel):
    """Schema representing clinic branding and configuration settings."""

    id: UUID
    name: str = Field(..., description="Clinic organization name.")
    branding_logo_url: str | None = Field(default=None, description="URL of clinic logo image asset.")
    client_type: Literal["clinic", "hospital", "home_care"] = "clinic"
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
    client_type: Literal["clinic", "hospital", "home_care"] = "clinic"
    branding_color: str | None = Field(default=None, max_length=32, description="Updated branding color hex string.")
    is_documents_enabled: bool | None = Field(default=None, description="Toggle document storage bucket on/off.")
    # Lengths match the database columns (models/clinic.py); longer values
    # used to reach the database and return 500 (L-43). The address column is
    # Text; 500 matches the CRM Settings field.
    address_line: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    pincode: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    registration_number: str | None = Field(default=None, max_length=120)
    gstin: str | None = None
    authorised_person: str | None = Field(default=None, max_length=255)

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


FeeCategory = Literal["consultation", "posture", "exercise_rx", "custom"]
SORT_ORDER_MAX = 10_000


def _clean_fee_name(value: str | None) -> str | None:
    """Trim the name; a name of only spaces is empty."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("name cannot be blank")
    return value


class ClinicFeeItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: FeeCategory
    default_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    price_editable: bool = True
    # sort_order is an INTEGER column; bound it so a large number is a 422,
    # not a database error (500).
    sort_order: int = Field(default=0, ge=0, le=SORT_ORDER_MAX)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean_fee_name(value)


class ClinicFeeItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: FeeCategory | None = None
    default_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    price_editable: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=SORT_ORDER_MAX)

    @field_validator("name", "category", "default_price", "price_editable", "sort_order")
    @classmethod
    def updates_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("fee item fields cannot be null")
        return value

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return _clean_fee_name(value)


class ClinicFeeItemResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    category: FeeCategory
    default_price: Decimal
    price_editable: bool
    active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
