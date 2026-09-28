from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    clinic_name: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

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
    branding_logo_url: Optional[str] = None
    branding_color: Optional[str] = None

class AuthMeResponse(BaseModel):
    user: UserInfoResponse
    clinic: ClinicInfoResponse
    capabilities: Dict[str, str]

