from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.security import check_password_byte_length
from app.enums.user import UserRole, normalize_user_role


class UserBase(BaseModel):
    """Shared user fields for CRM API contracts."""

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    role: UserRole
    is_active: bool = True

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: object) -> UserRole:
        """Normalize SRS and AV Suite role values to the canonical CRM enum."""

        if not isinstance(value, (str, UserRole)):
            raise ValueError("Unsupported user role")

        return normalize_user_role(value)


class UserCreate(UserBase):
    """User creation payload with AV Suite first/last name compatibility."""

    name: str = Field(default="", max_length=255)
    password: str = Field(min_length=8, max_length=128)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    # BE-1: tool checkboxes to switch on for the new user. None / [] = none.
    # Keys: "psycho-social-screening", "exercise-library", "posture-tool".
    tools: list[str] | None = None

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        return check_password_byte_length(value)

    @model_validator(mode="after")
    def apply_name_compatibility(self) -> Self:
        """Populate the SRS name field from AV Suite first/last fields when provided."""

        canonical_name = self.name.strip()
        if canonical_name:
            self.name = canonical_name
            return self

        name_parts = [name_part.strip() for name_part in (self.first_name, self.last_name) if name_part]
        if not name_parts:
            raise ValueError("name or first_name/last_name is required")

        self.name = " ".join(name_parts)
        return self


class UserUpdate(BaseModel):
    """User update payload."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: object) -> UserRole | None:
        """Normalize optional SRS and AV Suite role values."""

        if value is None:
            return None

        if not isinstance(value, (str, UserRole)):
            raise ValueError("Unsupported user role")

        return normalize_user_role(value)


class UserRead(UserBase):
    """User response payload."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    # BE-1: tool checkbox state per tool key (effective, role template included).
    tools: dict[str, bool] | None = None
    created_at: datetime
    updated_at: datetime


class UserToolsUpdate(BaseModel):
    """BE-1: PUT /users/{id}/tools. Exactly these tools end up on; others off."""

    tools: list[str]


class UserToolsRead(BaseModel):
    """BE-1: checkbox state for one user plus what the clinic plan allows."""

    user_id: UUID
    role: UserRole
    tools: dict[str, bool]
    available: dict[str, bool]
    labels: dict[str, str]
