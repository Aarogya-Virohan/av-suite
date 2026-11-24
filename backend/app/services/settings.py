from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.models.clinic import Clinic
from app.repositories.clinic import ClinicRepository
from app.schemas.settings import ClinicSettingsUpdate
from app.services.audit import AuditLogService


CODE_TAKEN_MESSAGE = "This clinic code is already used by another clinic. Choose a different one."


class SettingsValidationError(Exception):
    """Raised when validation fails for clinic settings updates."""


class SettingsNotFoundError(Exception):
    """Raised when a clinic resource is not found."""


class ClinicSettingsService:
    """Service managing clinic branding and configuration settings with audit trail."""

    clinic_repository: ClinicRepository
    audit_service: AuditLogService

    def __init__(
        self,
        clinic_repository: ClinicRepository,
        audit_service: AuditLogService,
    ) -> None:
        """Inject repository and audit service."""

        self.clinic_repository = clinic_repository
        self.audit_service = audit_service

    async def get_settings(self, clinic_id: UUID) -> Clinic:
        """Retrieve clinic settings and branding details."""

        clinic = await self.clinic_repository.get_by_id(clinic_id)
        if clinic is None:
            raise SettingsNotFoundError(f"Clinic '{clinic_id}' not found.")
        return clinic

    async def update_settings(
        self,
        clinic_id: UUID,
        user_id: UUID,
        payload: ClinicSettingsUpdate,
    ) -> Clinic:
        """Update allowed clinic settings (name, logo, color) and log audit entry."""

        clinic = await self.get_settings(clinic_id)
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            return clinic

        new_code = update_data.get("code")
        if new_code is not None and new_code != clinic.code:
            if await self.clinic_repository.code_in_use(new_code, exclude_id=clinic.id):
                raise SettingsValidationError(CODE_TAKEN_MESSAGE)
        elif new_code is not None:
            update_data.pop("code")
            if not update_data:
                return clinic

        try:
            updated_clinic = await self.clinic_repository.update(clinic, update_data)
        except IntegrityError as exc:
            # Two clinics saving the same new code at the same moment.
            if "uq_clinics_code" in str(exc.orig):
                await self.clinic_repository.session.rollback()
                raise SettingsValidationError(CODE_TAKEN_MESSAGE) from exc
            raise

        # Record audit log event safely
        await self.audit_service.log_event(
            clinic_id=clinic_id,
            user_id=user_id,
            action="update",
            entity_type="clinic",
            entity_id=clinic.id,
            details=update_data,
        )

        return updated_clinic
