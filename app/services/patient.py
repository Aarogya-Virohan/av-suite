from __future__ import annotations

from uuid import UUID

from app.models.patient import Patient
from app.repositories.patient import PatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientNotFoundError(Exception):
    """Raised when a requested patient record does not exist for a clinic."""


class PatientValidationError(Exception):
    """Raised when patient business validation fails."""


class PatientService:
    """Service layer managing clinic-scoped patient business operations."""

    patient_repository: PatientRepository

    def __init__(self, patient_repository: PatientRepository) -> None:
        """Inject the PatientRepository dependency."""

        self.patient_repository = patient_repository

    async def create_patient(self, clinic_id: UUID, payload: PatientCreate) -> Patient:
        """Validate payload and create a clinic-scoped patient."""

        full_name = payload.full_name.strip()
        if not full_name:
            raise PatientValidationError("Patient full name cannot be empty.")

        obj_in = payload.model_dump()
        obj_in["full_name"] = full_name
        obj_in["clinic_id"] = clinic_id
        return await self.patient_repository.create(obj_in)

    async def get_patient(self, clinic_id: UUID, patient_id: UUID) -> Patient:
        """Retrieve a patient by ID ensuring strict clinic scope isolation."""

        patient = await self.patient_repository.get_by_patient_id(patient_id, clinic_id=clinic_id)
        if patient is None:
            raise PatientNotFoundError(f"Patient '{patient_id}' not found for clinic '{clinic_id}'.")

        return patient

    async def list_patients(
        self,
        clinic_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
        active_only: bool = False,
    ) -> list[Patient]:
        """List patients scoped to a clinic with optional active status filter."""

        if active_only:
            return await self.patient_repository.list_active(clinic_id=clinic_id, offset=offset, limit=limit)

        return await self.patient_repository.list(clinic_id=clinic_id, offset=offset, limit=limit)

    async def update_patient(self, clinic_id: UUID, patient_id: UUID, payload: PatientUpdate) -> Patient:
        """Update a clinic-scoped patient record."""

        patient = await self.get_patient(clinic_id, patient_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "full_name" in update_data and update_data["full_name"] is not None:
            cleaned_name = update_data["full_name"].strip()
            if not cleaned_name:
                raise PatientValidationError("Patient full name cannot be empty.")
            update_data["full_name"] = cleaned_name

        if not update_data:
            return patient

        return await self.patient_repository.update(patient, update_data)

    async def delete_patient(self, clinic_id: UUID, patient_id: UUID) -> None:
        """Delete a clinic-scoped patient record."""

        patient = await self.get_patient(clinic_id, patient_id)
        await self.patient_repository.delete(patient)

    async def search_patients(
        self,
        clinic_id: UUID,
        *,
        query: str,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Search patients by name or phone within a clinic."""

        cleaned_query = query.strip()
        if not cleaned_query:
            return await self.list_patients(clinic_id, offset=offset, limit=limit)

        if cleaned_query.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            return await self.patient_repository.search_by_phone(
                cleaned_query, clinic_id=clinic_id, offset=offset, limit=limit
            )

        return await self.patient_repository.search_by_name(
            cleaned_query, clinic_id=clinic_id, offset=offset, limit=limit
        )
