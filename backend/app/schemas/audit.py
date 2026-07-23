from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogCreate(BaseModel):
    """Schema for creating a new audit log entry."""

    user_id: UUID | None = Field(default=None, description="UUID of user executing action.")
    action: str = Field(..., min_length=1, max_length=100, description="Action performed (e.g. create, update, delete, payment).")
    entity_type: str = Field(..., min_length=1, max_length=100, description="Target entity type (e.g. patient, appointment, invoice).")
    entity_id: UUID | None = Field(default=None, description="Target entity UUID.")
    details: dict[str, Any] | None = Field(default=None, description="JSON metadata detailing action context.")


class AuditLogResponse(BaseModel):
    """Schema representing an audit log entry."""

    id: UUID
    clinic_id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    details: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Schema representing a paginated list of audit logs."""

    items: list[AuditLogResponse]
    total: int
    offset: int
    limit: int
