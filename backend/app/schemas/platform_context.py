from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.enums.clinic import ClinicType
from app.enums.product import EntitlementSource, EntitlementStatus
from app.enums.user import UserRole


class PlatformUserContext(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    role: UserRole


class WorkspaceContext(BaseModel):
    id: UUID
    name: str
    type: ClinicType
    role: UserRole


class ActiveProductContext(BaseModel):
    key: str
    name: str
    description: str | None
    status: EntitlementStatus
    source: EntitlementSource
    valid_from: datetime | None
    valid_until: datetime | None


class PlatformContextResponse(BaseModel):
    user: PlatformUserContext
    workspaces: list[WorkspaceContext]
    active_workspace: WorkspaceContext | None
    active_products: list[ActiveProductContext]
    capabilities: list[str]
