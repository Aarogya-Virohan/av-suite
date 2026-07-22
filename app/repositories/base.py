from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, Protocol, TypeVar, cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession


class SupportsUUIDPrimaryKey(Protocol):
    """Protocol for ORM instances that expose a UUID primary key."""

    id: UUID


ModelT = TypeVar("ModelT", bound=SupportsUUIDPrimaryKey)


class BaseRepository(Generic[ModelT]):
    """Generic async repository for SQLAlchemy ORM models."""

    model: type[ModelT]
    session: AsyncSession

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        """Store the active async database session."""

        self.session = session
        self.model = model

    def _has_clinic_scope(self) -> bool:
        """Return whether the mapped model exposes a clinic scope column."""

        return hasattr(self.model, "clinic_id")

    def _apply_clinic_scope(self, statement: Select[tuple[ModelT]], clinic_id: UUID | None) -> Select[tuple[ModelT]]:
        """Apply an optional clinic filter when the model supports tenancy."""

        if clinic_id is None or not self._has_clinic_scope():
            return statement

        clinic_column = cast(Any, getattr(self.model, "clinic_id"))
        return statement.where(clinic_column == clinic_id)

    def _apply_id_filter(self, statement: Select[tuple[ModelT]], id: UUID) -> Select[tuple[ModelT]]:
        """Apply the primary-key filter in a type-safe SQLAlchemy-friendly way."""

        id_column = cast(Any, getattr(self.model, "id"))
        return statement.where(id_column == id)

    async def _delete_instance(self, db_obj: ModelT) -> None:
        """Remove the ORM instance using the current persistence strategy."""

        await self.session.delete(db_obj)

    async def create(self, obj_in: Mapping[str, object]) -> ModelT:
        """Create and persist a new ORM instance without committing."""

        obj = self.model()
        for field_name, value in obj_in.items():
            setattr(obj, field_name, value)

        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: UUID, *, clinic_id: UUID | None = None) -> ModelT | None:
        """Return a single row by primary key with optional clinic scoping."""

        if clinic_id is None or not self._has_clinic_scope():
            return await self.session.get(self.model, id)

        statement = self._apply_id_filter(select(self.model), id)
        statement = self._apply_clinic_scope(statement, clinic_id)
        result = await self.session.scalars(statement)
        return result.one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        clinic_id: UUID | None = None,
    ) -> list[ModelT]:
        """Return rows for the repository model with optional pagination and clinic scope."""

        statement = self._apply_clinic_scope(select(self.model), clinic_id).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)

        result = await self.session.scalars(statement)
        return list(result.all())

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        clinic_id: UUID | None = None,
    ) -> list[ModelT]:
        """Backward-compatible alias for list()."""

        return await self.list(offset=offset, limit=limit, clinic_id=clinic_id)

    async def update(self, db_obj: ModelT, obj_in: Mapping[str, object]) -> ModelT:
        """Apply field updates to an existing ORM instance without committing."""

        for field_name, value in obj_in.items():
            setattr(db_obj, field_name, value)

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelT) -> None:
        """Apply the repository's deletion strategy to an ORM instance."""

        await self._delete_instance(db_obj)
        await self.session.flush()

    async def exists(self, id: UUID, *, clinic_id: UUID | None = None) -> bool:
        """Check whether a row exists for the given primary key and optional clinic scope."""

        return (await self.get_by_id(id, clinic_id=clinic_id)) is not None
