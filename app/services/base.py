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

    async def get(self, id: UUID) -> ModelT | None:
        """Fetch a single entity by primary key."""

        return await self.repository.get_by_id(id)

    async def list(self, *, offset: int = 0, limit: int | None = None) -> list[ModelT]:
        """Return a paginated list of entities."""

        return await self.repository.get_all(offset=offset, limit=limit)

    async def update(self, db_obj: ModelT, obj_in: Mapping[str, object]) -> ModelT:
        """Update an entity through the repository layer."""

        return await self.repository.update(db_obj, obj_in)

    async def delete(self, db_obj: ModelT) -> None:
        """Delete an entity through the repository layer."""

        await self.repository.delete(db_obj)
