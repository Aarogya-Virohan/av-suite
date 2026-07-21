from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, Protocol, TypeVar, cast
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession


class SupportsUUIDPrimaryKey(Protocol):
    """Protocol-style base for ORM models with a UUID primary key."""

    id: Any


ModelT = TypeVar("ModelT", bound=SupportsUUIDPrimaryKey)


class BaseRepository(Generic[ModelT]):
    """Generic async repository for SQLAlchemy ORM models."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        """Store the active async database session."""

        self.session = session

    async def create(self, obj_in: Mapping[str, Any]) -> ModelT:
        """Create and persist a new ORM instance without committing."""

        obj = self.model(**dict(obj_in))
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """Return a single row by primary key."""

        return await self.session.get(self.model, id)

    async def get_all(self, *, offset: int = 0, limit: int | None = None) -> list[ModelT]:
        """Return rows for the repository model with optional pagination."""

        statement = select(self.model).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)

        result = await self.session.scalars(statement)
        return list(result.all())

    async def update(self, db_obj: ModelT, obj_in: Mapping[str, Any]) -> ModelT:
        """Apply field updates to an existing ORM instance without committing."""

        for field_name, value in obj_in.items():
            setattr(db_obj, field_name, value)

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelT) -> None:
        """Remove an ORM instance from the current session."""

        await self.session.delete(db_obj)
        await self.session.flush()

    async def exists(self, id: UUID) -> bool:
        """Check whether a row exists for the given primary key."""

        statement = select(exists().where(cast(Any, self.model).id == id))
        result = await self.session.scalar(statement)
        return bool(result)
