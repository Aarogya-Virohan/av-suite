from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from typing import List, Optional
import uuid
from datetime import datetime

class PostureMeasurementCreate(BaseModel):
    metric_name: str = Field(validation_alias=AliasChoices("metric_name", "param_id"))
    value: float = Field(validation_alias=AliasChoices("value", "raw_value"))
    unit: Optional[str] = None
    notes: Optional[str] = None
    severity: Optional[str] = None
    visibility: Optional[str] = None

class PostureSessionCreate(BaseModel):
    patient_id: uuid.UUID
    overall_confidence: Optional[float] = None
    annotated_front_image: Optional[str] = None
    annotated_back_image: Optional[str] = None
    annotated_side_image: Optional[str] = None
    measurements: List[PostureMeasurementCreate]

class PostureMeasurementRead(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    metric_name: str
    value: float
    unit: Optional[str]
    notes: Optional[str]
    severity: Optional[str]
    visibility: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PostureSessionRead(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    patient_id: uuid.UUID
    overall_confidence: Optional[float]
    annotated_front_image: Optional[str]
    annotated_back_image: Optional[str]
    annotated_side_image: Optional[str]
    created_at: datetime
    updated_at: datetime
    measurements: List[PostureMeasurementRead]

    model_config = ConfigDict(from_attributes=True)
