"""Request and response models for Tool 03."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.psychosocial import (
    CONTACT_EMAIL_MAX,
    CONTACT_NAME_MAX,
    CONTACT_NOTE_MAX,
    CONTACT_PHONE_MAX,
    CONTACT_ROLE_MAX,
    REFERRAL_ACTIONS,
)

InstrumentId = Literal["phq9", "gad7", "dass21"]
ReferralAction = Literal[REFERRAL_ACTIONS]  # type: ignore[valid-type]


# --- instrument catalogue ---------------------------------------------------
class OptionOut(BaseModel):
    value: int
    label: str


class ItemOut(BaseModel):
    id: str
    number: int
    text: str
    scored: bool
    options: list[OptionOut] | None = None


class InstrumentSummaryOut(BaseModel):
    id: str
    version: str
    short_name: str
    name: str
    item_count: int
    citation: str
    # Clinic-wide default for the Repeat field (SRS 4.3.2). None = just once.
    default_repeat_weeks: int | None = None


class InstrumentOut(BaseModel):
    id: str
    version: str
    short_name: str
    name: str
    instructions: str
    options: list[OptionOut]
    items: list[ItemOut]
    licence_note: str


# --- staff ------------------------------------------------------------------
class AssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruments: list[InstrumentId] = Field(min_length=1, max_length=3)
    expires_in_days: int = Field(default=7, ge=1, le=30)
    # Repeat these screeners every N weeks (SRS 4.1.1). None = just once.
    repeat_every_weeks: int | None = Field(default=None, ge=1, le=52)


class ReissueLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expires_in_days: int = Field(default=7, ge=1, le=30)


class ScaleOut(BaseModel):
    scale_id: str
    label: str
    score: int
    max_score: int
    band_label: str
    band_level: int
    referral: bool


class SessionSummaryOut(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    patient_id: uuid.UUID
    instrument_id: str
    instrument_version: str
    short_name: str
    position: int
    status: str
    answered_count: int
    total_items: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    referral_flag: bool
    risk_item_flag: bool
    # In-progress session where a risk item (PHQ-9 item 9) is already
    # answered above zero. Shown before submit so an abandoned screener
    # cannot hide it (S-D-017).
    partial_risk: bool
    scales: list[ScaleOut]


class AssignmentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    effective_status: str  # active | expired | completed | cancelled
    expires_at: datetime
    created_at: datetime
    assigned_by_name: str | None
    sessions: list[SessionSummaryOut]


class AssignmentCreatedOut(BaseModel):
    assignment: AssignmentOut
    # Path only. The frontend that hosts the screener adds its own origin,
    # so the backend needs no knowledge of frontend URLs.
    screener_path: str


class WorklistRowOut(BaseModel):
    session: SessionSummaryOut
    patient_name: str
    assignment_effective_status: str


class ResponseOut(BaseModel):
    item_id: str
    number: int
    text: str
    scored: bool
    value: int | None
    answer_label: str | None


class ReferralActionOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    action: str
    note: str | None
    recorded_by_name: str | None
    recorded_at: datetime
    # Copied when the action was logged (S-D-029). None = no contact named.
    contact_name: str | None = None
    contact_role: str | None = None


class BaselineOut(BaseModel):
    session_id: uuid.UUID
    completed_at: datetime | None
    scales: list[ScaleOut]


class SessionDetailOut(BaseModel):
    session: SessionSummaryOut
    patient_name: str
    instrument_name: str
    citation: str
    reasons: list[str]
    responses: list[ResponseOut]
    baseline: BaselineOut | None
    is_baseline: bool
    referral_actions: list[ReferralActionOut]


class ReferralActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: ReferralAction
    note: str | None = Field(default=None, max_length=1000)
    # Optional contact from the clinic directory (SRS 4.3.1).
    contact_id: uuid.UUID | None = None


class TrendBandOut(BaseModel):
    min_score: int
    max_score: int
    label: str
    level: int


class TrendPointOut(BaseModel):
    session_id: uuid.UUID
    completed_at: datetime
    score: int
    band_label: str
    band_level: int
    referral: bool


class TrendSeriesOut(BaseModel):
    instrument_id: str
    short_name: str
    scale_id: str
    label: str
    max_score: int
    referral_from: int | None
    bands: list[TrendBandOut]
    points: list[TrendPointOut]


class PatientTrendOut(BaseModel):
    patient_id: uuid.UUID
    series: list[TrendSeriesOut]


ScheduleState = Literal["consent_withdrawn", "waiting", "due", "upcoming"]


class ScheduleOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    instrument_id: str
    short_name: str
    interval_days: int
    state: ScheduleState
    next_due_at: datetime | None
    last_completed_at: datetime | None
    created_at: datetime
    created_by_name: str | None


class DueItemOut(ScheduleOut):
    patient_name: str


class ScreeningDataOut(BaseModel):
    """Counts only. Never scores, bands or flags: admins use this (SRS 3.2)."""

    patient_id: uuid.UUID
    links: int
    screeners: int
    referral_actions: int
    schedules: int
    consent_records: int
    # True when the patient's latest consent decision is a withdrawal. That one
    # record is kept on deletion so no new screener can be sent without them.
    withdrawal_on_file: bool


class DeleteScreeningDataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Typed by the admin in the UI. Guards against an accidental call.
    confirm: Literal["DELETE"]


class PatientSummaryOut(BaseModel):
    """CDSS read contract v1 (SRS 5.1). Supporting input only."""

    patient_id: uuid.UUID
    referral_flag: bool
    risk_item_flag: bool
    latest: list[SessionSummaryOut]


# --- public screener --------------------------------------------------------
class ConsentOut(BaseModel):
    required: bool
    text_version: str
    title: str
    paragraphs: list[str]


class ScreenerInstrumentOut(BaseModel):
    instrument: InstrumentOut
    status: str
    answers: dict[str, int]


class ScreenerOut(BaseModel):
    clinic_name: str
    expires_at: datetime
    consent: ConsentOut
    questionnaires: list[ScreenerInstrumentOut]
    current_instrument_id: str | None


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text_version: str = Field(min_length=1, max_length=32)


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instrument_id: InstrumentId
    item_id: str = Field(min_length=1, max_length=40)
    value: int = Field(ge=0, le=3, strict=True)


class AnswerOut(BaseModel):
    instrument_id: str
    answered_count: int
    total_items: int
    next_item_id: str | None
    ready_to_submit: bool


class SubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instrument_id: InstrumentId


class SubmitOut(BaseModel):
    instrument_id: str
    assignment_complete: bool
    next_instrument_id: str | None
    # Booleans only: the patient never sees a score (SRS 4.2.2, flow step 2).
    show_referral_message: bool
    show_support_contacts: bool


# --- clinic settings (SRS 4.3.2) ------------------------------------------
class BandThresholdOut(BaseModel):
    label: str
    min_score: int
    max_score: int | None
    refers: bool


class ScaleThresholdOut(BaseModel):
    scale_id: str
    label: str
    max_score: int
    referral_band: str
    referral_min_score: int
    bands: list[BandThresholdOut]


class RiskRuleOut(BaseModel):
    item_number: int
    min_value: int
    min_label: str
    description: str


class InstrumentSettingOut(BaseModel):
    instrument_id: str
    instrument_version: str
    short_name: str
    name: str
    default_repeat_weeks: int | None
    updated_at: datetime | None
    updated_by_name: str | None
    source: str
    scales: list[ScaleThresholdOut]
    risk_rules: list[RiskRuleOut]


class ClinicSettingsOut(BaseModel):
    # False until the founders decide on clinic-level thresholds (S-D-027, P-13).
    thresholds_editable: bool
    instruments: list[InstrumentSettingOut]


class UpdateInstrumentSettingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Required, may be null (= just once). Same range the assign form accepts.
    default_repeat_weeks: int | None = Field(ge=1, le=52)


# --- anonymised statistics (SRS 4.3.3) -------------------------------------
class BandCountOut(BaseModel):
    label: str
    count: int | None
    suppressed: bool


class ScaleDistributionOut(BaseModel):
    scale_id: str
    label: str
    bands: list[BandCountOut]


class ReferralFigureOut(BaseModel):
    count: int | None
    rate_percent: float | None
    suppressed: bool


class InstrumentAggregateOut(BaseModel):
    instrument_id: str
    short_name: str
    completed: int
    too_few: bool
    referral: ReferralFigureOut
    scales: list[ScaleDistributionOut]


class AggregatesOut(BaseModel):
    date_from: date
    date_to: date
    min_cell: int
    instruments: list[InstrumentAggregateOut]


# --- referral contact directory (SRS 4.3.1) ---------------------------------
def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ReferralContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=CONTACT_NAME_MAX)
    role: str = Field(max_length=CONTACT_ROLE_MAX)
    # Digits with optional +, spaces and hyphens, 6 to 20 digits.
    phone: str | None = Field(default=None, max_length=CONTACT_PHONE_MAX)
    email: EmailStr | None = Field(default=None, max_length=CONTACT_EMAIL_MAX)
    note: str | None = Field(default=None, max_length=CONTACT_NOTE_MAX)

    @field_validator("name", "role")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("phone", "note", mode="before")
    @classmethod
    def _optional_text(cls, value):
        return _blank_to_none(value) if isinstance(value, str) or value is None else value

    @field_validator("email", mode="before")
    @classmethod
    def _optional_email(cls, value):
        return _blank_to_none(value) if isinstance(value, str) or value is None else value

    @field_validator("phone")
    @classmethod
    def _phone_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = [c for c in value if c.isdigit()]
        allowed = set("0123456789+- ")
        if any(c not in allowed for c in value) or "+" in value[1:] or not 6 <= len(digits) <= 20:
            raise ValueError("enter a phone number with 6 to 20 digits")
        return value

    @model_validator(mode="after")
    def _reachable(self):
        if self.phone is None and self.email is None:
            raise ValueError("add a phone number or an email address")
        return self


class ReferralContactOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    phone: str | None
    email: str | None
    note: str | None
    archived: bool
    updated_at: datetime
    updated_by_name: str | None
