"""
Rules an exercise must pass to go on a home prescription (EL-D-013, EL-D-014).

- rx_mode BLOCKED (therapist-applied or supervised-in-clinic exercises, and
  yoga rows with safety rule SR24 until contraindication rules are live):
  refused with 422 and a plain message. Nothing is saved.
- requires_side (Self-Epley): the item must say "left" or "right"; refused
  with 422 otherwise. A side sent for any other exercise is dropped, so it
  never prints by mistake.
- CAREGIVER items are allowed; the PDF labels them.
- rx_mode HIDDEN (EL-D-017): refused with 422 ("no longer offered").

Unknown exercise ids are not judged here (clinic scoping of patient and
exercise ids is AUD-05, lane L2).
"""

from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.schemas.prescription import PrescriptionItemCreate
from app.services.exercise_structure import RX_BLOCKED, RX_HIDDEN


async def check_items(db: AsyncSession, items: Sequence[PrescriptionItemCreate]) -> None:
    """Raise 422 when an item breaks a rule; clear side where it does not apply."""
    ids = list({item.exercise_id for item in items})
    if not ids:
        return
    rows = await db.execute(
        select(Exercise.id, Exercise.title, Exercise.rx_mode, Exercise.requires_side).where(
            Exercise.id.in_(ids)
        )
    )
    info: dict[uuid.UUID, tuple[str, str, bool]] = {
        r.id: (r.title, r.rx_mode, r.requires_side) for r in rows.all()
    }
    blocked: list[str] = []
    hidden: list[str] = []
    missing_side: list[str] = []
    for item in items:
        row = info.get(item.exercise_id)
        if row is None:
            continue
        title, mode, needs_side = row
        if mode == RX_BLOCKED:
            blocked.append(title)
        if mode == RX_HIDDEN:
            hidden.append(title)
        if needs_side:
            if item.side is None:
                missing_side.append(title)
        else:
            item.side = None
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "These exercises are done by the therapist in the clinic and cannot go on a "
                "home prescription: " + ", ".join(sorted(set(blocked)))
            ),
        )
    if hidden:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="These exercises are no longer offered; remove them: " + ", ".join(sorted(set(hidden))),
        )
    if missing_side:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose the affected side (left or right) for: " + ", ".join(sorted(set(missing_side))),
        )
