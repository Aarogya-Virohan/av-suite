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
    # Category ids (GET /exercises/categories). Omitted or empty: none.
    category_ids: Optional[list[uuid.UUID]] = None

class ExerciseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    body_part: Optional[str] = None
    is_free: Optional[bool] = None
    video_url: Optional[str] = None
    # Omitted: categories unchanged. A list (also empty) replaces them.
    category_ids: Optional[list[uuid.UUID]] = None

class ExerciseCategoryRef(BaseModel):
    """One category an exercise carries (EL-D-005)."""

    id: uuid.UUID
    group_key: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class ExercisePhotoInfo(BaseModel):
    """One of the caller's clinic photos for an exercise. The image itself is
    served by GET /exercises/{id}/photos/{angle}; updated_at changes on every
    upload, so clients can use it to refresh a cached copy."""

    angle: str
    width: int
    height: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExerciseRead(ExerciseBase):
    id: uuid.UUID
    clinic_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    # The caller's clinic photos (front, side). Filled by the list and detail
    # endpoints; empty elsewhere (EL-D-004).
    photos: list[ExercisePhotoInfo] = []
    # Categories in filter panel order. Filled by the list, detail, create and
    # update endpoints; empty elsewhere (EL-D-005).
    categories: list[ExerciseCategoryRef] = []

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
