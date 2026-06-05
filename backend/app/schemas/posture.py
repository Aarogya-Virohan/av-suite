from pydantic import BaseModel, ConfigDict
import uuid
from typing import Optional, List
from datetime import datetime

# -------------------------
# PostureMeasurement Schemas
# -------------------------
class PostureMeasurementBase(BaseModel):
    metric_name: str
    value: float
    unit: Optional[str] = None
    severity: Optional[str] = None
    visibility: Optional[str] = None
    notes: Optional[str] = None

class PostureMeasurementCreate(PostureMeasurementBase):
    pass

class PostureMeasurementRead(PostureMeasurementBase):
    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# -------------------------
# PostureSession Schemas
# -------------------------
class PostureSessionBase(BaseModel):
    patient_id: uuid.UUID
    overall_confidence: Optional[float] = None
    annotated_front_image: Optional[str] = None
    annotated_back_image: Optional[str] = None
    annotated_left_image: Optional[str] = None
    annotated_right_image: Optional[str] = None

class PostureSessionCreate(PostureSessionBase):
    measurements: List[PostureMeasurementCreate] = []

class PostureSessionRead(PostureSessionBase):
    id: uuid.UUID
    clinic_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    measurements: List[PostureMeasurementRead] = []

    model_config = ConfigDict(from_attributes=True)
