from pydantic import BaseModel, ConfigDict, field_validator
import re
import uuid
from typing import Optional
from datetime import date, datetime

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'-]{0,99}$")
PHONE_PATTERN = re.compile(r"^[0-9]{10}$")


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if not NAME_PATTERN.match(v):
            raise ValueError(
                "Name may only contain letters, spaces, hyphens, apostrophes, and periods"
            )
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.strip()
        if not PHONE_PATTERN.match(v):
            raise ValueError("Phone number must be exactly 10 digits")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if v.year < date.today().year - 130:
            raise ValueError("Date of birth is not valid")
        return v

class PatientCreate(PatientBase):
    user_id: Optional[uuid.UUID] = None

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    user_id: Optional[uuid.UUID] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if not NAME_PATTERN.match(v):
            raise ValueError(
                "Name may only contain letters, spaces, hyphens, apostrophes, and periods"
            )
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.strip()
        if not PHONE_PATTERN.match(v):
            raise ValueError("Phone number must be exactly 10 digits")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if v.year < date.today().year - 130:
            raise ValueError("Date of birth is not valid")
        return v


class PatientRead(PatientBase):
    id: uuid.UUID
    clinic_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
