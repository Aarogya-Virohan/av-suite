from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Clinic
from app.repositories.base import BaseRepository


class ClinicRepository(BaseRepository[Clinic]):
    """Repository for Clinic entity operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, Clinic)

    async def get_by_slug_or_id(self, identifier: str) -> Clinic | None:
        """Find a clinic by UUID or exact public slug."""

        try:
            clinic_uuid = UUID(identifier)
            return await self.get_by_id(clinic_uuid)
        except (ValueError, AttributeError):
            pass
        statement = select(Clinic).where(Clinic.slug == identifier)
        return await self.session.scalar(statement)

    async def code_in_use(self, code: str, exclude_id: UUID | None = None) -> bool:
        """True when another clinic already has this Patient ID prefix."""

        statement = select(Clinic.id).where(Clinic.code == code)
        if exclude_id is not None:
            statement = statement.where(Clinic.id != exclude_id)
        return (await self.session.scalar(statement.limit(1))) is not None
