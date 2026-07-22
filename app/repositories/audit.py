from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
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
