from __future__ import annotations

from collections.abc import Mapping
from typing import Generic, TypeVar
from uuid import UUID

from app.repositories.base import BaseRepository, SupportsUUIDPrimaryKey

ModelT = TypeVar("ModelT", bound=SupportsUUIDPrimaryKey)


class BaseService(Generic[ModelT]):
    """Generic async service layer for coordinating repository operations."""

    repository: BaseRepository[ModelT]

    def __init__(self, repository: BaseRepository[ModelT]) -> None:
        """Store the repository used by the service."""

        self.repository = repository

    async def create(self, obj_in: Mapping[str, object]) -> ModelT:
        """Create a new entity through the repository layer."""

        return await self.repository.create(obj_in)

    async def get(self, id: UUID, *, clinic_id: UUID | None = None) -> ModelT | None:
        """Fetch a single entity by primary key with optional clinic scope."""

        return await self.repository.get_by_id(id, clinic_id=clinic_id)

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        clinic_id: UUID | None = None,
    ) -> list[ModelT]:
        """Return a paginated list of entities with optional clinic scope."""

        return await self.repository.list(offset=offset, limit=limit, clinic_id=clinic_id)

    async def update(self, db_obj: ModelT, obj_in: Mapping[str, object]) -> ModelT:
        """Update an entity through the repository layer."""

        return await self.repository.update(db_obj, obj_in)

    async def delete(self, db_obj: ModelT) -> None:
        """Delete an entity through the repository layer."""

        await self.repository.delete(db_obj)

    async def exists(self, id: UUID, *, clinic_id: UUID | None = None) -> bool:
        """Check whether an entity exists for the given primary key and clinic scope."""

        return await self.repository.exists(id, clinic_id=clinic_id)
