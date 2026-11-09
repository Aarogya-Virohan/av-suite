"""Provider-shared report (founders' F2 follow-up, S-D-039).

Flow: the patient answers, the provider reviews and discusses the result in
the consultation, then clicks "Share with patient", writes advice and ticks
resources. The patient gets a WhatsApp message with a link (no scores in
the message). The page asks for the year of birth when the record has one,
then shows advice, a patient-friendly summary and the resources.

Never automatic: a share exists only because a provider created it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.permission import CapabilityScope
from app.models.patient import Patient
from app.models.psychosocial import PsychosocialAssignment, PsychosocialSession, PsychosocialSharedReport
from app.screening.share import (
    ADVICE_MAX,
    CUSTOM_LINKS_MAX,
    RESOURCES_BY_KEY,
    SHAREABLE_INSTRUMENTS,
    SummaryLine,
    clean_custom_link,
    summary_line,
)
from app.services import psychosocial as svc

SHARE_TTL_DAYS_DEFAULT = 30
MAX_BIRTH_YEAR_ATTEMPTS = 5


def report_path(token: str) -> str:
    return f"/report/{token}"


def share_state(report: PsychosocialSharedReport) -> str:
    if report.revoked_at is not None:
        return "revoked"
    if report.locked_at is not None:
        return "locked"
    if svc.aware(report.expires_at) <= svc.utcnow():
        return "expired"
    return "active"


def _shareable_sessions(assignment: PsychosocialAssignment) -> list[PsychosocialSession]:
    return [
        s
        for s in sorted(assignment.sessions, key=lambda s: s.position)
        if s.status == "completed" and s.instrument_id in SHAREABLE_INSTRUMENTS
    ]


async def _visible_assignment(
    db: AsyncSession, clinic_id: uuid.UUID, assignment_id: uuid.UUID, scope: CapabilityScope, user_id: uuid.UUID
) -> PsychosocialAssignment:
    assignment = await db.scalar(
        select(PsychosocialAssignment).where(
            PsychosocialAssignment.id == assignment_id, PsychosocialAssignment.clinic_id == clinic_id
        )
    )
    visible = assignment is not None and (
        scope == CapabilityScope.ALL or (scope == CapabilityScope.OWN and assignment.assigned_by == user_id)
    )
    if not visible:
        raise svc.error(status.HTTP_404_NOT_FOUND, "ASSIGNMENT_NOT_FOUND", "Screening not found.")
    return assignment


async def create_share(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    scope: CapabilityScope,
    assignment_id: uuid.UUID,
    advice: str | None,
    resource_keys: list[str],
    custom_links: list[tuple[str, str]],
    expires_in_days: int,
) -> tuple[PsychosocialSharedReport, str]:
    assignment = await _visible_assignment(db, clinic_id, assignment_id, scope, user_id)
    patient = await svc.get_patient(db, clinic_id, assignment.patient_id)
    if not _shareable_sessions(assignment):
        raise svc.error(
            422, "NOTHING_TO_SHARE", "Only completed PHQ-9 and GAD-7 results can be shared with the patient."
        )
    advice = (advice or "").strip() or None
    if advice and len(advice) > ADVICE_MAX:
        raise svc.error(422, "ADVICE_TOO_LONG", f"Advice can be up to {ADVICE_MAX} characters.")
    unknown = sorted(set(resource_keys) - RESOURCES_BY_KEY.keys())
    if unknown:
        raise svc.error(422, "UNKNOWN_RESOURCE", f"Unknown resource: {', '.join(unknown)}")
    if len(custom_links) > CUSTOM_LINKS_MAX:
        raise svc.error(422, "TOO_MANY_LINKS", f"Add up to {CUSTOM_LINKS_MAX} links of your own.")
    links = []
    for title, url in custom_links:
        try:
            clean_title, clean_url = clean_custom_link(title, url)
        except ValueError as e:
            raise svc.error(422, "INVALID_LINK", str(e)) from None
        links.append({"title": clean_title, "url": clean_url})
    if not advice and not resource_keys and not links:
        raise svc.error(422, "EMPTY_SHARE", "Add advice or at least one resource before sharing.")
    if not 1 <= expires_in_days <= svc.LINK_TTL_DAYS_MAX:
        raise svc.error(422, "INVALID_EXPIRY", f"Link expiry must be 1 to {svc.LINK_TTL_DAYS_MAX} days.")

    token, token_hash = svc.new_token()
    report = PsychosocialSharedReport(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assignment_id=assignment.id,
        shared_by=user_id,
        token_hash=token_hash,
        advice=advice,
        # Keep the catalogue order, not the click order.
        resource_keys=[k for k in RESOURCES_BY_KEY if k in set(resource_keys)],
        custom_links=links,
        birth_year_check=patient.date_of_birth is not None,
        failed_attempts=0,
        open_count=0,
        expires_at=svc.utcnow() + timedelta(days=expires_in_days),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    await svc.audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.report_shared",
        entity_type="psychosocial_shared_report",
        entity_id=report.id,
        details={
            "patient_id": str(patient.id),
            "assignment_id": str(assignment.id),
            "resources": len(report.resource_keys) + len(links),
            "has_advice": advice is not None,
        },
    )
    return report, token


async def list_shares(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID, scope: CapabilityScope, user_id: uuid.UUID
) -> list[PsychosocialSharedReport]:
    await svc.get_patient(db, clinic_id, patient_id)
    conditions = [
        PsychosocialSharedReport.clinic_id == clinic_id,
        PsychosocialSharedReport.patient_id == patient_id,
    ]
    if scope == CapabilityScope.OWN:
        conditions.append(PsychosocialSharedReport.shared_by == user_id)
    elif scope != CapabilityScope.ALL:
        return []
    rows = await db.scalars(
        select(PsychosocialSharedReport)
        .where(*conditions)
        .order_by(desc(PsychosocialSharedReport.created_at), PsychosocialSharedReport.id)
    )
    return list(rows)


async def revoke_share(
    db: AsyncSession, *, clinic_id: uuid.UUID, share_id: uuid.UUID, scope: CapabilityScope, user_id: uuid.UUID
) -> PsychosocialSharedReport:
    report = await db.scalar(
        select(PsychosocialSharedReport).where(
            PsychosocialSharedReport.id == share_id, PsychosocialSharedReport.clinic_id == clinic_id
        )
    )
    visible = report is not None and (
        scope == CapabilityScope.ALL or (scope == CapabilityScope.OWN and report.shared_by == user_id)
    )
    if not visible:
        raise svc.error(status.HTTP_404_NOT_FOUND, "SHARE_NOT_FOUND", "Shared report not found.")
    if report.revoked_at is None:
        report.revoked_at = svc.utcnow()
        await db.commit()
        await svc.audit(
            db,
            clinic_id=clinic_id,
            user_id=user_id,
            action="psychosocial.report_revoked",
            entity_type="psychosocial_shared_report",
            entity_id=report.id,
            details={"patient_id": str(report.patient_id)},
        )
    return report


# ---------------------------------------------------------------------------
# patient side (public, token)
# ---------------------------------------------------------------------------
async def resolve_share(db: AsyncSession, token: str) -> PsychosocialSharedReport:
    report = await db.scalar(
        select(PsychosocialSharedReport).where(PsychosocialSharedReport.token_hash == svc.hash_token(token))
    )
    if report is None:
        raise svc.error(status.HTTP_404_NOT_FOUND, "LINK_NOT_FOUND", "This link is not valid.")
    if not await svc.screening_enabled(db, report.clinic_id):
        raise svc.error(status.HTTP_403_FORBIDDEN, "SCREENING_UNAVAILABLE", "This report is not available right now.")
    state = share_state(report)
    if state == "revoked":
        raise svc.error(status.HTTP_410_GONE, "LINK_CANCELLED", "This link is no longer active.")
    if state == "expired":
        raise svc.error(status.HTTP_410_GONE, "LINK_EXPIRED", "This link has expired.")
    if state == "locked":
        raise svc.error(status.HTTP_423_LOCKED, "LINK_LOCKED", "This link is locked.")
    return report


@dataclass(frozen=True)
class OpenedReport:
    report: PsychosocialSharedReport
    clinic_name: str
    provider_name: str | None
    summary: list[SummaryLine]


async def open_share(db: AsyncSession, token: str, birth_year: int | None) -> OpenedReport:
    report = await resolve_share(db, token)
    if report.birth_year_check:
        patient = await db.get(Patient, report.patient_id)
        expected = patient.date_of_birth.year if patient and patient.date_of_birth else None
        if expected is None or birth_year != expected:
            report.failed_attempts += 1
            locked = report.failed_attempts >= MAX_BIRTH_YEAR_ATTEMPTS
            if locked:
                report.locked_at = svc.utcnow()
            await db.commit()
            if locked:
                await svc.audit(
                    db,
                    clinic_id=report.clinic_id,
                    user_id=None,
                    action="psychosocial.report_locked",
                    entity_type="psychosocial_shared_report",
                    entity_id=report.id,
                    details={"patient_id": str(report.patient_id)},
                )
                raise svc.error(status.HTTP_423_LOCKED, "LINK_LOCKED", "This link is locked.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "WRONG_BIRTH_YEAR",
                    "message": "That year does not match our records.",
                    "attempts_left": MAX_BIRTH_YEAR_ATTEMPTS - report.failed_attempts,
                },
            )

    assignment = await db.get(PsychosocialAssignment, report.assignment_id)
    summary = [summary_line(s.instrument_id, s.instrument_version, s.responses) for s in _shareable_sessions(assignment)]
    now = svc.utcnow()
    first = report.first_opened_at is None
    report.first_opened_at = report.first_opened_at or now
    report.open_count += 1
    report.failed_attempts = 0
    await db.commit()
    if first:
        await svc.audit(
            db,
            clinic_id=report.clinic_id,
            user_id=None,
            action="psychosocial.report_opened",
            entity_type="psychosocial_shared_report",
            entity_id=report.id,
            details={"patient_id": str(report.patient_id)},
        )
    names = await svc.user_names(db, {report.shared_by} if report.shared_by else set())
    return OpenedReport(
        report=report,
        clinic_name=await svc.clinic_name(db, report.clinic_id),
        provider_name=names.get(report.shared_by) if report.shared_by else None,
        summary=summary,
    )
