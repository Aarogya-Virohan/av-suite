from __future__ import annotations
import asyncio

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
from app.schemas.settings import (
    ClinicSettingsResponse,
    ClinicSettingsUpdate,
    LogoPreviewRequest,
    LogoPreviewResponse,
)
from app.core.upload_limits import MAX_LOGO_BYTES, check_logo_size
from app.services.report_letterhead import (
    LogoRejected,
    logo_needs_contrast_warning,
    prepare_uploaded_logo,
    render_logo_for_mode,
)
from app.services.audit import AuditLogService, changed_fields, log_event_safely
from app.services.settings import (
    ClinicSettingsService,
    SettingsNotFoundError,
    SettingsValidationError,
)

router = APIRouter()

# A 2 MB file as base64 plus the data-URI header; anything longer is refused
# before it is decoded.
MAX_LOGO_UPLOAD_CHARS = (2 * 1024 * 1024 * 4) // 3 + 200


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
    await log_event_safely(
        session, clinic.id, _admin.id, "create", "fee_item", item.id,
        {"name": item.name, "category": item.category, "default_price": item.default_price,
         "price_editable": item.price_editable},
    )
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
    changes_in = payload.model_dump(exclude_unset=True)
    before = {key: getattr(item, key) for key in changes_in}
    for key, value in changes_in.items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    await log_event_safely(
        session, clinic.id, _admin.id, "update", "fee_item", item.id,
        {"name": item.name, "changes": changed_fields(before, {key: getattr(item, key) for key in before})},
    )
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
    await log_event_safely(
        session, clinic.id, _admin.id, "delete", "fee_item", item.id, {"name": item.name},
    )


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


def _logo_low_contrast(stored: str | None, mode: str) -> bool:
    """BR-g warning: the logo as the band shows it is hard to see. Only for
    logos stored as data URIs (all uploads since Round 4); an old https logo
    is not downloaded for this."""
    if not stored or not stored.strip().lower().startswith("data:"):
        return False
    return logo_needs_contrast_warning(render_logo_for_mode(stored, mode), mode)


async def _settings_response(clinic: Clinic) -> ClinicSettingsResponse:
    out = ClinicSettingsResponse.model_validate(clinic)
    out.logo_low_contrast = await asyncio.to_thread(
        _logo_low_contrast, clinic.branding_logo_url, clinic.logo_bg_mode or "as_is"
    )
    return out


def _logo_rejected(exc: LogoRejected) -> HTTPException:
    # A file over the size limit stays a 413, as before Round 4 (#87).
    code = (
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        if exc.code == "LOGO_TOO_LARGE"
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(status_code=code, detail={"code": exc.code, "message": exc.message})
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
        return await _settings_response(clinic_record)
    except SettingsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/settings/clinic/logo-preview", response_model=LogoPreviewResponse)
async def preview_clinic_logo(
    payload: LogoPreviewRequest,
    clinic: CurrentClinicDep,
    scope: CapabilityScope = Depends(require_capability("settings.edit")),
) -> LogoPreviewResponse:
    """Check a picked logo and show it as the report band would, without
    saving anything (live letterhead preview in Settings, BR-g)."""

    def work() -> LogoPreviewResponse:
        stored = prepare_uploaded_logo(payload.logo, MAX_LOGO_BYTES)
        shown = render_logo_for_mode(stored, payload.logo_bg_mode)
        from app.services.report_letterhead import _png_size

        w, h = _png_size(shown) or (0, 0)
        return LogoPreviewResponse(
            logo=stored,
            letterhead_logo=shown,
            width=w,
            height=h,
            low_contrast=logo_needs_contrast_warning(shown, payload.logo_bg_mode),
        )

    if len(payload.logo) > (MAX_LOGO_UPLOAD_CHARS):
        raise _logo_rejected(LogoRejected("LOGO_TOO_LARGE", "The logo file is larger than 2 MB. Please choose a smaller file."))
    try:
        return await asyncio.to_thread(work)
    except LogoRejected as exc:
        raise _logo_rejected(exc) from exc


@router.patch("/settings/clinic", response_model=ClinicSettingsResponse)
async def update_clinic_settings(
    payload: ClinicSettingsUpdate,
    clinic: CurrentClinicDep,
    user: CurrentUserDep,
    service: SettingsServiceDep,
    scope: CapabilityScope = Depends(require_capability("settings.edit")),
) -> ClinicSettingsResponse:
    """Update clinic branding settings (admin only)."""

    # BR-g: an uploaded logo (data URI) is checked against the upload rules
    # (PNG / JPG / WebP, up to 2 MB, at least 200 px on the shorter side,
    # 1:4 to 4:1) and stored as a resized copy of at most MAX_LOGO_BYTES.
    logo = payload.branding_logo_url
    if isinstance(logo, str) and logo.strip().lower().startswith("data:"):
        try:
            payload.branding_logo_url = await asyncio.to_thread(
                prepare_uploaded_logo, logo, MAX_LOGO_BYTES
            )
        except LogoRejected as exc:
            raise _logo_rejected(exc) from exc
    check_logo_size(payload.branding_logo_url)
    try:
        updated_clinic = await service.update_settings(clinic.id, user.id, payload)
        return await _settings_response(updated_clinic)
    except SettingsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SettingsValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
