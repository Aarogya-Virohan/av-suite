from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for clinic-scoped AuditLog operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, AuditLog)

    async def list_logs(
        self,
        *,
        clinic_id: UUID | None = None,
        entity_type: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """List audit log entries with entity_type, action, user_id, and date range filters."""

        effective_limit = min(limit, 500)
        statement = select(AuditLog)

        if entity_type:
            statement = statement.where(AuditLog.entity_type == entity_type)

        if action:
            statement = statement.where(AuditLog.action == action)

        if user_id is not None:
            statement = statement.where(AuditLog.user_id == user_id)

        if start_date is not None:
            statement = statement.where(AuditLog.created_at >= start_date)

        if end_date is not None:
            statement = statement.where(AuditLog.created_at <= end_date)

        statement = self._apply_clinic_scope(statement, clinic_id).order_by(AuditLog.created_at.desc()).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def get_log_by_id(self, clinic_id: UUID, log_id: UUID) -> AuditLog | None:
        """Return a single audit log by ID in clinic scope."""

        return await self.get_by_id(log_id, clinic_id=clinic_id)

    async def list_logs_paginated(
        self,
        *,
        clinic_id: UUID | None = None,
        entity_type: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        """List audit logs with total count and optional text search."""

        effective_limit = min(limit, 500)
        statement = select(AuditLog)

        if entity_type:
            statement = statement.where(AuditLog.entity_type == entity_type)

        if action:
            statement = statement.where(AuditLog.action == action)

        if user_id is not None:
            statement = statement.where(AuditLog.user_id == user_id)

        if start_date is not None:
            statement = statement.where(AuditLog.created_at >= start_date)

        if end_date is not None:
            statement = statement.where(AuditLog.created_at <= end_date)

        if search:
            search_pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    AuditLog.action.ilike(search_pattern),
                    AuditLog.entity_type.ilike(search_pattern),
                    cast(AuditLog.user_id, String).ilike(search_pattern),
                    cast(AuditLog.entity_id, String).ilike(search_pattern),
                    cast(AuditLog.details, String).ilike(search_pattern),
                )
            )

        statement = self._apply_clinic_scope(statement, clinic_id)

        count_statement = select(func.count()).select_from(statement.subquery())
        total_result = await self.session.execute(count_statement)
        total = total_result.scalar() or 0

        statement = statement.order_by(AuditLog.created_at.desc()).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all()), total
