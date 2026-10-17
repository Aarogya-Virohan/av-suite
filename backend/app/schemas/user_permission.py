from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import ClassVar

from app.enums.permission import CapabilityScope


class UserPermissionBase(BaseModel):
    """Shared properties for user permissions."""
    capability_key: str
    scope: CapabilityScope


class UserPermissionCreate(UserPermissionBase):
    """Payload to create or update a user permission."""
    pass


class UserPermissionRead(UserPermissionBase):
    """Response payload for user permissions."""
    
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)
    
    id: UUID
    clinic_id: UUID
    user_id: UUID
    granted_by: UUID | None
    created_at: datetime
    updated_at: datetime
