"""Tool 03 staff endpoints (authenticated, clinic-scoped, capability-gated)."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import AuthenticatedContextDep, SessionDep, require_capability
from app.enums.permission import CapabilityScope
from app.models.patient import Patient
from app.models.psychosocial import PsychosocialAssignment, PsychosocialSession
from app.schemas.envelope import MetaPagination, ResponseEnvelope
from app.schemas.psychosocial import (
    AssignmentCreatedOut,
    AssignmentOut,
    AssignRequest,
    BaselineOut,
    DeleteScreeningDataRequest,
    InstrumentSummaryOut,
    PatientSummaryOut,
    ReferralActionOut,
    ReferralActionRequest,
    ReissueLinkRequest,
    ResponseOut,
    ScaleOut,
    ScreeningDataOut,
    SessionDetailOut,
    SessionSummaryOut,
    WorklistRowOut,
)
from app.screening.registry import get_instrument, list_instruments
from app.services import psychosocial as svc

router = APIRouter()


# --- serialisers ------------------------------------------------------------
def _scales(result: dict | None) -> list[ScaleOut]:
    if not result:
        return []
    return [
        ScaleOut(
            scale_id=s["scale_id"],
            label=s["label"],
            score=s["score"],
            max_score=s["max_score"],
            band_label=s["band_label"],
            band_level=s["band_level"],
            referral=s["referral"],
        )
        for s in result.get("scales", [])
    ]


def _partial_risk(session: PsychosocialSession) -> bool:
    if session.status != "in_progress":
        return False
    instrument = get_instrument(session.instrument_id, session.instrument_version)
    responses = session.responses or {}
    return any(responses.get(rule.item_id, 0) >= rule.min_value for rule in instrument.risk_item_rules)


def session_summary(session: PsychosocialSession) -> SessionSummaryOut:
    instrument = get_instrument(session.instrument_id, session.instrument_version)
    return SessionSummaryOut(
        id=session.id,
        assignment_id=session.assignment_id,
        patient_id=session.patient_id,
        instrument_id=session.instrument_id,
        instrument_version=session.instrument_version,
        short_name=instrument.short_name,
        position=session.position,
        status=session.status,
        answered_count=len(session.responses or {}),
        total_items=len(instrument.items),
        started_at=session.started_at,
        completed_at=session.completed_at,
        created_at=session.created_at,
        referral_flag=session.referral_flag,
        risk_item_flag=session.risk_item_flag,
        partial_risk=_partial_risk(session),
        scales=_scales(session.result),
    )


def effective_status(assignment: PsychosocialAssignment) -> str:
    if assignment.status == "active" and svc.aware(assignment.expires_at) <= svc.utcnow():
        return "expired"
    return assignment.status


def assignment_out(assignment: PsychosocialAssignment, names: dict[uuid.UUID, str]) -> AssignmentOut:
    return AssignmentOut(
        id=assignment.id,
        patient_id=assignment.patient_id,
        status=assignment.status,
        effective_status=effective_status(assignment),
        expires_at=assignment.expires_at,
        created_at=assignment.created_at,
        assigned_by_name=names.get(assignment.assigned_by) if assignment.assigned_by else None,
        sessions=[session_summary(s) for s in assignment.sessions],
    )


# --- catalogue --------------------------------------------------------------
@router.get(
    "/psychosocial/instruments",
    response_model=ResponseEnvelope[list[InstrumentSummaryOut]],
)
async def list_screeners(_scope: CapabilityScope = Depends(require_capability("screening.assign"))):
    return ResponseEnvelope(
        data=[
            InstrumentSummaryOut(
                id=i.id,
                version=i.version,
                short_name=i.short_name,
                name=i.name,
                item_count=len(i.scored_items),
                citation=i.citation,
            )
            for i in list_instruments()
        ]
    )


# --- assign / cancel / reissue ---------------------------------------------
@router.post(
    "/patients/{patient_id}/psychosocial/sessions",
    response_model=ResponseEnvelope[AssignmentCreatedOut],
    status_code=status.HTTP_201_CREATED,
)
async def assign_screeners(
    patient_id: uuid.UUID,
    payload: AssignRequest,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    _scope: CapabilityScope = Depends(require_capability("screening.assign")),
):
    assignment, token = await svc.create_assignment(
        db,
        clinic_id=ctx.clinic.id,
        user_id=ctx.user.id,
        patient_id=patient_id,
        instrument_ids=list(payload.instruments),
        expires_in_days=payload.expires_in_days,
    )
    names = await svc.user_names(db, {ctx.user.id})
    return ResponseEnvelope(
        data=AssignmentCreatedOut(
            assignment=assignment_out(assignment, names),
            screener_path=svc.screener_path(token),
        )
    )


@router.post(
    "/psychosocial/assignments/{assignment_id}/cancel",
    response_model=ResponseEnvelope[AssignmentOut],
)
async def cancel_screener(
    assignment_id: uuid.UUID,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    _scope: CapabilityScope = Depends(require_capability("screening.assign")),
):
    assignment = await svc.cancel_assignment(
        db, clinic_id=ctx.clinic.id, user_id=ctx.user.id, assignment_id=assignment_id
    )
    names = await svc.user_names(db, {assignment.assigned_by})
    return ResponseEnvelope(data=assignment_out(assignment, names))


@router.post(
    "/psychosocial/assignments/{assignment_id}/link",
    response_model=ResponseEnvelope[AssignmentCreatedOut],
)
async def reissue_link(
    assignment_id: uuid.UUID,
    payload: ReissueLinkRequest,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    _scope: CapabilityScope = Depends(require_capability("screening.assign")),
):
    assignment, token = await svc.rotate_link(
        db,
        clinic_id=ctx.clinic.id,
        user_id=ctx.user.id,
        assignment_id=assignment_id,
        expires_in_days=payload.expires_in_days,
    )
    names = await svc.user_names(db, {assignment.assigned_by})
    return ResponseEnvelope(
        data=AssignmentCreatedOut(
            assignment=assignment_out(assignment, names),
            screener_path=svc.screener_path(token),
        )
    )


# --- review -----------------------------------------------------------------
@router.get(
    "/patients/{patient_id}/psychosocial/sessions",
    response_model=ResponseEnvelope[list[AssignmentOut]],
)
async def list_patient_screeners(
    patient_id: uuid.UUID,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    scope: CapabilityScope = Depends(require_capability("screening.view")),
):
    assignments = await svc.list_patient_assignments(
        db, clinic_id=ctx.clinic.id, patient_id=patient_id, scope=scope, user_id=ctx.user.id
    )
    names = await svc.user_names(db, {a.assigned_by for a in assignments})
    return ResponseEnvelope(data=[assignment_out(a, names) for a in assignments])


@router.get(
    "/patients/{patient_id}/psychosocial/summary",
    response_model=ResponseEnvelope[PatientSummaryOut],
)
async def patient_screening_summary(
    patient_id: uuid.UUID,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    scope: CapabilityScope = Depends(require_capability("screening.view")),
):
    latest = await svc.patient_summary(
        db, clinic_id=ctx.clinic.id, patient_id=patient_id, scope=scope, user_id=ctx.user.id
    )
    return ResponseEnvelope(
        data=PatientSummaryOut(
            patient_id=patient_id,
            referral_flag=any(s.referral_flag for s in latest),
            risk_item_flag=any(s.risk_item_flag for s in latest),
            latest=[session_summary(s) for s in latest],
        )
    )


@router.get(
    "/psychosocial/sessions",
    response_model=ResponseEnvelope[list[WorklistRowOut]],
)
async def clinic_worklist(
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    scope: CapabilityScope = Depends(require_capability("screening.view")),
    status_filter: Literal["pending", "in_progress", "completed", "cancelled"] | None = Query(
        default=None, alias="status"
    ),
    flagged: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    rows, total = await svc.list_clinic_sessions(
        db,
        clinic_id=ctx.clinic.id,
        scope=scope,
        user_id=ctx.user.id,
        status_filter=status_filter,
        flagged_only=flagged,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return ResponseEnvelope(
        data=[
            WorklistRowOut(
                session=session_summary(session),
                patient_name=f"{patient.first_name} {patient.last_name}".strip(),
                assignment_effective_status=effective_status(assignment),
            )
            for session, patient, assignment in rows
        ],
        meta=MetaPagination(total=total, page=page, page_size=page_size),
    )


def _referral_out(record, names) -> ReferralActionOut:
    return ReferralActionOut(
        id=record.id,
        session_id=record.session_id,
        action=record.action,
        note=record.note,
        recorded_by_name=names.get(record.recorded_by) if record.recorded_by else None,
        recorded_at=record.recorded_at,
    )


@router.get(
    "/psychosocial/sessions/{session_id}",
    response_model=ResponseEnvelope[SessionDetailOut],
)
async def session_detail(
    session_id: uuid.UUID,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    scope: CapabilityScope = Depends(require_capability("screening.view")),
):
    session = await svc.get_session_for_staff(
        db, clinic_id=ctx.clinic.id, session_id=session_id, scope=scope, user_id=ctx.user.id
    )
    instrument = get_instrument(session.instrument_id, session.instrument_version)
    patient = await db.get(Patient, session.patient_id)
    responses = session.responses or {}
    response_rows = []
    for item in instrument.items:
        value = responses.get(item.id)
        label = None
        if value is not None:
            label = next((o.label for o in instrument.options_for(item) if o.value == value), None)
        response_rows.append(
            ResponseOut(
                item_id=item.id,
                number=item.number,
                text=item.text,
                scored=item.scored,
                value=value,
                answer_label=label,
            )
        )

    baseline_out = None
    is_baseline = False
    if session.status == "completed":
        baseline = await svc.baseline_for(db, session)
        if baseline is not None:
            is_baseline = baseline.id == session.id
            if not is_baseline:
                baseline_out = BaselineOut(
                    session_id=baseline.id,
                    completed_at=baseline.completed_at,
                    scales=_scales(baseline.result),
                )

    actions = await svc.referral_actions_for_sessions(db, ctx.clinic.id, [session.id])
    names = await svc.user_names(db, {a.recorded_by for a in actions})
    detail = SessionDetailOut(
        session=session_summary(session),
        patient_name=f"{patient.first_name} {patient.last_name}".strip() if patient else "",
        instrument_name=instrument.name,
        citation=instrument.citation,
        reasons=list((session.result or {}).get("reasons", [])),
        responses=response_rows,
        baseline=baseline_out,
        is_baseline=is_baseline,
        referral_actions=[_referral_out(a, names) for a in actions],
    )
    await svc.audit(
        db,
        clinic_id=ctx.clinic.id,
        user_id=ctx.user.id,
        action="psychosocial.result_viewed",
        entity_type="psychosocial_session",
        entity_id=session.id,
        details={"patient_id": str(session.patient_id)},
    )
    return ResponseEnvelope(data=detail)


@router.post(
    "/psychosocial/sessions/{session_id}/referral-actions",
    response_model=ResponseEnvelope[ReferralActionOut],
    status_code=status.HTTP_201_CREATED,
)
async def log_referral(
    session_id: uuid.UUID,
    payload: ReferralActionRequest,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    scope: CapabilityScope = Depends(require_capability("screening.refer")),
):
    session = await svc.get_session_for_staff(
        db, clinic_id=ctx.clinic.id, session_id=session_id, scope=scope, user_id=ctx.user.id
    )
    record = await svc.log_referral_action(
        db,
        clinic_id=ctx.clinic.id,
        user_id=ctx.user.id,
        session=session,
        action=payload.action,
        note=payload.note,
    )
    names = await svc.user_names(db, {ctx.user.id})
    return ResponseEnvelope(data=_referral_out(record, names))


@router.get(
    "/patients/{patient_id}/psychosocial/referral-actions",
    response_model=ResponseEnvelope[list[ReferralActionOut]],
)
async def patient_referral_history(
    patient_id: uuid.UUID,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    scope: CapabilityScope = Depends(require_capability("screening.view")),
):
    assignments = await svc.list_patient_assignments(
        db, clinic_id=ctx.clinic.id, patient_id=patient_id, scope=scope, user_id=ctx.user.id
    )
    session_ids = [s.id for a in assignments for s in a.sessions]
    actions = await svc.referral_actions_for_sessions(db, ctx.clinic.id, session_ids)
    names = await svc.user_names(db, {a.recorded_by for a in actions})
    return ResponseEnvelope(data=[_referral_out(a, names) for a in actions])


# --- deletion on request (SRS 3.2, S-D-024) ---------------------------------
@router.get(
    "/patients/{patient_id}/psychosocial/data",
    response_model=ResponseEnvelope[ScreeningDataOut],
)
async def screening_data_overview(
    patient_id: uuid.UUID,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    _scope: CapabilityScope = Depends(require_capability("screening.delete")),
):
    counts = await svc.screening_data_counts(db, clinic_id=ctx.clinic.id, patient_id=patient_id)
    return ResponseEnvelope(data=ScreeningDataOut(**counts))


@router.post(
    "/patients/{patient_id}/psychosocial/data/delete",
    response_model=ResponseEnvelope[ScreeningDataOut],
)
async def delete_screening_data(
    patient_id: uuid.UUID,
    payload: DeleteScreeningDataRequest,
    ctx: AuthenticatedContextDep,
    db: SessionDep,
    _scope: CapabilityScope = Depends(require_capability("screening.delete")),
):
    """Erase a patient's screening data. Returns what was removed."""
    deleted = await svc.delete_patient_screening_data(
        db, clinic_id=ctx.clinic.id, user_id=ctx.user.id, patient_id=patient_id
    )
    return ResponseEnvelope(data=ScreeningDataOut(**deleted))
