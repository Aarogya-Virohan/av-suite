import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.exercise import ExerciseRead

MAX_TEMPLATE_ITEMS = 50


class TemplateItemIn(BaseModel):
    exercise_id: uuid.UUID
    # Same bounds as PrescriptionItemCreate, since a template fills a prescription.
    sets: int = Field(default=1, ge=1, le=20)
    reps: int = Field(default=10, ge=1, le=200)
    hold: int = Field(default=0, ge=0, le=600)
    frequency: str = Field(default="Daily", min_length=1, max_length=100)
    note: Optional[str] = Field(default=None, max_length=1000)


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    items: List[TemplateItemIn] = Field(min_length=1, max_length=MAX_TEMPLATE_ITEMS)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("description")
    @classmethod
    def _blank_description_is_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("items")
    @classmethod
    def _no_repeats(cls, v: List[TemplateItemIn]) -> List[TemplateItemIn]:
        ids = [i.exercise_id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("An exercise can be in a template only once")
        return v


class TemplateItemRead(BaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    position: int
    sets: int
    reps: int
    hold: int
    frequency: str
    note: Optional[str]
    exercise: Optional[ExerciseRead] = None

    model_config = ConfigDict(from_attributes=True)


class TemplateRead(BaseModel):
    id: uuid.UUID
    clinic_id: Optional[uuid.UUID]
    name: str
    description: Optional[str]
    is_global: bool = False
    created_at: datetime
    updated_at: datetime
    items: List[TemplateItemRead]

    model_config = ConfigDict(from_attributes=True)
