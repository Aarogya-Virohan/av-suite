from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums.patient import PatientStatus


class PatientBase(BaseModel):
    """Shared patient fields for CRM API payloads."""

    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = Field(default=None, max_length=32)
    chief_complaint: str | None = None
    referral_source: str | None = Field(default=None, max_length=255)
    status: PatientStatus = PatientStatus.ACTIVE


class PatientCreate(PatientBase):
    """Patient creation payload."""

    full_name: str = Field(min_length=1, max_length=255)


class PatientUpdate(BaseModel):
    """Patient update payload."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = Field(default=None, max_length=32)
    chief_complaint: str | None = None
    referral_source: str | None = Field(default=None, max_length=255)
    status: PatientStatus | None = None


class PatientResponse(PatientBase):
    """Patient response payload."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    """Paginated list response payload for patients."""

    items: list[PatientResponse]
    total: int
    offset: int
    limit: int
