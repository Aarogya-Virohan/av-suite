from pydantic import BaseModel, ConfigDict
import uuid
from typing import Optional
from datetime import datetime

class ExerciseBase(BaseModel):
    title: str
    description: Optional[str] = None
    body_part: Optional[str] = None
    is_free: bool = False
    video_url: Optional[str] = None

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseRead(ExerciseBase):
    id: uuid.UUID
    clinic_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
