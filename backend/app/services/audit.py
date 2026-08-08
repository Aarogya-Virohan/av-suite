from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.audit import AuditLog
from app.repositories.audit import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditLogService:
    """Service providing safe audit log recording and clinic-scoped querying."""

    audit_repository: AuditLogRepository

    def __init__(self, audit_repository: AuditLogRepository) -> None:
        """Inject audit log repository."""

        self.audit_repository = audit_repository

    async def log_event(
        self,
        clinic_id: UUID,
        user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Record an audit log entry safely without causing parent transaction failure."""

        try:
            log_data = {
                "clinic_id": clinic_id,
                "user_id": user_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details or {},
            }
            return await self.audit_repository.create(log_data)
        except Exception as exc:
            logger.warning("Failed to record audit log event (%s on %s): %s", action, entity_type, exc)
            return None

    async def list_logs(
        self,
        clinic_id: UUID,
        *,
        entity_type: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Query audit log entries for a clinic with optional filtering."""

        return await self.audit_repository.list_logs(
            clinic_id=clinic_id,
            entity_type=entity_type,
            action=action,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

    async def get_log(self, clinic_id: UUID, log_id: UUID) -> AuditLog | None:
        """Fetch one clinic-scoped audit log by ID."""

        return await self.audit_repository.get_log_by_id(clinic_id, log_id)

    async def list_logs_paginated(
        self,
        clinic_id: UUID,
        *,
        entity_type: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        """Query audit logs with pagination metadata and optional search."""

        return await self.audit_repository.list_logs_paginated(
            clinic_id=clinic_id,
            entity_type=entity_type,
            action=action,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            search=search,
            offset=offset,
            limit=limit,
        )
