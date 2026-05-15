from pydantic import BaseModel, ConfigDict
import uuid
from typing import Optional
from datetime import date, datetime

class PatientBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None

class PatientCreate(PatientBase):
    user_id: Optional[uuid.UUID] = None

class PatientRead(PatientBase):
    id: uuid.UUID
    clinic_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
