from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_async_session,
    get_current_clinic,
    get_current_user,
    require_capability,
    require_admin,
)
from app.enums.permission import CapabilityScope
from app.models.clinic import Clinic
from app.models.user import User
from app.models.clinic_fee_item import ClinicFeeItem
from app.schemas.settings import (
    ClinicFeeItemCreate,
    ClinicFeeItemResponse,
    ClinicFeeItemUpdate,
)
from app.repositories.audit import AuditLogRepository
from app.repositories.clinic import ClinicRepository
from app.schemas.settings import ClinicSettingsResponse, ClinicSettingsUpdate
from app.services.audit import AuditLogService
from app.services.settings import (
    ClinicSettingsService,
    SettingsNotFoundError,
    SettingsValidationError,
)

router = APIRouter()


@router.get("/settings/fee-items", response_model=list[ClinicFeeItemResponse])
async def list_fee_items(
    clinic: CurrentClinicDep,
    session: AsyncSession = Depends(get_async_session),
    scope: CapabilityScope = Depends(require_capability("invoices.create")),
):
    result = await session.scalars(
        select(ClinicFeeItem)
        .where(
            ClinicFeeItem.clinic_id == clinic.id,
            ClinicFeeItem.active.is_(True),
        )
        .order_by(ClinicFeeItem.sort_order, ClinicFeeItem.name)
    )
    return result.all()


@router.post(
    "/settings/fee-items",
    response_model=ClinicFeeItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_fee_item(
    payload: ClinicFeeItemCreate,
    clinic: CurrentClinicDep,
    session: AsyncSession = Depends(get_async_session),
    _admin: User = Depends(require_admin),
):
    item = ClinicFeeItem(clinic_id=clinic.id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.patch("/settings/fee-items/{item_id}", response_model=ClinicFeeItemResponse)
async def update_fee_item(
    item_id: UUID,
    payload: ClinicFeeItemUpdate,
    clinic: CurrentClinicDep,
    session: AsyncSession = Depends(get_async_session),
    _admin: User = Depends(require_admin),
):
    item = await session.scalar(
        select(ClinicFeeItem).where(
            ClinicFeeItem.id == item_id,
            ClinicFeeItem.clinic_id == clinic.id,
            ClinicFeeItem.active.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Fee item not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/settings/fee-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_fee_item(
    item_id: UUID,
    clinic: CurrentClinicDep,
    session: AsyncSession = Depends(get_async_session),
    _admin: User = Depends(require_admin),
):
    item = await session.scalar(
        select(ClinicFeeItem).where(
            ClinicFeeItem.id == item_id,
            ClinicFeeItem.clinic_id == clinic.id,
            ClinicFeeItem.active.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Fee item not found.")
    item.active = False
    await session.commit()


async def get_settings_service(
    session: AsyncSession = Depends(get_async_session),
) -> ClinicSettingsService:
    """Inject ClinicSettingsService bound to async session."""

    audit_service = AuditLogService(audit_repository=AuditLogRepository(session))
    return ClinicSettingsService(
        clinic_repository=ClinicRepository(session),
        audit_service=audit_service,
    )


SettingsServiceDep = Annotated[ClinicSettingsService, Depends(get_settings_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("/settings/clinic", response_model=ClinicSettingsResponse)
async def get_clinic_settings(
    clinic: CurrentClinicDep,
    user: CurrentUserDep,
    service: SettingsServiceDep,
    scope: CapabilityScope = Depends(require_capability("settings.view")),
) -> ClinicSettingsResponse:
    """Retrieve clinic branding and configuration settings."""

    try:
        clinic_record = await service.get_settings(clinic.id)
        return ClinicSettingsResponse.model_validate(clinic_record)
    except SettingsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch("/settings/clinic", response_model=ClinicSettingsResponse)
async def update_clinic_settings(
    payload: ClinicSettingsUpdate,
    clinic: CurrentClinicDep,
    user: CurrentUserDep,
    service: SettingsServiceDep,
    scope: CapabilityScope = Depends(require_capability("settings.edit")),
) -> ClinicSettingsResponse:
    """Update clinic branding settings (admin only)."""

    try:
        updated_clinic = await service.update_settings(clinic.id, user.id, payload)
        return ClinicSettingsResponse.model_validate(updated_clinic)
    except SettingsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SettingsValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
