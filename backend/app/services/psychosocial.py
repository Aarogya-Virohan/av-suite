"""Tool 03 business logic: assignments, patient screener flow, review.

Routers stay thin. Everything that decides state lives here so the rules
(strict answer order, immutability, consent, clinic isolation) are tested in
one place.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, desc, false, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementStatus
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.product import WorkspaceProduct
from app.models.psychosocial import (
    PsychosocialAssignment,
    PsychosocialConsent,
    PsychosocialConsentRequest,
    PsychosocialReferralAction,
    PsychosocialSchedule,
    PsychosocialSession,
    PsychosocialSessionReview,
)
from app.models.user import User
from app.repositories.audit import AuditLogRepository
from app.screening.consent import CONSENT_TEXT_VERSION
from app.screening import registry
from app.screening.registry import get_instrument
from app.screening.scoring import ScoringError, score
from app.screening.types import Instrument, Item
from app.services.audit import AuditLogService

LINK_TTL_DAYS_DEFAULT = 7  # F5 default, pending founder sign-off
LINK_TTL_DAYS_MAX = 30
PRODUCT_ID = "psycho-social-screening"
# Founders' suggestion (7 Nov): warn before sending the same screener again
# within this window. PHQ-9 and GAD-7 ask about the last 2 weeks.
RECENT_SEND_DAYS = 14


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; treat them as UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def screener_path(token: str) -> str:
    return f"/screener/{token}"


async def audit(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    details: dict[str, Any] | None = None,
) -> None:
    # Details never carry scores, bands or flags: admins can read the audit
    # log, and SRS 3.2 keeps individual results away from them.
    await AuditLogService(AuditLogRepository(db)).log_event(
        clinic_id=clinic_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )


def ordered_items(instrument: Instrument) -> tuple[Item, ...]:
    return instrument.items


def next_item(instrument: Instrument, responses: dict[str, Any]) -> Item | None:
    for item in ordered_items(instrument):
        if item.id not in responses:
            return item
    return None


def scored_complete(instrument: Instrument, responses: dict[str, Any]) -> bool:
    return all(item.id in responses for item in instrument.scored_items)


def serialise_result(result) -> dict[str, Any]:
    data = asdict(result)
    data["scales"] = [dict(s) for s in data["scales"]]
    data["reasons"] = list(data["reasons"])
    return data


# ---------------------------------------------------------------------------
# lookups
# ---------------------------------------------------------------------------
async def get_patient(db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
    patient = await db.scalar(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )
    )
    if patient is None:
        raise error(status.HTTP_404_NOT_FOUND, "PATIENT_NOT_FOUND", "Patient not found.")
    return patient


async def latest_consent(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> PsychosocialConsent | None:
    return await db.scalar(
        select(PsychosocialConsent)
        .where(
            PsychosocialConsent.clinic_id == clinic_id,
            PsychosocialConsent.patient_id == patient_id,
        )
        .order_by(desc(PsychosocialConsent.recorded_at))
        .limit(1)
    )


def consent_satisfied(consent: PsychosocialConsent | None) -> bool:
    return (
        consent is not None
        and consent.status == "granted"
        and consent.text_version == CONSENT_TEXT_VERSION
    )


def scope_filter(scope: CapabilityScope, user_id: uuid.UUID):
    if scope == CapabilityScope.ALL:
        return None
    if scope == CapabilityScope.OWN:
        return PsychosocialSession.assigned_by == user_id
    return false()


# ---------------------------------------------------------------------------
# physio side
# ---------------------------------------------------------------------------
async def create_assignment(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    patient_id: uuid.UUID,
    instrument_ids: list[str],
    expires_in_days: int,
    repeat_every_days: int | None = None,
    allow_recent: bool = False,
) -> tuple[PsychosocialAssignment, str]:
    await get_patient(db, clinic_id, patient_id)

    if not instrument_ids or len(set(instrument_ids)) != len(instrument_ids):
        raise error(422, "INVALID_INSTRUMENTS", "Choose one or more different screeners.")
    instruments: list[Instrument] = []
    for instrument_id in instrument_ids:
        try:
            instruments.append(get_instrument(instrument_id))
        except KeyError:
            raise error(422, "INVALID_INSTRUMENTS", f"Unknown screener: {instrument_id}") from None
        if not registry.is_sendable(instrument_id):
            # S-D-031: kept for past results, no longer sent.
            raise error(
                422,
                "INSTRUMENT_RETIRED",
                f"{instruments[-1].short_name} is no longer sent. Choose PHQ-9 and GAD-7.",
            )
    if not 1 <= expires_in_days <= LINK_TTL_DAYS_MAX:
        raise error(422, "INVALID_EXPIRY", f"Link expiry must be 1 to {LINK_TTL_DAYS_MAX} days.")

    consent = await latest_consent(db, clinic_id, patient_id)
    if consent is not None and consent.status == "withdrawn":
        raise error(
            status.HTTP_409_CONFLICT,
            "CONSENT_WITHDRAWN",
            "This patient has withdrawn consent for screening. No new screeners can be sent.",
        )

    if not allow_recent:
        recent = await recently_sent(db, clinic_id, patient_id, [i.id for i in instruments])
        if recent:
            names = ", ".join(get_instrument(r["instrument_id"]).short_name for r in recent)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "RECENTLY_SENT",
                    "message": (
                        f"{names} was already sent to this patient in the last {RECENT_SEND_DAYS} days. "
                        "These questionnaires ask about the last 2 weeks, so an earlier repeat adds little."
                    ),
                    "recent": recent,
                },
            )

    token, token_hash = new_token()
    assignment = PsychosocialAssignment(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        assigned_by=user_id,
        token_hash=token_hash,
        status="active",
        expires_at=utcnow() + timedelta(days=expires_in_days),
    )
    assignment.sessions = [
        PsychosocialSession(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patient_id,
            assigned_by=user_id,
            position=index,
            instrument_id=instrument.id,
            instrument_version=instrument.version,
            status="pending",
            responses={},
        )
        for index, instrument in enumerate(instruments)
    ]
    db.add(assignment)
    if repeat_every_days is not None:
        # Same transaction: the link and its repeat are saved together.
        from app.services.psychosocial_schedule import upsert_schedules

        await upsert_schedules(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            patient_id=patient_id,
            instrument_ids=instrument_ids,
            interval_days=repeat_every_days,
        )
    await db.commit()
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.assigned",
        entity_type="psychosocial_assignment",
        entity_id=assignment.id,
        details={"patient_id": str(patient_id), "instruments": instrument_ids},
    )
    if repeat_every_days is not None:
        await audit(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            action="psychosocial.schedule_set",
            entity_type="patient",
            entity_id=patient_id,
            details={
                "patient_id": str(patient_id),
                "instruments": instrument_ids,
                "interval_days": repeat_every_days,
            },
        )
    return assignment, token


async def get_assignment_for_staff(
    db: AsyncSession, clinic_id: uuid.UUID, assignment_id: uuid.UUID
) -> PsychosocialAssignment:
    assignment = await db.scalar(
        select(PsychosocialAssignment).where(
            PsychosocialAssignment.id == assignment_id,
            PsychosocialAssignment.clinic_id == clinic_id,
        )
    )
    if assignment is None:
        raise error(status.HTTP_404_NOT_FOUND, "ASSIGNMENT_NOT_FOUND", "Screener link not found.")
    return assignment


def assignment_started(assignment: PsychosocialAssignment) -> bool:
    return any(s.status != "pending" or s.responses for s in assignment.sessions)


async def cancel_assignment(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, assignment_id: uuid.UUID
) -> PsychosocialAssignment:
    assignment = await get_assignment_for_staff(db, clinic_id, assignment_id)
    if assignment.status != "active":
        raise error(status.HTTP_409_CONFLICT, "NOT_CANCELLABLE", "This screener is no longer active.")
    if assignment_started(assignment):
        raise error(
            status.HTTP_409_CONFLICT,
            "ALREADY_STARTED",
            "The patient has already started this screener, so it cannot be cancelled.",
        )
    now = utcnow()
    assignment.status = "cancelled"
    assignment.cancelled_at = now
    assignment.cancelled_by = user_id
    for session in assignment.sessions:
        session.status = "cancelled"
    await db.commit()
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.cancelled",
        entity_type="psychosocial_assignment",
        entity_id=assignment.id,
        details={"patient_id": str(assignment.patient_id)},
    )
    return assignment


async def rotate_link(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    assignment_id: uuid.UUID,
    expires_in_days: int,
) -> tuple[PsychosocialAssignment, str]:
    """Issue a fresh link. The old token stops working immediately."""
    assignment = await get_assignment_for_staff(db, clinic_id, assignment_id)
    if assignment.status != "active":
        raise error(status.HTTP_409_CONFLICT, "NOT_ACTIVE", "This screener is no longer active.")
    if not 1 <= expires_in_days <= LINK_TTL_DAYS_MAX:
        raise error(422, "INVALID_EXPIRY", f"Link expiry must be 1 to {LINK_TTL_DAYS_MAX} days.")
    consent = await latest_consent(db, clinic_id, assignment.patient_id)
    if consent is not None and consent.status == "withdrawn":
        raise error(status.HTTP_409_CONFLICT, "CONSENT_WITHDRAWN", "This patient has withdrawn consent.")
    token, token_hash = new_token()
    assignment.token_hash = token_hash
    assignment.expires_at = utcnow() + timedelta(days=expires_in_days)
    await db.commit()
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.link_reissued",
        entity_type="psychosocial_assignment",
        entity_id=assignment.id,
        details={"patient_id": str(assignment.patient_id)},
    )
    return assignment, token


async def list_patient_assignments(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    scope: CapabilityScope,
    user_id: uuid.UUID,
) -> list[PsychosocialAssignment]:
    await get_patient(db, clinic_id, patient_id)
    stmt = (
        select(PsychosocialAssignment)
        .where(
            PsychosocialAssignment.clinic_id == clinic_id,
            PsychosocialAssignment.patient_id == patient_id,
        )
        .order_by(desc(PsychosocialAssignment.created_at))
    )
    if scope == CapabilityScope.OWN:
        stmt = stmt.where(PsychosocialAssignment.assigned_by == user_id)
    elif scope != CapabilityScope.ALL:
        return []
    return list((await db.scalars(stmt)).all())


async def list_clinic_sessions(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    scope: CapabilityScope,
    user_id: uuid.UUID,
    status_filter: str | None,
    flagged_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[tuple[PsychosocialSession, Patient, PsychosocialAssignment]], int]:
    conditions = [
        PsychosocialSession.clinic_id == clinic_id,
        Patient.deleted_at.is_(None),
    ]
    scoped = scope_filter(scope, user_id)
    if scoped is not None:
        conditions.append(scoped)
    if status_filter:
        conditions.append(PsychosocialSession.status == status_filter)
    if flagged_only:
        conditions.append(PsychosocialSession.referral_flag.is_(True))

    base = (
        select(PsychosocialSession, Patient, PsychosocialAssignment)
        .join(Patient, Patient.id == PsychosocialSession.patient_id)
        .join(PsychosocialAssignment, PsychosocialAssignment.id == PsychosocialSession.assignment_id)
        .where(and_(*conditions))
    )
    total = await db.scalar(
        select(func.count())
        .select_from(PsychosocialSession)
        .join(Patient, Patient.id == PsychosocialSession.patient_id)
        .where(and_(*conditions))
    )
    rows = await db.execute(
        base.order_by(
            desc(PsychosocialSession.risk_item_flag),
            desc(func.coalesce(PsychosocialSession.completed_at, PsychosocialSession.created_at)),
        )
        .limit(limit)
        .offset(offset)
    )
    return [tuple(row) for row in rows.all()], int(total or 0)


async def get_session_for_staff(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    session_id: uuid.UUID,
    scope: CapabilityScope,
    user_id: uuid.UUID,
) -> PsychosocialSession:
    conditions = [
        PsychosocialSession.id == session_id,
        PsychosocialSession.clinic_id == clinic_id,
    ]
    scoped = scope_filter(scope, user_id)
    if scoped is not None:
        conditions.append(scoped)
    session = await db.scalar(select(PsychosocialSession).where(*conditions))
    if session is None:
        raise error(status.HTTP_404_NOT_FOUND, "SESSION_NOT_FOUND", "Screening session not found.")
    return session


async def baseline_for(db: AsyncSession, session: PsychosocialSession) -> PsychosocialSession | None:
    """First completed session for this patient and instrument (SRS 2.1)."""
    return await db.scalar(
        select(PsychosocialSession)
        .where(
            PsychosocialSession.clinic_id == session.clinic_id,
            PsychosocialSession.patient_id == session.patient_id,
            PsychosocialSession.instrument_id == session.instrument_id,
            PsychosocialSession.status == "completed",
        )
        .order_by(PsychosocialSession.completed_at, PsychosocialSession.id)
        .limit(1)
    )


async def referral_actions_for_sessions(
    db: AsyncSession, clinic_id: uuid.UUID, session_ids: list[uuid.UUID]
) -> list[PsychosocialReferralAction]:
    if not session_ids:
        return []
    return list(
        (
            await db.scalars(
                select(PsychosocialReferralAction)
                .where(
                    PsychosocialReferralAction.clinic_id == clinic_id,
                    PsychosocialReferralAction.session_id.in_(session_ids),
                )
                .order_by(PsychosocialReferralAction.recorded_at)
            )
        ).all()
    )


async def log_referral_action(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    session: PsychosocialSession,
    action: str,
    note: str | None,
    contact=None,
) -> PsychosocialReferralAction:
    """``contact`` is an active PsychosocialReferralContact of this clinic, or None."""
    if session.status != "completed" or not session.referral_flag:
        raise error(
            status.HTTP_409_CONFLICT,
            "NO_REFERRAL_FLAG",
            "A referral action can only be logged for a completed, flagged result.",
        )
    record = PsychosocialReferralAction(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=session.patient_id,
        session_id=session.id,
        action=action,
        note=(note or "").strip() or None,
        recorded_by=user_id,
        recorded_at=utcnow(),
        contact_id=contact.id if contact is not None else None,
        contact_name=contact.name if contact is not None else None,
        contact_role=contact.role if contact is not None else None,
    )
    db.add(record)
    await db.commit()
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.referral_logged",
        entity_type="psychosocial_session",
        entity_id=session.id,
        details={
            "patient_id": str(session.patient_id),
            "contact_id": str(contact.id) if contact is not None else None,
        },
    )
    return record


async def patient_summary(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    scope: CapabilityScope,
    user_id: uuid.UUID,
) -> list[PsychosocialSession]:
    """CDSS contract: latest completed session per instrument (SRS 5.1)."""
    await get_patient(db, clinic_id, patient_id)
    conditions = [
        PsychosocialSession.clinic_id == clinic_id,
        PsychosocialSession.patient_id == patient_id,
        PsychosocialSession.status == "completed",
    ]
    scoped = scope_filter(scope, user_id)
    if scoped is not None:
        conditions.append(scoped)
    sessions = (
        await db.scalars(
            select(PsychosocialSession)
            .where(*conditions)
            .order_by(desc(PsychosocialSession.completed_at))
        )
    ).all()
    latest: dict[str, PsychosocialSession] = {}
    for session in sessions:
        latest.setdefault(session.instrument_id, session)
    return list(latest.values())


async def completed_sessions(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    scope: CapabilityScope,
    user_id: uuid.UUID,
) -> list[PsychosocialSession]:
    """Every completed session the caller may see, oldest first (trend, report)."""
    await get_patient(db, clinic_id, patient_id)
    conditions = [
        PsychosocialSession.clinic_id == clinic_id,
        PsychosocialSession.patient_id == patient_id,
        PsychosocialSession.status == "completed",
    ]
    scoped = scope_filter(scope, user_id)
    if scoped is not None:
        conditions.append(scoped)
    return list(
        (
            await db.scalars(
                select(PsychosocialSession)
                .where(*conditions)
                .order_by(PsychosocialSession.completed_at)
            )
        ).all()
    )


# ---------------------------------------------------------------------------
# deletion on request (SRS 3.2, S-D-024)
# ---------------------------------------------------------------------------
async def _count(db: AsyncSession, model, clinic_id: uuid.UUID, patient_id: uuid.UUID, *extra) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(model)
        .where(model.clinic_id == clinic_id, model.patient_id == patient_id, *extra)
    ) or 0


async def screening_data_counts(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> dict[str, Any]:
    """What a deletion would remove. Counts only, no clinical values."""
    await get_patient(db, clinic_id, patient_id)
    consent = await latest_consent(db, clinic_id, patient_id)
    withdrawal_on_file = consent is not None and consent.status == "withdrawn"
    consents = await _count(db, PsychosocialConsent, clinic_id, patient_id)
    return {
        "patient_id": patient_id,
        "links": await _count(db, PsychosocialAssignment, clinic_id, patient_id),
        "screeners": await _count(db, PsychosocialSession, clinic_id, patient_id),
        "referral_actions": await _count(db, PsychosocialReferralAction, clinic_id, patient_id),
        "schedules": await _count(db, PsychosocialSchedule, clinic_id, patient_id),
        # The kept withdrawal record is not counted as deleted.
        "consent_records": consents - 1 if withdrawal_on_file else consents,
        "withdrawal_on_file": withdrawal_on_file,
    }


async def delete_patient_screening_data(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, patient_id: uuid.UUID
) -> dict[str, Any]:
    """Erase every screening record for one patient, in one transaction.

    Removed: links, screeners (answers and results), referral actions, review
    marks, re-consent links, repeat schedules and consent records. If the patient's latest consent decision is a
    withdrawal, that single record is kept (status, text version, date) so
    the clinic cannot send a new screener without the patient. Deleting a
    completed session is allowed: the immutability trigger blocks UPDATE only.
    The audit event holds counts, never clinical values.
    """
    counts = await screening_data_counts(db, clinic_id=clinic_id, patient_id=patient_id)
    keep_id: uuid.UUID | None = None
    if counts["withdrawal_on_file"]:
        keep_id = (await latest_consent(db, clinic_id, patient_id)).id

    def scoped(model):
        return (model.clinic_id == clinic_id, model.patient_id == patient_id)

    # Child rows first, so the result does not depend on FK cascades.
    await db.execute(
        delete(PsychosocialConsentRequest)
        .where(*scoped(PsychosocialConsentRequest))
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(
        delete(PsychosocialSessionReview)
        .where(*scoped(PsychosocialSessionReview))
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(
        delete(PsychosocialReferralAction)
        .where(*scoped(PsychosocialReferralAction))
        .execution_options(synchronize_session="fetch")
    )
    consent_filter = list(scoped(PsychosocialConsent))
    if keep_id is not None:
        consent_filter.append(PsychosocialConsent.id != keep_id)
    await db.execute(
        delete(PsychosocialConsent).where(*consent_filter).execution_options(synchronize_session="fetch")
    )
    if keep_id is not None:
        # Its link is about to go. Keep the decision, drop the reference.
        await db.execute(
            update(PsychosocialConsent)
            .where(PsychosocialConsent.id == keep_id)
            .values(assignment_id=None)
            .execution_options(synchronize_session="fetch")
        )
    await db.execute(
        delete(PsychosocialSession)
        .where(*scoped(PsychosocialSession))
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(
        delete(PsychosocialAssignment)
        .where(*scoped(PsychosocialAssignment))
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(
        delete(PsychosocialSchedule)
        .where(*scoped(PsychosocialSchedule))
        .execution_options(synchronize_session="fetch")
    )
    await db.commit()

    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.data_deleted",
        entity_type="patient",
        entity_id=patient_id,
        details={
            "patient_id": str(patient_id),
            "links": counts["links"],
            "screeners": counts["screeners"],
            "referral_actions": counts["referral_actions"],
            "schedules": counts["schedules"],
            "consent_records": counts["consent_records"],
            "withdrawal_kept": counts["withdrawal_on_file"],
        },
    )
    return counts


async def recently_sent(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID, instrument_ids: list[str]
) -> list[dict[str, str]]:
    """Screeners sent within RECENT_SEND_DAYS, not cancelled: latest send per screener."""
    since = utcnow() - timedelta(days=RECENT_SEND_DAYS)
    rows = await db.execute(
        select(PsychosocialSession.instrument_id, func.max(PsychosocialAssignment.created_at))
        .join(PsychosocialAssignment, PsychosocialAssignment.id == PsychosocialSession.assignment_id)
        .where(
            PsychosocialSession.clinic_id == clinic_id,
            PsychosocialSession.patient_id == patient_id,
            PsychosocialSession.instrument_id.in_(instrument_ids),
            PsychosocialSession.status != "cancelled",
            PsychosocialAssignment.created_at >= since,
        )
        .group_by(PsychosocialSession.instrument_id)
    )
    found = {instrument_id: aware(sent_at) for instrument_id, sent_at in rows}
    return [
        {"instrument_id": i, "sent_at": found[i].isoformat()} for i in instrument_ids if i in found
    ]


# ---------------------------------------------------------------------------
# re-consent after a withdrawal (Q7 = 7B, S-D-037)
# ---------------------------------------------------------------------------
def consent_request_path(token: str) -> str:
    return f"/consent/{token}"


def consent_request_state(request: PsychosocialConsentRequest) -> str:
    if request.status == "pending" and aware(request.expires_at) <= utcnow():
        return "expired"
    return request.status


async def latest_consent_request(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> PsychosocialConsentRequest | None:
    return await db.scalar(
        select(PsychosocialConsentRequest)
        .where(
            PsychosocialConsentRequest.clinic_id == clinic_id,
            PsychosocialConsentRequest.patient_id == patient_id,
        )
        .order_by(desc(PsychosocialConsentRequest.created_at), desc(PsychosocialConsentRequest.id))
        .limit(1)
    )


async def create_consent_request(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    patient_id: uuid.UUID,
    expires_in_days: int,
) -> tuple[PsychosocialConsentRequest, str]:
    """One open request per patient: a new one stops the previous link."""
    await get_patient(db, clinic_id, patient_id)
    if not 1 <= expires_in_days <= LINK_TTL_DAYS_MAX:
        raise error(422, "INVALID_EXPIRY", f"Link expiry must be 1 to {LINK_TTL_DAYS_MAX} days.")
    consent = await latest_consent(db, clinic_id, patient_id)
    if consent is None or consent.status != "withdrawn":
        raise error(
            status.HTTP_409_CONFLICT,
            "CONSENT_NOT_WITHDRAWN",
            "This patient has not withdrawn consent. Send a screener instead.",
        )
    now = utcnow()
    await db.execute(
        update(PsychosocialConsentRequest)
        .where(
            PsychosocialConsentRequest.clinic_id == clinic_id,
            PsychosocialConsentRequest.patient_id == patient_id,
            PsychosocialConsentRequest.status == "pending",
        )
        .values(status="cancelled")
        .execution_options(synchronize_session="fetch")
    )
    token, token_hash = new_token()
    request = PsychosocialConsentRequest(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        requested_by=user_id,
        token_hash=token_hash,
        status="pending",
        expires_at=now + timedelta(days=expires_in_days),
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.reconsent_requested",
        entity_type="psychosocial_consent_request",
        entity_id=request.id,
        details={"patient_id": str(patient_id)},
    )
    return request, token


async def resolve_consent_request(db: AsyncSession, token: str) -> PsychosocialConsentRequest:
    request = await db.scalar(
        select(PsychosocialConsentRequest).where(PsychosocialConsentRequest.token_hash == hash_token(token))
    )
    if request is None:
        raise error(status.HTTP_404_NOT_FOUND, "LINK_NOT_FOUND", "This link is not valid.")
    if not await screening_enabled(db, request.clinic_id):
        raise error(status.HTTP_403_FORBIDDEN, "SCREENING_UNAVAILABLE", "This screening is not available right now.")
    if request.status == "cancelled":
        raise error(status.HTTP_410_GONE, "LINK_CANCELLED", "This link is no longer active.")
    if consent_request_state(request) == "expired":
        raise error(status.HTTP_410_GONE, "LINK_EXPIRED", "This link has expired.")
    return request


async def answer_consent_request(
    db: AsyncSession, token: str, *, accept: bool, text_version: str | None
) -> PsychosocialConsentRequest:
    """Record the patient's choice. Repeating the same choice is a no-op."""
    request = await resolve_consent_request(db, token)
    choice = "granted" if accept else "declined"
    if request.status != "pending":
        if request.status == choice:
            return request
        raise error(status.HTTP_409_CONFLICT, "ALREADY_ANSWERED", "You have already answered this request.")
    if accept and text_version != CONSENT_TEXT_VERSION:
        raise error(
            status.HTTP_409_CONFLICT,
            "CONSENT_TEXT_CHANGED",
            "The consent text has been updated. Please reload the page.",
        )
    now = utcnow()
    request.status = choice
    request.answered_at = now
    if accept:
        db.add(
            PsychosocialConsent(
                id=uuid.uuid4(),
                clinic_id=request.clinic_id,
                patient_id=request.patient_id,
                assignment_id=None,
                status="granted",
                text_version=CONSENT_TEXT_VERSION,
                recorded_at=now,
            )
        )
    await db.commit()
    await audit(
        db,
        clinic_id=request.clinic_id,
        user_id=None,
        action="psychosocial.reconsent_granted" if accept else "psychosocial.reconsent_declined",
        entity_type="psychosocial_consent_request",
        entity_id=request.id,
        details={"patient_id": str(request.patient_id)}
        | ({"text_version": CONSENT_TEXT_VERSION} if accept else {}),
    )
    return request


# ---------------------------------------------------------------------------
# priority review (F4 = 4A, S-D-033)
# ---------------------------------------------------------------------------
def risk_answered(session: PsychosocialSession) -> bool:
    """A risk item (PHQ-9 item 9) answered at or above its rule, submitted or not."""
    instrument = get_instrument(session.instrument_id, session.instrument_version)
    responses = session.responses or {}
    return any(responses.get(rule.item_id, 0) >= rule.min_value for rule in instrument.risk_item_rules)


def needs_priority_review(session: PsychosocialSession) -> bool:
    """Completed with the risk flag, or a risk answer left unsubmitted.

    Unsubmitted covers an in-progress screener and one cancelled by the
    patient's withdrawal after a risk answer: the patient saw the helpline
    card, so the provider must see it too.
    """
    if session.status == "completed":
        return bool(session.risk_item_flag)
    if session.status in ("in_progress", "cancelled"):
        return risk_answered(session)
    return False


async def record_review(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, session: PsychosocialSession
) -> None:
    """Mark a risk result as opened by a provider. Other results are not tracked."""
    if not needs_priority_review(session):
        return
    if await _reviewed(db, session):
        return
    db.add(
        PsychosocialSessionReview(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=session.patient_id,
            session_id=session.id,
            reviewed_by=user_id,
            reviewed_at=utcnow(),
        )
    )
    await db.commit()


async def _reviewed(db: AsyncSession, session: PsychosocialSession) -> bool:
    conditions = [PsychosocialSessionReview.session_id == session.id]
    if session.status == "completed" and session.completed_at is not None:
        # An earlier look at the unsubmitted answers does not count for the
        # submitted result.
        conditions.append(PsychosocialSessionReview.reviewed_at >= session.completed_at)
    return (await db.scalar(select(func.count()).select_from(PsychosocialSessionReview).where(*conditions))) > 0


async def priority_review(
    db: AsyncSession, *, clinic_id: uuid.UUID, scope: CapabilityScope, user_id: uuid.UUID
) -> list[tuple[PsychosocialSession, Patient]]:
    """Risk results no provider has opened yet, newest activity first."""
    conditions = [
        PsychosocialSession.clinic_id == clinic_id,
        Patient.deleted_at.is_(None),
        PsychosocialSession.instrument_id.in_(
            [i.id for i in registry.INSTRUMENTS.values() if i.risk_item_rules]
        ),
        (
            and_(PsychosocialSession.status == "completed", PsychosocialSession.risk_item_flag.is_(True))
            | PsychosocialSession.status.in_(("in_progress", "cancelled"))
        ),
    ]
    scoped = scope_filter(scope, user_id)
    if scoped is not None:
        conditions.append(scoped)
    rows = (
        await db.execute(
            select(PsychosocialSession, Patient)
            .join(Patient, Patient.id == PsychosocialSession.patient_id)
            .where(*conditions)
        )
    ).all()
    candidates = [(s, p) for s, p in rows if needs_priority_review(s)]
    if not candidates:
        return []
    reviews = await db.execute(
        select(PsychosocialSessionReview.session_id, func.max(PsychosocialSessionReview.reviewed_at))
        .where(
            PsychosocialSessionReview.clinic_id == clinic_id,
            PsychosocialSessionReview.session_id.in_([s.id for s, _ in candidates]),
        )
        .group_by(PsychosocialSessionReview.session_id)
    )
    last_review = {sid: aware(at) for sid, at in reviews}
    out = []
    for session, patient in candidates:
        seen = last_review.get(session.id)
        if seen is None:
            out.append((session, patient))
        elif session.status == "completed" and seen < aware(session.completed_at):
            out.append((session, patient))
    out.sort(key=lambda r: (aware(r[0].completed_at or r[0].updated_at), r[0].id), reverse=True)
    return out


# ---------------------------------------------------------------------------
# sent links tracker (F3 = enhanced 3A, S-D-032): operational status only
# ---------------------------------------------------------------------------
TRACKER_STATUSES = ("pending", "expired", "completed", "cancelled")


async def list_sent_links(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    status_filter: str | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[PsychosocialAssignment, Patient]], int]:
    """Every link the clinic sent, newest first. Never scores, answers or flags."""
    now = utcnow()
    conditions = [
        PsychosocialAssignment.clinic_id == clinic_id,
        Patient.deleted_at.is_(None),
    ]
    if status_filter == "pending":
        conditions += [PsychosocialAssignment.status == "active", PsychosocialAssignment.expires_at > now]
    elif status_filter == "expired":
        conditions += [PsychosocialAssignment.status == "active", PsychosocialAssignment.expires_at <= now]
    elif status_filter in ("completed", "cancelled"):
        conditions.append(PsychosocialAssignment.status == status_filter)
    base = (
        select(PsychosocialAssignment, Patient)
        .join(Patient, Patient.id == PsychosocialAssignment.patient_id)
        .where(*conditions)
    )
    total = await db.scalar(
        select(func.count())
        .select_from(PsychosocialAssignment)
        .join(Patient, Patient.id == PsychosocialAssignment.patient_id)
        .where(*conditions)
    )
    rows = await db.execute(
        base.order_by(desc(PsychosocialAssignment.created_at), PsychosocialAssignment.id).limit(limit).offset(offset)
    )
    return [tuple(r) for r in rows.all()], int(total or 0)


async def screening_enabled(db: AsyncSession, clinic_id: uuid.UUID) -> bool:
    return (
        await db.scalar(
            select(func.count())
            .select_from(WorkspaceProduct)
            .where(
                WorkspaceProduct.clinic_id == clinic_id,
                WorkspaceProduct.product_id == PRODUCT_ID,
                WorkspaceProduct.status == EntitlementStatus.ENABLED,
            )
        )
    ) > 0


# ---------------------------------------------------------------------------
# patient side (public, token)
# ---------------------------------------------------------------------------
async def resolve_token(
    db: AsyncSession, token: str, *, allow_completed: bool = False
) -> PsychosocialAssignment:
    assignment = await db.scalar(
        select(PsychosocialAssignment).where(PsychosocialAssignment.token_hash == hash_token(token))
    )
    if assignment is None:
        raise error(status.HTTP_404_NOT_FOUND, "LINK_NOT_FOUND", "This link is not valid.")
    if not await screening_enabled(db, assignment.clinic_id):
        # Lapsed or uninstalled: no provider would see new answers, so a risk
        # answer must not be collected (S-D-034). Checked before every other
        # state so the patient gets one clear message.
        raise error(
            status.HTTP_403_FORBIDDEN,
            "SCREENING_UNAVAILABLE",
            "This screening is not available right now.",
        )
    if assignment.status == "cancelled":
        raise error(status.HTTP_410_GONE, "LINK_CANCELLED", "This link is no longer active.")
    if assignment.status == "completed" and not allow_completed:
        raise error(status.HTTP_409_CONFLICT, "ALREADY_COMPLETED", "These questions have already been answered.")
    if assignment.status == "active" and aware(assignment.expires_at) <= utcnow():
        raise error(status.HTTP_410_GONE, "LINK_EXPIRED", "This link has expired.")
    return assignment


def current_session(assignment: PsychosocialAssignment) -> PsychosocialSession | None:
    for session in assignment.sessions:
        if session.status in ("pending", "in_progress"):
            return session
    return None


async def lock_session(db: AsyncSession, session_id: uuid.UUID) -> PsychosocialSession:
    """Row lock so two quick taps cannot both claim the same next item."""
    locked = await db.scalar(
        select(PsychosocialSession)
        .where(PsychosocialSession.id == session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert locked is not None
    return locked


async def require_consent(db: AsyncSession, assignment: PsychosocialAssignment) -> None:
    consent = await latest_consent(db, assignment.clinic_id, assignment.patient_id)
    if not consent_satisfied(consent):
        raise error(status.HTTP_403_FORBIDDEN, "CONSENT_REQUIRED", "Please confirm consent before starting.")


async def record_consent(db: AsyncSession, token: str, text_version: str) -> PsychosocialAssignment:
    assignment = await resolve_token(db, token)
    if text_version != CONSENT_TEXT_VERSION:
        raise error(
            status.HTTP_409_CONFLICT,
            "CONSENT_TEXT_CHANGED",
            "The consent text has been updated. Please reload the page.",
        )
    current = await latest_consent(db, assignment.clinic_id, assignment.patient_id)
    if consent_satisfied(current):
        return assignment  # idempotent
    db.add(
        PsychosocialConsent(
            id=uuid.uuid4(),
            clinic_id=assignment.clinic_id,
            patient_id=assignment.patient_id,
            assignment_id=assignment.id,
            status="granted",
            text_version=CONSENT_TEXT_VERSION,
            recorded_at=utcnow(),
        )
    )
    await db.commit()
    await audit(
        db,
        clinic_id=assignment.clinic_id,
        user_id=None,
        action="psychosocial.consent_granted",
        entity_type="psychosocial_assignment",
        entity_id=assignment.id,
        details={"patient_id": str(assignment.patient_id), "text_version": CONSENT_TEXT_VERSION},
    )
    return assignment


async def withdraw_consent(db: AsyncSession, token: str) -> None:
    assignment = await resolve_token(db, token)
    now = utcnow()
    db.add(
        PsychosocialConsent(
            id=uuid.uuid4(),
            clinic_id=assignment.clinic_id,
            patient_id=assignment.patient_id,
            assignment_id=assignment.id,
            status="withdrawn",
            text_version=CONSENT_TEXT_VERSION,
            recorded_at=now,
        )
    )
    # Withdrawal stops every open screener for this patient. Completed
    # results stay: deletion is a separate request (S-L-005).
    open_assignments = (
        await db.scalars(
            select(PsychosocialAssignment).where(
                PsychosocialAssignment.clinic_id == assignment.clinic_id,
                PsychosocialAssignment.patient_id == assignment.patient_id,
                PsychosocialAssignment.status == "active",
            )
        )
    ).all()
    for open_assignment in open_assignments:
        open_assignment.status = "cancelled"
        open_assignment.cancelled_at = now
        for session in open_assignment.sessions:
            if session.status in ("pending", "in_progress"):
                session.status = "cancelled"
    await db.commit()
    await audit(
        db,
        clinic_id=assignment.clinic_id,
        user_id=None,
        action="psychosocial.consent_withdrawn",
        entity_type="psychosocial_assignment",
        entity_id=assignment.id,
        details={"patient_id": str(assignment.patient_id)},
    )


def find_session(assignment: PsychosocialAssignment, instrument_id: str) -> PsychosocialSession:
    for session in assignment.sessions:
        if session.instrument_id == instrument_id:
            return session
    raise error(status.HTTP_404_NOT_FOUND, "INSTRUMENT_NOT_ASSIGNED", "This questionnaire is not part of this link.")


async def save_answer(
    db: AsyncSession, token: str, instrument_id: str, item_id: str, value: int
) -> PsychosocialSession:
    assignment = await resolve_token(db, token)
    await require_consent(db, assignment)
    target = find_session(assignment, instrument_id)
    current = current_session(assignment)
    if current is None or current.id != target.id:
        if target.status == "completed":
            raise error(status.HTTP_409_CONFLICT, "ALREADY_SUBMITTED", "This questionnaire has already been submitted.")
        raise error(status.HTTP_409_CONFLICT, "OUT_OF_ORDER", "Please finish the current questionnaire first.")

    session = await lock_session(db, target.id)
    instrument = get_instrument(session.instrument_id, session.instrument_version)
    responses = dict(session.responses or {})

    if item_id in responses:
        if responses[item_id] == value:
            return session  # retry of an answer already saved; no write
        raise error(
            status.HTTP_409_CONFLICT,
            "ANSWER_LOCKED",
            "This answer was already saved and cannot be changed.",
        )
    expected = next_item(instrument, responses)
    if expected is None or expected.id != item_id:
        raise error(status.HTTP_409_CONFLICT, "OUT_OF_ORDER", "Please answer the questions in order.")
    allowed = {option.value for option in instrument.options_for(expected)}
    if isinstance(value, bool) or value not in allowed:
        raise error(422, "INVALID_ANSWER", "That answer is not one of the options.")

    responses[item_id] = value
    session.responses = responses
    if session.status == "pending":
        session.status = "in_progress"
        session.started_at = utcnow()
    await db.commit()
    return session


async def submit_session(db: AsyncSession, token: str, instrument_id: str) -> PsychosocialAssignment:
    assignment = await resolve_token(db, token, allow_completed=True)
    target = find_session(assignment, instrument_id)
    if target.status == "completed":
        return assignment  # retry after a successful submit: same answer
    if assignment.status == "completed":
        raise error(status.HTTP_409_CONFLICT, "ALREADY_COMPLETED", "These questions have already been answered.")
    await require_consent(db, assignment)
    current = current_session(assignment)
    if current is None or current.id != target.id:
        raise error(status.HTTP_409_CONFLICT, "OUT_OF_ORDER", "Please finish the current questionnaire first.")

    session = await lock_session(db, target.id)
    instrument = get_instrument(session.instrument_id, session.instrument_version)
    responses = dict(session.responses or {})
    if not scored_complete(instrument, responses):
        raise error(status.HTTP_409_CONFLICT, "INCOMPLETE", "Please answer every question before submitting.")
    try:
        result = score(instrument, responses)
    except ScoringError as exc:  # stored data no longer valid: never guess
        raise error(status.HTTP_409_CONFLICT, "INVALID_RESPONSES", str(exc)) from exc

    session.result = serialise_result(result)
    session.referral_flag = result.referral_flag
    session.risk_item_flag = result.risk_item_flag
    session.completed_at = utcnow()
    session.status = "completed"
    await db.flush()

    await db.refresh(assignment, attribute_names=["sessions"])
    if all(s.status == "completed" for s in assignment.sessions):
        assignment.status = "completed"
    await db.commit()
    await audit(
        db,
        clinic_id=session.clinic_id,
        user_id=None,
        action="psychosocial.completed",
        entity_type="psychosocial_session",
        entity_id=session.id,
        details={"patient_id": str(session.patient_id), "instrument": session.instrument_id},
    )
    return assignment


async def clinic_name(db: AsyncSession, clinic_id: uuid.UUID) -> str:
    clinic = await db.get(Clinic, clinic_id)
    return clinic.name if clinic else ""


async def user_names(db: AsyncSession, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    ids = {u for u in user_ids if u}
    if not ids:
        return {}
    rows = await db.execute(select(User.id, User.first_name, User.last_name).where(User.id.in_(ids)))
    return {row.id: f"{row.first_name} {row.last_name}".strip() for row in rows}
