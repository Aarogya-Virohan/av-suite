from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.user import UserRole
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.clinic import Clinic
from app.models.user import User


class Membership(UUIDMixin, TimestampMixin, Base):
    """Explicit membership of a user in a clinic/workspace."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "clinic_id", name="uq_memberships_user_clinic"),
        Index("ix_memberships_clinic_user", "clinic_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user: Mapped[User] = relationship(
        foreign_keys=[user_id],
        back_populates="memberships",
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship(back_populates="memberships")

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
            name="user_role",
            length=50,
        ),
        nullable=False,
    )
