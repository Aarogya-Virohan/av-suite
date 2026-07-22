from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, Protocol, TypeVar, cast
from uuid import UUID

from sqlalchemy import Select, exists, select
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

    def _apply_clinic_scope(self, statement: Select[Any], clinic_id: UUID | None) -> Select[Any]:
        """Apply a clinic filter when the model supports tenancy."""

        if self._has_clinic_scope():
            if clinic_id is None:
                raise ValueError(f"clinic_id is required for clinic-scoped model '{self.model.__name__}'.")
            clinic_column = cast(Any, getattr(self.model, "clinic_id"))
            return statement.where(clinic_column == clinic_id)

        return statement

    def _apply_id_filter(self, statement: Select[Any], id: UUID) -> Select[Any]:
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

        if self._has_clinic_scope():
            statement = self._apply_id_filter(select(self.model), id)
            statement = self._apply_clinic_scope(statement, clinic_id)
            result = await self.session.scalars(statement)
            return result.one_or_none()

        return await self.session.get(self.model, id)

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        clinic_id: UUID | None = None,
    ) -> list[ModelT]:
        """Return rows for the repository model with optional pagination and clinic scope."""

        effective_limit = 100 if limit is None else min(limit, 500)
        statement = self._apply_clinic_scope(select(self.model), clinic_id).offset(offset).limit(effective_limit)

        result = await self.session.scalars(statement)
        return list(result.all())

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
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

        statement = self._apply_id_filter(select(1).select_from(self.model), id)
        statement = self._apply_clinic_scope(statement, clinic_id)
        query = select(exists(statement))
        result = await self.session.scalar(query)
        return bool(result)

