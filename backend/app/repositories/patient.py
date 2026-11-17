from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.patient import PatientStatus
from app.models.patient import Patient
from app.repositories.base import BaseRepository
from app.services.patient_number import allocate_patient_display_number
from collections.abc import Mapping


class PatientRepository(BaseRepository[Patient]):
    """Repository for clinic-scoped patient persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a patient repository bound to the active session."""

        super().__init__(session, Patient)

    async def create(self, obj_in: Mapping[str, object]) -> Patient:
        """Create a patient, allocating a clinic number when none was supplied."""

        data = dict(obj_in)
        number = data.get("display_number")
        if number is None:
            clinic_id = data.get("clinic_id")
            if clinic_id is None:
                raise ValueError("clinic_id is required to allocate a patient display number.")
            data["display_number"] = await allocate_patient_display_number(
                self.session, UUID(str(clinic_id))
            )
        elif isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise ValueError("display_number must be a positive integer.")

        return await super().create(data)

    async def get_by_patient_id(self, id: UUID, *, clinic_id: UUID | None = None) -> Patient | None:
        """Return a single patient by primary key ID and clinic scope."""

        return await self.get_by_id(id, clinic_id=clinic_id)

    async def search_by_name(
        self,
        name: str,
        *,
        clinic_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Search patients by case-insensitive name match."""

        effective_limit = min(limit, 500)
        statement = select(Patient).where(Patient.full_name.ilike(f"%{name.strip()}%"))
        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def search_by_phone(
        self,
        phone: str,
        *,
        clinic_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Search patients by phone number match."""

        effective_limit = min(limit, 500)
        statement = select(Patient).where(Patient.phone.ilike(f"%{phone.strip()}%"))
        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def search_by_email(
        self,
        email: str,
        *,
        clinic_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Search patients by email address if supported."""

        if not hasattr(Patient, "email"):
            return []

        effective_limit = min(limit, 500)
        statement = select(Patient).where(getattr(Patient, "email").ilike(f"%{email.strip()}%"))
        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def list_active(
        self,
        *,
        clinic_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Return active patients for a clinic."""

        effective_limit = min(limit, 500)
        statement = select(Patient).where(Patient.status == PatientStatus.ACTIVE)
        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def update_patient(self, db_obj: Patient, update_data: dict) -> Patient:
        """Update only supplied fields and preserve updated_at."""
        
        return await self.update(db_obj, update_data)

    async def soft_delete_patient(self, db_obj: Patient, deleted_by: UUID | None = None) -> None:
        """Soft delete a patient."""
        
        await self.delete(db_obj, deleted_by)

