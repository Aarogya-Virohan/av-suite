from pydantic import BaseModel, ConfigDict, computed_field
import uuid
from typing import Optional
from datetime import datetime

from app.services import exercise_media

class ExerciseBase(BaseModel):
    title: str
    description: Optional[str] = None
    body_part: Optional[str] = None
    is_free: bool = False
    video_url: Optional[str] = None

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    body_part: Optional[str] = None
    is_free: Optional[bool] = None
    video_url: Optional[str] = None

class ExerciseRead(ExerciseBase):
    id: uuid.UUID
    clinic_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    # Read-only, worked out from video_url (EL-D-003). video_url itself is
    # unchanged, so existing clients keep working.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_url(self) -> Optional[str]:
        return exercise_media.image_url(self.video_url)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def demo_video_url(self) -> Optional[str]:
        return exercise_media.demo_video_url(self.video_url)
