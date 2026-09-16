from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.permission import CapabilityScope
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.clinic import Clinic
from app.models.user import User


def _capability_scope_values(enum_cls: type[CapabilityScope]) -> list[str]:
    """Return database enum values for capability scopes."""

    return [member.value for member in enum_cls]


class UserPermission(UUIDMixin, TimestampMixin, Base):
    """Persistent per-user Rev3 capability override."""

    __tablename__: str = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "capability_key", name="uq_user_permissions_user_capability"),
        Index("ix_user_permissions_clinic_user", "clinic_id", "user_id"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship(back_populates="user_permissions")

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user: Mapped[User] = relationship(
        foreign_keys=[user_id],
        back_populates="permission_overrides",
    )

    capability_key: Mapped[str] = mapped_column(String(150), nullable=False)
    scope: Mapped[CapabilityScope] = mapped_column(
        Enum(
            CapabilityScope,
            name="capability_scope",
            values_callable=_capability_scope_values,
        ),
        nullable=False,
    )

    granted_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    granted_by_user: Mapped[User | None] = relationship(foreign_keys=[granted_by])
