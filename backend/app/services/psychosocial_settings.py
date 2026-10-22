"""Clinic-wide Tool 03 settings (SRS 4.3.2, S-D-027).

Holds the default repeat interval per screener. It only prefills the Repeat
field on the assign form: changing it never edits repeat schedules that
already exist. Referral thresholds are read-only here and come from the
instrument definitions (app/screening/thresholds.py).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.psychosocial import PsychosocialClinicSetting
from app.screening.registry import list_instruments
from app.services.psychosocial import audit

# Flip only together with a stored, confirmed per-clinic threshold and a
# scoring change (Pending P-13). The API reports it so the UI can say why
# the table cannot be edited.
THRESHOLDS_EDITABLE = False


async def clinic_settings(
    db: AsyncSession, clinic_id: uuid.UUID
) -> dict[str, PsychosocialClinicSetting]:
    rows = await db.scalars(
        select(PsychosocialClinicSetting).where(PsychosocialClinicSetting.clinic_id == clinic_id)
    )
    return {row.instrument_id: row for row in rows}


async def default_repeat_weeks(db: AsyncSession, clinic_id: uuid.UUID) -> dict[str, int | None]:
    """Default per screener for this clinic. Screeners never configured: None."""
    rows = await clinic_settings(db, clinic_id)
    return {
        inst.id: (rows[inst.id].default_repeat_weeks if inst.id in rows else None)
        for inst in list_instruments()
    }


async def set_default_repeat(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    instrument_id: str,
    weeks: int | None,
) -> PsychosocialClinicSetting:
    row = await db.scalar(
        select(PsychosocialClinicSetting)
        .where(
            PsychosocialClinicSetting.clinic_id == clinic_id,
            PsychosocialClinicSetting.instrument_id == instrument_id,
        )
        .with_for_update()
    )
    before = row.default_repeat_weeks if row is not None else None
    if row is None:
        row = PsychosocialClinicSetting(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            instrument_id=instrument_id,
            default_repeat_weeks=weeks,
            updated_by=user_id,
        )
        db.add(row)
    elif before == weeks:
        # Nothing changed: no write, no audit event.
        return row
    else:
        row.default_repeat_weeks = weeks
        row.updated_by = user_id
    await db.commit()
    await db.refresh(row)

    # Clinic configuration only, no patient data.
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.settings_updated",
        entity_type="psychosocial_clinic_setting",
        entity_id=row.id,
        details={
            "instrument_id": instrument_id,
            "default_repeat_weeks_before": before,
            "default_repeat_weeks_after": weeks,
        },
    )
    return row
