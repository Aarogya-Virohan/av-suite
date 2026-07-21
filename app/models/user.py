from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.common.base import Base
from app.common.mixins import TimestampMixin, UUIDMixin
from app.enums.user import UserRole
from app.models.clinic import Clinic


def _user_role_values(enum_cls: type[UserRole]) -> list[str]:
    """Return database enum values for user roles."""

    return [member.value for member in enum_cls]


class User(UUIDMixin, TimestampMixin, Base):
    """Clinic-scoped application user."""

    __tablename__: str = "users"
    __table_args__: tuple[Index, ...] = (
        Index("ix_users_clinic_id", "clinic_id"),
        Index("ix_users_role", "role"),
        Index("ix_users_email", "email", unique=True),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=_user_role_values,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
