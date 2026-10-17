from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums.document import DocumentCategory


class PatientDocumentBase(BaseModel):
    """Base schema for patient document payload validation."""

    label: str = Field(..., min_length=1, max_length=255, description="Human readable title or document label.")
    file_type: str = Field(..., min_length=1, max_length=100, description="MIME type or file extension.")
    category: DocumentCategory = Field(default=DocumentCategory.OTHER, description="Document classification category.")
    notes: str | None = Field(default=None, max_length=2000, description="Optional notes or observations.")


class PatientDocumentCreate(PatientDocumentBase):
    """Schema for registering a new patient document."""

    patient_id: UUID = Field(..., description="Target patient UUID.")
    treatment_id: UUID | None = Field(default=None, description="Optional linked treatment session UUID.")
    uploaded_by: UUID | None = Field(default=None, description="Optional uploader staff UUID.")
    file_url: str = Field(..., min_length=1, max_length=1024, description="Storage location URL or path.")
    file_size: int | None = Field(default=None, ge=0, description="File size in bytes.")


class PatientDocumentUpdate(BaseModel):
    """Schema for updating an existing document metadata record."""

    label: str | None = Field(default=None, min_length=1, max_length=255)
    category: DocumentCategory | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=2000)


class PatientDocumentResponse(PatientDocumentBase):
    """Schema representing a full patient document record."""

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    treatment_id: UUID | None
    uploaded_by: UUID | None
    file_url: str
    file_size: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientDocumentListResponse(BaseModel):
    """Schema representing a paginated list of patient documents."""

    items: list[PatientDocumentResponse]
    total: int
    offset: int
    limit: int
