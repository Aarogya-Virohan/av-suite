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
