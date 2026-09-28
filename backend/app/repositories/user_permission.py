from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.permission import CapabilityScope
from app.models.user_permission import UserPermission
from app.repositories.base import BaseRepository


class UserPermissionRepository(BaseRepository[UserPermission]):
    """Repository for persistent per-user capability overrides."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a user permission repository bound to the active session."""

        super().__init__(session, UserPermission)

    async def list_for_user(self, user_id: UUID) -> list[UserPermission]:
        """Return all permission overrides for a user."""

        result = await self.session.scalars(
            select(UserPermission).where(UserPermission.user_id == user_id)
        )
        return list(result.all())

    async def list_for_user_in_clinic(self, clinic_id: UUID, user_id: UUID) -> list[UserPermission]:
        """Return all permission overrides for a user within a clinic."""

        result = await self.session.scalars(
            select(UserPermission).where(
                UserPermission.clinic_id == clinic_id,
                UserPermission.user_id == user_id,
            )
        )
        return list(result.all())

    async def get_for_user_capability(
        self,
        user_id: UUID,
        capability_key: str,
        *,
        clinic_id: UUID | None = None,
    ) -> UserPermission | None:
        """Return one override for a user/capability pair, optionally clinic-scoped."""

        statement = select(UserPermission).where(
            UserPermission.user_id == user_id,
            UserPermission.capability_key == capability_key,
        )
        if clinic_id is not None:
            statement = statement.where(UserPermission.clinic_id == clinic_id)

        result = await self.session.scalars(statement)
        return result.one_or_none()

    async def set_override(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
        capability_key: str,
        scope: CapabilityScope,
        granted_by: UUID | None,
    ) -> UserPermission:
        """Create or update a user's explicit permission override."""

        existing = await self.get_for_user_capability(
            user_id,
            capability_key,
            clinic_id=clinic_id,
        )
        payload = {
            "clinic_id": clinic_id,
            "user_id": user_id,
            "capability_key": capability_key,
            "scope": scope,
            "granted_by": granted_by,
        }
        if existing is None:
            return await self.create(payload)

        return await self.update(existing, payload)

    async def delete_for_user_capability(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
        capability_key: str,
    ) -> bool:
        """Delete one explicit permission override if it exists."""

        existing = await self.get_for_user_capability(
            user_id,
            capability_key,
            clinic_id=clinic_id,
        )
        if existing is None:
            return False

        await self.delete(existing)
        return True
