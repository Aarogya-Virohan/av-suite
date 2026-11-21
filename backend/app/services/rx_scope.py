"""AUD-05: a prescription may only use this clinic's patient and exercises
that are global or belong to this clinic (claude/ref/audit.md, lane L2).

Before: a patient UUID from another clinic was saved (and printed on the Rx
PDF), and an unknown patient or exercise UUID hit a foreign key = 500.
Rx content rules (BLOCKED / HIDDEN / side) stay in rx_rules.py (L5).
"""

from __future__ import annotations

import uuid
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.repositories.patient import PatientRepository


async def check_patient(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> None:
    """404 when the patient is not in the caller's clinic (same check as other create paths)."""
    patient = await PatientRepository(db).get_by_patient_id(patient_id, clinic_id=clinic_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found or not in caller's clinic",
        )


async def check_exercises(
    db: AsyncSession, clinic_id: uuid.UUID, exercise_ids: Iterable[uuid.UUID]
) -> None:
    """422 when an exercise id is unknown or belongs to another clinic."""
    ids = set(exercise_ids)
    if not ids:
        return
    allowed = set(
        (
            await db.scalars(
                select(Exercise.id).where(
                    Exercise.id.in_(ids),
                    or_(Exercise.clinic_id.is_(None), Exercise.clinic_id == clinic_id),
                )
            )
        ).all()
    )
    unknown = ids - allowed
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "EXERCISE_NOT_AVAILABLE",
                "message": "Some exercises are not available in this clinic. Remove them and try again.",
                "exercise_ids": sorted(str(i) for i in unknown),
            },
        )
