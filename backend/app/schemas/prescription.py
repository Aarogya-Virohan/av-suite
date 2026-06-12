from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime
from app.schemas.exercise import ExerciseRead

class PrescriptionItemCreate(BaseModel):
    exercise_id: uuid.UUID
    sets: int = 1
    reps: int = 10
    hold: int = 0
    frequency: str = "Daily"
    hold_angle: Optional[int] = None
    note: Optional[str] = None

class PrescriptionItemRead(BaseModel):
    id: uuid.UUID
    prescription_id: uuid.UUID
    exercise_id: uuid.UUID
    sets: int
    reps: int
    hold: int
    frequency: str
    hold_angle: Optional[int]
    note: Optional[str]
    created_at: datetime
    updated_at: datetime
    exercise: Optional[ExerciseRead] = None

    model_config = ConfigDict(from_attributes=True)

class PrescriptionCreate(BaseModel):
    patient_id: uuid.UUID
    physio_notes: Optional[str] = None
    status: str = "active"
    items: List[PrescriptionItemCreate]

class PrescriptionRead(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    physio_id: uuid.UUID
    physio_notes: Optional[str]
    status: str
    pdf_key: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: List[PrescriptionItemRead]

    model_config = ConfigDict(from_attributes=True)

class PrescriptionItemPatch(BaseModel):
    sets: Optional[int] = None
    reps: Optional[int] = None
    hold: Optional[int] = None
    frequency: Optional[str] = None
    hold_angle: Optional[int] = None
    note: Optional[str] = None

class PrescriptionPatch(BaseModel):
    physio_notes: Optional[str] = None
    status: Optional[str] = None
    items: Optional[List[PrescriptionItemCreate]] = None
