from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.base import Base
from app.common.mixins import UUIDMixin
from app.models.clinic import Clinic
from app.models.user import User


class AuditLog(UUIDMixin, Base):
    """Audit log entry tracking system actions and entity modifications."""

    __tablename__: str = "audit_logs"
    __table_args__: tuple[Index, ...] = (
        Index("ix_audit_logs_clinic_id", "clinic_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity_type", "entity_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship()

    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    user: Mapped[User | None] = relationship()

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
