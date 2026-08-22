from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.lead import LeadStage
from app.models.lead import Lead
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    """Repository for clinic-scoped Lead operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, Lead)

    async def list_leads(
        self,
        *,
        clinic_id: UUID | None = None,
        stage: LeadStage | None = None,
        assigned_to: UUID | None = None,
        source: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Lead]:
        """List leads with optional stage, assignee, source, search, and clinic scoping."""

        effective_limit = min(limit, 500)
        statement = select(Lead)

        if stage is not None:
            statement = statement.where(Lead.stage == stage)

        if assigned_to is not None:
            statement = statement.where(Lead.assigned_to == assigned_to)

        if source is not None:
            statement = statement.where(Lead.source == source)

        if search:
            search_pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Lead.name.ilike(search_pattern),
                    Lead.phone.ilike(search_pattern),
                )
            )

        statement = self._apply_soft_delete_filter(statement)
        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())
