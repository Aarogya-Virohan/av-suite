from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

# Item schemas
class PrescriptionItemBase(BaseModel):
    exercise_id: uuid.UUID
    sets: int
    reps: int
    hold: int
    frequency: str
    hold_angle: Optional[float] = None
    note: Optional[str] = None

class PrescriptionItemCreate(PrescriptionItemBase):
    pass

class PrescriptionItemRead(PrescriptionItemBase):
    id: uuid.UUID
    prescription_id: uuid.UUID
    # We could nest exercise details here if needed

    model_config = {"from_attributes": True}

# Prescription schemas
class PrescriptionBase(BaseModel):
    patient_id: uuid.UUID
    physio_notes: Optional[str] = None
    status: str = "draft"

class PrescriptionCreate(PrescriptionBase):
    items: List[PrescriptionItemCreate]

class PrescriptionUpdate(BaseModel):
    physio_notes: Optional[str] = None
    status: Optional[str] = None

class PrescriptionRead(PrescriptionBase):
    id: uuid.UUID
    clinic_id: uuid.UUID
    physio_id: uuid.UUID
    pdf_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[PrescriptionItemRead] = []

    model_config = {"from_attributes": True}
