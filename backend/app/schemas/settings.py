from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

from app.enums.clinic import ClinicPlanTier
from app.services.clinic_code import normalize_clinic_code


LogoBgMode = Literal["as_is", "white", "transparent"]
_WEBSITE = re.compile(r"^(https?://)?([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(:[0-9]{1,5})?(/[^\s]*)?$", re.I)


def clean_website(value: str | None) -> str | None:
    """"www.clinic.in", "clinic.in/about" or a full http(s) link; blank = none."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not _WEBSITE.match(value):
        raise ValueError("Enter a website like www.yourclinic.in")
    return value


class LogoPreviewRequest(BaseModel):
    """A logo picked in Settings, before it is saved."""

    logo: str = Field(..., description="The picked file as a data URI.")
    logo_bg_mode: LogoBgMode = "as_is"


class LogoPreviewResponse(BaseModel):
    logo: str = Field(..., description="The copy that would be stored (resized, data URI).")
    letterhead_logo: str = Field(..., description="The logo as the report band shows it in this mode.")
    width: int
    height: int
    low_contrast: bool


class ClinicSettingsResponse(BaseModel):
    """Schema representing clinic branding and configuration settings."""

    id: UUID
    name: str = Field(..., description="Clinic organization name.")
    branding_logo_url: str | None = Field(default=None, description="URL of clinic logo image asset.")
    client_type: Literal["clinic", "hospital", "home_care"] = "clinic"
    code: str = Field(..., description="Prefix of the Patient ID, e.g. ADP in ADP-000003.")
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
    display_doctor_name: str | None = Field(
        default=None, description="Doctor name in the clinical report header; empty = clinic owner admin's name."
    )
    website: str | None = Field(default=None, description="Shown in the clinic block above the report footer.")
    logo_bg_mode: LogoBgMode = Field(default="as_is", description="How the logo background shows on the report band.")
    logo_low_contrast: bool = Field(
        default=False, description="The logo is hard to see on the report band in the chosen mode (Settings warning)."
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicSettingsUpdate(BaseModel):
    """Schema for updating clinic settings and branding."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Updated clinic name.")
    branding_logo_url: str | None = Field(default=None, description="Updated branding logo URL.")
    client_type: Literal["clinic", "hospital", "home_care"] = "clinic"
    code: str | None = Field(
        default=None,
        description="Prefix of the Patient ID: 1 to 6 capital letters or digits. Must be unused by other clinics.",
    )
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
    display_doctor_name: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    logo_bg_mode: LogoBgMode | None = None

    @field_validator("display_doctor_name")
    @classmethod
    def clean_doctor(cls, value):
        if value is None:
            return None
        return value.strip() or None

    @field_validator("website")
    @classmethod
    def valid_website(cls, value):
        return clean_website(value)

    @field_validator("logo_bg_mode", mode="before")
    @classmethod
    def mode_not_null(cls, value):
        if value is None:
            raise ValueError("logo_bg_mode must be as_is, white or transparent")
        return value

    @field_validator("code", mode="before")
    @classmethod
    def valid_code(cls, value):
        # Omitted = unchanged (exclude_unset). An explicit null or blank is an error.
        return normalize_clinic_code(value if isinstance(value, str) else "")

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
