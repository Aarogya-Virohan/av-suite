"""Tool 03 public patient screener.

No login: the link token authorises the request. Every route is in the
ClinicGate public allowlist and goes through the in-process rate limiter.
Responses never contain patient identity, the session database ids, or
any score.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from app.core.dependencies import SessionDep
from app.schemas.envelope import ResponseEnvelope
from app.schemas.psychosocial import (
    AnswerOut,
    AnswerRequest,
    ConsentOut,
    ConsentRequest,
    InstrumentOut,
    ReconsentAnswer,
    ReportGateOut,
    ReportLineOut,
    ReportLinkOut,
    ReportOpen,
    ReportOut,
    ReconsentOut,
    ItemOut,
    OptionOut,
    ScreenerInstrumentOut,
    ScreenerOut,
    SubmitOut,
    SubmitRequest,
)
from app.screening.consent import CONSENT_PARAGRAPHS, CONSENT_TEXT_VERSION, CONSENT_TITLE
from app.screening.rate_limit import enforce_screener_rate_limit
from app.screening.registry import get_instrument
from app.screening.types import Instrument
from app.services import psychosocial as svc
from app.services import psychosocial_share as sharing
from app.screening.share import RESOURCES_BY_KEY, link_domain

router = APIRouter(prefix="/screener", dependencies=[Depends(enforce_screener_rate_limit)])

TokenPath = Path(min_length=20, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


def instrument_out(instrument: Instrument) -> InstrumentOut:
    return InstrumentOut(
        id=instrument.id,
        version=instrument.version,
        short_name=instrument.short_name,
        name=instrument.name,
        instructions=instrument.instructions,
        options=[OptionOut(value=o.value, label=o.label) for o in instrument.options],
        items=[
            ItemOut(
                id=item.id,
                number=item.number,
                text=item.text,
                scored=item.scored,
                options=(
                    [OptionOut(value=o.value, label=o.label) for o in item.options]
                    if item.options is not None
                    else None
                ),
            )
            for item in instrument.items
        ],
        licence_note=instrument.licence_note,
    )


def consent_out(required: bool) -> ConsentOut:
    return ConsentOut(
        required=required,
        text_version=CONSENT_TEXT_VERSION,
        title=CONSENT_TITLE,
        paragraphs=list(CONSENT_PARAGRAPHS),
    )


# Re-consent link (Q7 = 7B, S-D-037). Two path segments, so it never clashes
# with GET /{token}.
@router.get("/reconsent/{token}", response_model=ResponseEnvelope[ReconsentOut])
async def open_reconsent(db: SessionDep, token: str = TokenPath):
    request = await svc.resolve_consent_request(db, token)
    return ResponseEnvelope(
        data=ReconsentOut(
            clinic_name=await svc.clinic_name(db, request.clinic_id),
            state=svc.consent_request_state(request),
            expires_at=request.expires_at,
            consent=consent_out(True),
        )
    )


@router.post("/reconsent/{token}/answer", response_model=ResponseEnvelope[ReconsentOut])
async def answer_reconsent(payload: ReconsentAnswer, db: SessionDep, token: str = TokenPath):
    request = await svc.answer_consent_request(db, token, accept=payload.accept, text_version=payload.text_version)
    return ResponseEnvelope(
        data=ReconsentOut(
            clinic_name=await svc.clinic_name(db, request.clinic_id),
            state=svc.consent_request_state(request),
            expires_at=request.expires_at,
            consent=consent_out(True),
        )
    )


# Provider-shared report (S-D-039). Two path segments, like the re-consent link.
@router.get("/report/{token}", response_model=ResponseEnvelope[ReportGateOut])
async def report_gate(db: SessionDep, token: str = TokenPath):
    row = await sharing.resolve_share(db, token)
    return ResponseEnvelope(
        data=ReportGateOut(clinic_name=await svc.clinic_name(db, row.clinic_id), needs_birth_year=row.birth_year_check)
    )


@router.post("/report/{token}/open", response_model=ResponseEnvelope[ReportOut])
async def report_open(payload: ReportOpen, db: SessionDep, token: str = TokenPath):
    opened = await sharing.open_share(db, token, payload.birth_year)
    row = opened.report
    links = [
        ReportLinkOut(
            title=r.title,
            description=r.description,
            url=r.url,
            domain=link_domain(r.url) if r.url else None,
            phones=[{"label": label, "tel": tel} for label, tel in r.phones],
        )
        for r in (RESOURCES_BY_KEY[k] for k in row.resource_keys if k in RESOURCES_BY_KEY)
    ] + [
        ReportLinkOut(title=link["title"], description=None, url=link["url"], domain=link_domain(link["url"]), phones=[])
        for link in row.custom_links
    ]
    return ResponseEnvelope(
        data=ReportOut(
            clinic_name=opened.clinic_name,
            provider_name=opened.provider_name,
            shared_on=row.created_at,
            advice=row.advice,
            summary=[
                ReportLineOut(short_name=s.short_name, score=s.score, max_score=s.max_score, phrase=s.phrase)
                for s in opened.summary
            ],
            resources=links,
        )
    )


@router.get("/{token}", response_model=ResponseEnvelope[ScreenerOut])
async def open_screener(db: SessionDep, token: str = TokenPath):
    assignment = await svc.resolve_token(db, token)
    consent = await svc.latest_consent(db, assignment.clinic_id, assignment.patient_id)
    current = svc.current_session(assignment)
    return ResponseEnvelope(
        data=ScreenerOut(
            clinic_name=await svc.clinic_name(db, assignment.clinic_id),
            expires_at=assignment.expires_at,
            consent=ConsentOut(
                required=not svc.consent_satisfied(consent),
                text_version=CONSENT_TEXT_VERSION,
                title=CONSENT_TITLE,
                paragraphs=list(CONSENT_PARAGRAPHS),
            ),
            questionnaires=[
                ScreenerInstrumentOut(
                    instrument=instrument_out(get_instrument(s.instrument_id, s.instrument_version)),
                    status=s.status,
                    answers=dict(s.responses or {}),
                )
                for s in assignment.sessions
            ],
            current_instrument_id=current.instrument_id if current else None,
        )
    )


@router.post("/{token}/consent", response_model=ResponseEnvelope[dict])
async def give_consent(payload: ConsentRequest, db: SessionDep, token: str = TokenPath):
    await svc.record_consent(db, token, payload.text_version)
    return ResponseEnvelope(data={"consent": "granted"})


@router.post("/{token}/withdraw", response_model=ResponseEnvelope[dict])
async def withdraw(db: SessionDep, token: str = TokenPath):
    await svc.withdraw_consent(db, token)
    return ResponseEnvelope(data={"consent": "withdrawn"})


@router.post("/{token}/answers", response_model=ResponseEnvelope[AnswerOut])
async def save_answer(payload: AnswerRequest, db: SessionDep, token: str = TokenPath):
    session = await svc.save_answer(db, token, payload.instrument_id, payload.item_id, payload.value)
    instrument = get_instrument(session.instrument_id, session.instrument_version)
    responses = session.responses or {}
    upcoming = svc.next_item(instrument, responses)
    return ResponseEnvelope(
        data=AnswerOut(
            instrument_id=session.instrument_id,
            answered_count=len(responses),
            total_items=len(instrument.items),
            next_item_id=upcoming.id if upcoming else None,
            ready_to_submit=svc.scored_complete(instrument, responses),
        )
    )


@router.post("/{token}/submit", response_model=ResponseEnvelope[SubmitOut])
async def submit(payload: SubmitRequest, db: SessionDep, token: str = TokenPath):
    assignment = await svc.submit_session(db, token, payload.instrument_id)
    nxt = svc.current_session(assignment) if assignment.status == "active" else None
    completed = [s for s in assignment.sessions if s.status == "completed"]
    return ResponseEnvelope(
        data=SubmitOut(
            instrument_id=payload.instrument_id,
            assignment_complete=assignment.status == "completed",
            next_instrument_id=nxt.instrument_id if nxt else None,
            show_referral_message=any(s.referral_flag for s in completed),
            show_support_contacts=any(s.risk_item_flag for s in completed),
        )
    )
