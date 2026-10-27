"""
Exercise categories (tags) and the links between exercises and categories.

The list of categories is the same for every clinic and is seeded by a
migration from app/services/exercise_categories.py (EL-D-005). An exercise
can carry any number of categories, from any group.
"""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

exercise_category_links = Table(
    "exercise_category_links",
    Base.metadata,
    Column(
        "exercise_id",
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        PGUUID(as_uuid=True),
        ForeignKey("exercise_categories.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class ExerciseCategory(Base):
    __tablename__ = "exercise_categories"
    __table_args__ = (
        UniqueConstraint("group_key", "name", name="uq_exercise_categories_group_name"),
    )

    # Fixed id (uuid5 of group and name), so it is the same on every database.
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    group_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
