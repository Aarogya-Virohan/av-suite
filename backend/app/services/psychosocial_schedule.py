"""Repeat schedules and the Due list (SRS 4.1.1 recurring, S-D-026).

Nothing here sends a link. Links go out through the physio's WhatsApp, so a
link the system created on its own would never reach the patient. A
schedule only answers "is this screener due again?", and the clinic sends
the due ones from the Due list with one click.

State of a schedule, decided by ``schedule_state`` (pure, unit tested):
- consent_withdrawn: the patient withdrew consent; never due.
- waiting: an open link with this screener exists (not expired, not done).
- due: the next date has passed. Next date = last completed result of this
  screener + interval, or the day the schedule started if there is none yet.
- upcoming: the next date is still ahead.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.psychosocial import (
    PsychosocialAssignment,
    PsychosocialConsent,
    PsychosocialSchedule,
    PsychosocialSession,
)
from app.screening.trend import INSTRUMENT_ORDER
from app.services import psychosocial as svc

STATES = ("consent_withdrawn", "waiting", "due", "upcoming")


def schedule_state(
    *,
    started_at: datetime,
    interval_days: int,
    last_completed_at: datetime | None,
    open_link: bool,
    consent_withdrawn: bool,
    now: datetime,
) -> tuple[str, datetime | None]:
    """Return (state, next due date). Next date is None while a link is open."""
    if consent_withdrawn:
        return "consent_withdrawn", None
    if open_link:
        return "waiting", None
    if last_completed_at is not None:
        next_due = svc.aware(last_completed_at) + timedelta(days=interval_days)
    else:
        next_due = svc.aware(started_at)
    return ("due" if next_due <= now else "upcoming"), next_due


@dataclass
class ScheduleView:
    schedule: PsychosocialSchedule
    state: str
    next_due_at: datetime | None
    last_completed_at: datetime | None


async def upsert_schedules(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    patient_id: uuid.UUID,
    instrument_ids: list[str],
    interval_days: int,
) -> list[PsychosocialSchedule]:
    """Start or change the repeat for each screener. The caller commits."""
    existing = {
        s.instrument_id: s
        for s in (
            await db.scalars(
                select(PsychosocialSchedule).where(
                    PsychosocialSchedule.clinic_id == clinic_id,
                    PsychosocialSchedule.patient_id == patient_id,
                    PsychosocialSchedule.instrument_id.in_(instrument_ids),
                    PsychosocialSchedule.stopped_at.is_(None),
                )
            )
        ).all()
    }
    out = []
    for instrument_id in instrument_ids:
        schedule = existing.get(instrument_id)
        if schedule is None:
            schedule = PsychosocialSchedule(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                patient_id=patient_id,
                instrument_id=instrument_id,
                interval_days=interval_days,
                created_by=user_id,
            )
            db.add(schedule)
        else:
            schedule.interval_days = interval_days
        out.append(schedule)
    return out


async def _evaluate(
    db: AsyncSession, clinic_id: uuid.UUID, schedules: list[PsychosocialSchedule]
) -> list[ScheduleView]:
    if not schedules:
        return []
    now = svc.utcnow()
    patient_ids = {s.patient_id for s in schedules}

    last_rows = await db.execute(
        select(
            PsychosocialSession.patient_id,
            PsychosocialSession.instrument_id,
            func.max(PsychosocialSession.completed_at),
        )
        .where(
            PsychosocialSession.clinic_id == clinic_id,
            PsychosocialSession.patient_id.in_(patient_ids),
            PsychosocialSession.status == "completed",
        )
        .group_by(PsychosocialSession.patient_id, PsychosocialSession.instrument_id)
    )
    last = {(p, i): t for p, i, t in last_rows}

    open_rows = await db.execute(
        select(PsychosocialSession.patient_id, PsychosocialSession.instrument_id)
        .join(
            PsychosocialAssignment,
            and_(
                PsychosocialAssignment.id == PsychosocialSession.assignment_id,
                PsychosocialAssignment.status == "active",
                PsychosocialAssignment.expires_at > now,
            ),
        )
        .where(
            PsychosocialSession.clinic_id == clinic_id,
            PsychosocialSession.patient_id.in_(patient_ids),
            PsychosocialSession.status.in_(("pending", "in_progress")),
        )
        .distinct()
    )
    open_links = {(p, i) for p, i in open_rows}

    consents = (
        await db.scalars(
            select(PsychosocialConsent)
            .where(
                PsychosocialConsent.clinic_id == clinic_id,
                PsychosocialConsent.patient_id.in_(patient_ids),
            )
            .order_by(PsychosocialConsent.recorded_at)
        )
    ).all()
    latest_consent = {c.patient_id: c.status for c in consents}

    views = []
    for s in schedules:
        key = (s.patient_id, s.instrument_id)
        state, next_due = schedule_state(
            started_at=s.created_at,
            interval_days=s.interval_days,
            last_completed_at=last.get(key),
            open_link=key in open_links,
            consent_withdrawn=latest_consent.get(s.patient_id) == "withdrawn",
            now=now,
        )
        views.append(ScheduleView(s, state, next_due, last.get(key)))
    return views


async def list_patient_schedules(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[ScheduleView]:
    await svc.get_patient(db, clinic_id, patient_id)
    schedules = (
        await db.scalars(
            select(PsychosocialSchedule)
            .where(
                PsychosocialSchedule.clinic_id == clinic_id,
                PsychosocialSchedule.patient_id == patient_id,
                PsychosocialSchedule.stopped_at.is_(None),
            )
        )
    ).all()
    # Rows saved together share created_at, so the screener order breaks ties.
    ordered = sorted(
        schedules,
        key=lambda s: (
            s.created_at,
            INSTRUMENT_ORDER.index(s.instrument_id) if s.instrument_id in INSTRUMENT_ORDER else 99,
        ),
    )
    return await _evaluate(db, clinic_id, ordered)


async def clinic_due(db: AsyncSession, *, clinic_id: uuid.UUID) -> list[tuple[ScheduleView, str]]:
    """Every due schedule in the clinic with the patient's name, most overdue first."""
    rows = (
        await db.execute(
            select(PsychosocialSchedule, Patient.first_name, Patient.last_name)
            .join(Patient, Patient.id == PsychosocialSchedule.patient_id)
            .where(
                PsychosocialSchedule.clinic_id == clinic_id,
                PsychosocialSchedule.stopped_at.is_(None),
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
            )
        )
    ).all()
    names = {s.id: f"{first} {last}".strip() for s, first, last in rows}
    views = await _evaluate(db, clinic_id, [s for s, _, _ in rows])
    due = [v for v in views if v.state == "due"]
    due.sort(key=lambda v: (v.next_due_at, names[v.schedule.id]))
    return [(v, names[v.schedule.id]) for v in due]


async def stop_schedule(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, schedule_id: uuid.UUID
) -> PsychosocialSchedule:
    schedule = await db.scalar(
        select(PsychosocialSchedule).where(
            PsychosocialSchedule.id == schedule_id,
            PsychosocialSchedule.clinic_id == clinic_id,
        )
    )
    if schedule is None:
        raise svc.error(status.HTTP_404_NOT_FOUND, "SCHEDULE_NOT_FOUND", "Repeat schedule not found.")
    if schedule.stopped_at is not None:
        raise svc.error(status.HTTP_409_CONFLICT, "SCHEDULE_STOPPED", "This repeat is already stopped.")
    schedule.stopped_at = svc.utcnow()
    schedule.stopped_by = user_id
    await db.commit()
    await svc.audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.schedule_stopped",
        entity_type="psychosocial_schedule",
        entity_id=schedule.id,
        details={"patient_id": str(schedule.patient_id), "instrument": schedule.instrument_id},
    )
    return schedule
