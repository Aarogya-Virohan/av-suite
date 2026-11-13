from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from app.core.security import check_password_byte_length


class RegisterRequest(BaseModel):
    clinic_name: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        return check_password_byte_length(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    clinic_id: UUID | None = None


class WorkspaceSwitchRequest(BaseModel):
    clinic_id: UUID

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


from uuid import UUID
from typing import Optional, Dict

class UserInfoResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    is_active: bool

class ClinicInfoResponse(BaseModel):
    id: UUID
    name: str
    slug: Optional[str] = None
    branding_logo_url: Optional[str] = None
    branding_color: Optional[str] = None

class AuthMeResponse(BaseModel):
    user: UserInfoResponse
    clinic: ClinicInfoResponse
    capabilities: Dict[str, str]

