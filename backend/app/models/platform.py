from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, DateTime, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class PlatformOperator(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "platform_operators"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'support')", name="ck_platform_operators_role"),
        Index("ix_platform_operators_email", "email", unique=True),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    mfa_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_totp_step: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PlatformAuditLog(UUIDMixin, Base):
    __tablename__ = "platform_audit_logs"
    __table_args__ = (
        Index("ix_platform_audit_logs_created_at", "created_at"),
        Index("ix_platform_audit_logs_organization_id", "organization_id"),
        Index("ix_platform_audit_logs_operator_id", "operator_id"),
    )

    operator_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("platform_operators.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clinics.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PlatformAuthRateLimit(Base):
    """Shared, expiring authentication attempt counters for all application workers."""

    __tablename__ = "platform_auth_rate_limits"
    __table_args__ = (Index("ix_platform_auth_rate_limits_updated_at", "updated_at"),)

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
