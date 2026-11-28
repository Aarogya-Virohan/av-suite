"""Single-patient screening summary as PDF (SRS 4.1.4).

Content follows the SRS: every completed session, its scores and severity
bands, and every referral action, plus the score trend per scale (SRS
4.1.2). Individual answers are left out: the SRS does not ask for them and
the physio can open each result in the app (S-D-025).

The look follows the posture report and the prescription PDF: the brand
constants and fonts are imported from app/services/posture/pdf_service.py,
not copied, and nothing in that module is changed.

The PDF is rendered on request and streamed back to the signed-in user. It
is never stored and never served from a public path.
"""

from __future__ import annotations

import asyncio
import html
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.permission import CapabilityScope
from app.models.clinic import Clinic
from app.screening.registry import get_instrument
from app.screening.trend import TrendSeries, build_series
from app.services import psychosocial as svc
from app.services.brand import (
    INK,
    MIDNIGHT,
    MUTED,
    RULE_SOFT,
    font_faces as _font_faces,
)
from app.services.clinic_brand import clinic_brand
from app.services.document_numbers import PSY, next_clinical_number
from app.models.document_numbering import PsychosocialReport
from app.services.patient_number import format_patient_id
from app.services.prescription_pdf import fetch_logo
from app.services.report_letterhead import (
    ClinicBrand,
    PatientBox,
    age_sex_text,
    clinical_band_html,
    clinical_footer_html,
    clinical_page_css,
    patient_box_html,
)

try:
    from weasyprint import HTML
except (ImportError, OSError):  # pragma: no cover - native libs missing
    HTML = None

IST = ZoneInfo("Asia/Kolkata")
REPORT_TITLE = "Psycho-Social Screening Summary"

REFERRAL_LABELS = {
    "referred_gp": "Referred to GP",
    "referred_psychologist": "Referred to psychologist",
    "referred_psychiatrist": "Referred to psychiatrist",
    "already_under_care": "Already under mental health care",
    "patient_declined": "Patient declined referral",
    "monitor_and_rescreen": "Monitor and re-screen",
    "other": "Other",
}

DISCLAIMER = (
    "These questionnaires are screening aids, not a diagnosis. Scores and bands follow the "
    "published scoring of each instrument. Interpret them together with the clinical "
    "assessment. A referral suggestion means the score reached the published threshold "
    "for specialist input."
)

# Band tints for the chart, lightest for the lowest band. Bands are also
# named in the chart, so colour is never the only cue (SRS 3.6).
BAND_TINTS = ("#ffffff", "#f6f1e3", "#f3e3c9", "#f0d0bd", "#ecbcb2")
LINE = MIDNIGHT
FLAG = "#b03a2e"


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
@dataclass
class SessionRow:
    completed_at: datetime
    short_name: str
    scales: list[tuple[str, int, int, str]]  # label, score, max, band
    referral: bool
    risk: bool


@dataclass
class ReferralRow:
    recorded_at: datetime
    screener: str
    screener_date: datetime | None
    action: str
    note: str | None
    by: str
    contact: str | None = None


@dataclass
class ReportData:
    report_id: str
    clinic_name: str
    patient_name: str
    patient_details: list[str]
    generated_at: datetime
    generated_by: str
    own_scope: bool
    series: list[TrendSeries]
    sessions: list[SessionRow] = field(default_factory=list)
    referrals: list[ReferralRow] = field(default_factory=list)
    # Round 4 (BR-c, BR-l): shared letterhead and patient box.
    brand: ClinicBrand | None = None
    patient_code: str = ""  # "SPC-000128", label "Patient ID"
    age_sex: str = ""


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(IST)


def display_date(value: datetime | date | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = ist(value).date()
    return value.strftime("%d %b %Y").lstrip("0")


def display_datetime(value: datetime) -> str:
    local = ist(value)
    return f"{display_date(local)}, {local.strftime('%I:%M %p').lstrip('0').lower()}"


def report_filename(patient_name: str, on: datetime) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", patient_name.lower()).strip("-") or "patient"
    return f"screening-summary-{slug}-{ist(on).strftime('%Y-%m-%d')}.pdf"


async def _new_report_number(db: AsyncSession, clinic, patient_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """D-043: every export is one psychosocial_reports row with its own
    <clinic code>-PSY-<6 digits> number, given by the server."""
    number = await next_clinical_number(db, clinic.id, clinic.code, PSY)
    db.add(
        PsychosocialReport(
            clinic_id=clinic.id, patient_id=patient_id, number=number, created_by_user_id=user_id
        )
    )
    await db.flush()
    return number


async def build_report_data(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    scope: CapabilityScope,
    user_id: uuid.UUID,
) -> ReportData:
    patient = await svc.get_patient(db, clinic_id, patient_id)
    sessions = await svc.completed_sessions(
        db, clinic_id=clinic_id, patient_id=patient_id, scope=scope, user_id=user_id
    )
    actions = await svc.referral_actions_for_sessions(db, clinic_id, [s.id for s in sessions])
    names = await svc.user_names(db, {user_id} | {a.recorded_by for a in actions if a.recorded_by})
    clinic = await db.get(Clinic, clinic_id)
    brand = await clinic_brand(db, clinic, fetch_logo)
    age = patient.age
    if age is None and patient.date_of_birth:
        today = ist(svc.utcnow()).date()
        dob = patient.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    sex = str(getattr(patient.gender, "value", patient.gender) or "").replace("_", " ")

    details = []
    if patient.age:
        details.append(f"{patient.age} yrs")
    elif patient.date_of_birth:
        details.append(f"Born {display_date(patient.date_of_birth)}")
    if patient.gender:
        details.append(str(getattr(patient.gender, "value", patient.gender)).replace("_", " ").title())
    if patient.phone:
        details.append(patient.phone)

    by_id = {s.id: s for s in sessions}
    rows = []
    for s in sessions:
        instrument = get_instrument(s.instrument_id, s.instrument_version)
        rows.append(
            SessionRow(
                completed_at=s.completed_at,
                short_name=instrument.short_name,
                scales=[
                    (
                        scale["label"].replace("DASS-21 ", ""),
                        scale["score"],
                        scale["max_score"],
                        scale["band_label"],
                    )
                    for scale in (s.result or {}).get("scales", [])
                ],
                referral=s.referral_flag,
                risk=s.risk_item_flag,
            )
        )
    referrals = []
    for a in actions:
        session = by_id.get(a.session_id)
        referrals.append(
            ReferralRow(
                recorded_at=a.recorded_at,
                screener=get_instrument(session.instrument_id, session.instrument_version).short_name
                if session
                else "",
                screener_date=session.completed_at if session else None,
                action=REFERRAL_LABELS.get(a.action, a.action),
                note=a.note,
                by=names.get(a.recorded_by, "Former staff member") if a.recorded_by else "Former staff member",
                contact=f"{a.contact_name} ({a.contact_role})" if a.contact_name else None,
            )
        )

    now = svc.utcnow()
    return ReportData(
        report_id=await _new_report_number(db, clinic, patient.id, user_id),
        clinic_name=clinic.name if clinic else "",
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        patient_details=details,
        generated_at=now,
        generated_by=names.get(user_id, ""),
        own_scope=scope == CapabilityScope.OWN,
        series=build_series(sessions),
        sessions=rows,
        referrals=referrals,
        brand=brand,
        patient_code=format_patient_id(clinic.code, patient.display_number) if clinic else "",
        age_sex=age_sex_text(age, sex),
    )


# ---------------------------------------------------------------------------
# chart
# ---------------------------------------------------------------------------
def trend_svg(series: TrendSeries, width: float = 500, height: float = 132) -> str:
    """Line chart of one scale over time, drawn in points (pt)."""
    left, right, top, bottom = 26.0, 92.0, 8.0, 20.0
    plot_w, plot_h = width - left - right, height - top - bottom
    max_score = max(series.max_score, 1)

    def y(score: float) -> float:
        return top + plot_h - (score / max_score) * plot_h

    points = series.points
    times = [p.completed_at.timestamp() for p in points]
    t0, t1 = min(times), max(times)
    span = t1 - t0

    def x(t: float) -> float:
        if span == 0:
            return left + plot_w / 2
        return left + (t - t0) / span * plot_w

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}pt" height="{height}pt" '
        f'viewBox="0 0 {width} {height}" font-family="Inter, Helvetica, Arial, sans-serif">'
    ]
    # Bands, lowest at the bottom, each named at the right edge.
    for band in series.bands:
        y_top = y(band.max_score + (1 if band.max_score < max_score else 0))
        y_bottom = y(band.min_score)
        y_top = max(y_top, top)
        tint = BAND_TINTS[min(band.level, len(BAND_TINTS) - 1)]
        parts.append(
            f'<rect x="{left}" y="{y_top:.2f}" width="{plot_w}" height="{y_bottom - y_top:.2f}" '
            f'fill="{tint}" stroke="{RULE_SOFT}" stroke-width="0.4"/>'
        )
        mid = (y_top + y_bottom) / 2 + 2.4
        parts.append(
            f'<text x="{left + plot_w + 5}" y="{mid:.2f}" font-size="6.4" fill="{MUTED}">'
            f'{_esc(band.label)} ({band.min_score}-{band.max_score})</text>'
        )
    # Y axis: 0 and max.
    for value in (0, series.max_score):
        parts.append(
            f'<text x="{left - 4}" y="{y(value) + 2.4:.2f}" font-size="6.4" fill="{MUTED}" '
            f'text-anchor="end">{value}</text>'
        )
    # Referral threshold.
    if series.referral_from is not None:
        ry = y(series.referral_from)
        parts.append(
            f'<line x1="{left}" y1="{ry:.2f}" x2="{left + plot_w}" y2="{ry:.2f}" '
            f'stroke="{FLAG}" stroke-width="0.8" stroke-dasharray="3 2"/>'
        )
        parts.append(
            f'<text x="{left + plot_w - 3}" y="{ry - 2.5:.2f}" font-size="6" fill="{FLAG}" '
            f'text-anchor="end">Referral from {series.referral_from}</text>'
        )
    # Line and points.
    coords = [(x(t), y(p.score)) for t, p in zip(times, points)]
    if len(coords) > 1:
        path = " ".join(f"{cx:.2f},{cy:.2f}" for cx, cy in coords)
        parts.append(f'<polyline points="{path}" fill="none" stroke="{LINE}" stroke-width="1.2"/>')
    label_points = len(points) <= 12
    for (cx, cy), p in zip(coords, points):
        fill = FLAG if p.referral else LINE
        parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.3" fill="{fill}"/>')
        if label_points:
            parts.append(
                f'<text x="{cx:.2f}" y="{cy - 4.5:.2f}" font-size="6.6" font-weight="700" '
                f'fill="{INK}" text-anchor="middle">{p.score}</text>'
            )
    # X axis dates: first, last and up to three between.
    ticks = [0, len(points) - 1] if len(points) > 1 else [0]
    if len(points) > 4:
        step = (len(points) - 1) / 4
        ticks = sorted({0, len(points) - 1, *(round(step * i) for i in (1, 2, 3))})
    for i in ticks:
        cx = coords[i][0]
        anchor = "middle"
        if len(points) > 1 and i == 0:
            anchor = "start"
        elif len(points) > 1 and i == len(points) - 1:
            anchor = "end"
        parts.append(
            f'<text x="{cx:.2f}" y="{height - 6}" font-size="6.4" fill="{MUTED}" '
            f'text-anchor="{anchor}">{_esc(display_date(points[i].completed_at))}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# html
# ---------------------------------------------------------------------------
def _flags(referral: bool, risk: bool) -> str:
    out = []
    if risk:
        out.append('<span class="flag risk">Self-harm answer</span>')
    if referral:
        out.append('<span class="flag">Referral suggested</span>')
    return " ".join(out) or '<span class="none">None</span>'


def _sessions_table(rows: list[SessionRow]) -> str:
    if not rows:
        return '<p class="empty">No completed screenings yet.</p>'
    body = []
    for r in reversed(rows):  # newest first, like the app
        scales = "<br/>".join(
            f'{_esc(label)}: <strong>{score}</strong> / {maximum} &middot; {_esc(band)}'
            if len(r.scales) > 1
            else f'<strong>{score}</strong> / {maximum} &middot; {_esc(band)}'
            for label, score, maximum, band in r.scales
        )
        body.append(
            f"<tr><td>{_esc(display_date(r.completed_at))}</td><td>{_esc(r.short_name)}</td>"
            f"<td>{scales}</td><td>{_flags(r.referral, r.risk)}</td></tr>"
        )
    return (
        '<table class="grid"><thead><tr><th style="width:17%">Completed</th>'
        '<th style="width:13%">Screener</th><th>Score and band</th>'
        '<th style="width:28%">Flags</th></tr></thead><tbody>'
        + "".join(body)
        + "</tbody></table>"
    )


def _referrals_table(rows: list[ReferralRow]) -> str:
    if not rows:
        return '<p class="empty">No referral actions recorded.</p>'
    body = []
    for r in rows:
        about = f"{_esc(r.screener)} of {_esc(display_date(r.screener_date))}" if r.screener else ""
        note = f'<br/><span class="note">{_esc(r.note)}</span>' if r.note else ""
        contact = f"<br/>To: {_esc(r.contact)}" if r.contact else ""
        body.append(
            f"<tr><td>{_esc(display_date(r.recorded_at))}</td><td>{about}</td>"
            f"<td><strong>{_esc(r.action)}</strong>{contact}{note}</td><td>{_esc(r.by)}</td></tr>"
        )
    return (
        '<table class="grid"><thead><tr><th style="width:17%">Recorded</th>'
        '<th style="width:22%">For result</th><th>Action</th><th style="width:20%">By</th>'
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"
    )


def _trend_sections(series: list[TrendSeries]) -> str:
    if not series:
        return '<p class="empty">No completed screenings yet.</p>'
    out = []
    for s in series:
        note = "" if len(s.points) > 1 else '<p class="hint">One result so far. The trend shows from the second result.</p>'
        out.append(
            f'<div class="trend"><p class="trend-title">{_esc(s.label)} '
            f'<span class="muted">{len(s.points)} result{"s" if len(s.points) != 1 else ""}, '
            f'score 0 to {s.max_score}</span></p>{trend_svg(s)}{note}</div>'
        )
    return "".join(out)


def build_report_html(data: ReportData) -> str:
    brand = data.brand or ClinicBrand(name=data.clinic_name)
    scope_note = (
        '<p class="scope">This summary includes only the screenings sent by '
        f"{_esc(data.generated_by)}.</p>"
        if data.own_scope
        else ""
    )
    box = patient_box_html(
        PatientBox(
            name=data.patient_name,
            patient_id=data.patient_code,
            age_sex=data.age_sex,
            date=display_date(data.generated_at),
            therapist=data.generated_by,
            report_no=data.report_id,
        )
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{_esc(REPORT_TITLE)}</title>
<style>
    {_font_faces()}
    {clinical_page_css(brand)}
    p {{ margin: 0; }}
    .confidential {{ font-size: 8pt; font-weight: 600; color: {MUTED}; margin: -2mm 0 4mm 0; }}
    .scope {{ margin: -2mm 0 4mm 0; font-size: 8.4pt; color: {MUTED}; }}
    h2.strip {{ margin: 6mm 0 3mm 0; }}
    .trend {{ border: 0.3mm solid {RULE_SOFT}; border-radius: 2.5mm; padding: 3mm 4mm 2mm 4mm; margin-bottom: 3mm; page-break-inside: avoid; }}
    .trend-title {{ margin: 0 0 1.5mm 0; font-weight: 700; }}
    .muted {{ color: {MUTED}; font-weight: 400; font-size: 8pt; }}
    .hint {{ margin: 1mm 0 0 0; font-size: 8pt; color: {MUTED}; }}
    table.grid {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
    table.grid th {{ padding: 2mm 2.5mm; border-bottom: 0.3mm solid {RULE_SOFT}; }}
    table.grid td {{ border-bottom: 0.2mm solid {RULE_SOFT}; padding: 2mm 2.5mm; vertical-align: top; }}
    table.grid tr {{ page-break-inside: avoid; }}
    .flag {{ display: inline-block; font-size: 7.6pt; font-weight: 700; color: {FLAG}; border: 0.3mm solid {FLAG}; border-radius: 1.5mm; padding: 0.3mm 1.6mm; margin: 0 1mm 0.8mm 0; }}
    .flag.risk {{ background: {FLAG}; color: #ffffff; }}
    .none, .note, .empty {{ color: {MUTED}; }}
    .empty {{ font-style: italic; }}
    .disclaimer {{ margin-top: 7mm; padding-top: 3mm; border-top: 0.3mm solid {RULE_SOFT}; font-size: 8pt; color: {MUTED}; }}
    /* T3-a #3: the closing never sits alone on a page. */
    .closing {{ page-break-inside: avoid; break-inside: avoid; page-break-before: avoid; break-before: avoid; }}
</style>
</head>
<body>
{clinical_band_html(brand)}
{clinical_footer_html(brand, data.report_id)}
<p class="doc-title">{_esc(REPORT_TITLE)}</p>
{box}
<p class="confidential">Confidential clinical record</p>
{scope_note}

<h2 class="strip">Score trend</h2>
{_trend_sections(data.series)}

<h2 class="strip">Completed screenings</h2>
{_sessions_table(data.sessions)}

<h2 class="strip">Referral actions</h2>
{_referrals_table(data.referrals)}

<div class="closing">
<p class="disclaimer">{_esc(DISCLAIMER)}</p>
</div>
</body>
</html>
"""


def _render(document: str) -> bytes:
    if HTML is None:  # pragma: no cover
        raise RuntimeError("WeasyPrint is not available on this server.")
    return HTML(string=document).write_pdf()


async def render_pdf(data: ReportData) -> bytes:
    """Render off the event loop (WeasyPrint is CPU bound)."""
    return await asyncio.to_thread(_render, build_report_html(data))
