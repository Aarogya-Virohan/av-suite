from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.organization import ClinicStatus, OrganizationStatus
from app.exceptions import ResourceNotFoundError, WorkspaceSuspendedError
from app.models.clinic import Clinic
from app.models.organization import Organization


async def is_clinic_active(db: AsyncSession, clinic: Clinic) -> bool:
    """Return whether both the clinic and its organization are active."""

    if clinic.status != ClinicStatus.ACTIVE:
        return False
    if clinic.organization_id is None:
        return False
    organization = await db.get(Organization, clinic.organization_id)
    return organization is not None and organization.status == OrganizationStatus.ACTIVE


async def ensure_clinic_active(db: AsyncSession, clinic_id: UUID) -> Clinic:
    """Load a clinic and raise the workspace suspension error at the right level."""

    clinic = await db.get(Clinic, clinic_id)
    if clinic is None:
        raise ResourceNotFoundError("Clinic", clinic_id)
    if clinic.status != ClinicStatus.ACTIVE:
        raise WorkspaceSuspendedError("clinic")
    if clinic.organization_id is None:
        raise WorkspaceSuspendedError("organization")
    organization = await db.get(Organization, clinic.organization_id)
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise WorkspaceSuspendedError("organization")
    return clinic
