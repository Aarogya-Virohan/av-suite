from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.booking import AppointmentRequestStatus
from app.models.booking import AppointmentRequest
from app.repositories.base import BaseRepository


class AppointmentRequestRepository(BaseRepository[AppointmentRequest]):
    """Repository for clinic-scoped AppointmentRequest operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, AppointmentRequest)

    async def list_requests(
        self,
        *,
        clinic_id: UUID | None = None,
        status: AppointmentRequestStatus | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AppointmentRequest]:
        """List appointment requests with optional status filter, search, and clinic scoping."""

        effective_limit = min(limit, 500)
        statement = select(AppointmentRequest)

        if status is not None:
            statement = statement.where(AppointmentRequest.status == status)

        if search:
            search_pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    AppointmentRequest.name.ilike(search_pattern),
                    AppointmentRequest.phone.ilike(search_pattern),
                )
            )

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())
