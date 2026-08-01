from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from app.core.dependencies import require_admin

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.models.clinic import Clinic
from app.repositories.audit import AuditLogRepository
from app.schemas.audit import AuditLogResponse
from app.services.audit import AuditLogService
from app.schemas.envelope import ResponseEnvelope

router = APIRouter(dependencies=[Depends(require_admin)])


async def get_audit_log_service(
    session: AsyncSession = Depends(get_async_session),
) -> AuditLogService:
    """Inject AuditLogService bound to async session."""

    return AuditLogService(audit_repository=AuditLogRepository(session))


AuditLogServiceDep = Annotated[AuditLogService, Depends(get_audit_log_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


@router.get("/audit-logs", response_model=ResponseEnvelope[list[AuditLogResponse]])
async def list_audit_logs(
    clinic: CurrentClinicDep,
    service: AuditLogServiceDep,
    entity_type: Annotated[str | None, Query(alias="entity_type")] = None,
    action: Annotated[str | None, Query(alias="action")] = None,
    user_id: Annotated[UUID | None, Query(alias="user_id")] = None,
    start_date: Annotated[datetime | None, Query(alias="start_date")] = None,
    end_date: Annotated[datetime | None, Query(alias="end_date")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ResponseEnvelope[list[AuditLogResponse]]:
    """List clinic-scoped audit logs with filtering and pagination."""

    logs = await service.list_logs(
        clinic.id,
        entity_type=entity_type,
        action=action,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )
    items = [AuditLogResponse.model_validate(log) for log in logs]
    return ResponseEnvelope(
        data=items,
        meta={"total": len(logs) if len(logs) < limit else len(items) + offset, "offset": offset, "limit": limit}
    )
