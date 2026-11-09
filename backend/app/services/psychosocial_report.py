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
from app.services.posture.pdf_service import (
    BRAND_DARK,
    DEEP_TEAL,
    GROVE,
    INK,
    LIME,
    MIDNIGHT,
    MIDNIGHT_2,
    MUTED,
    ON_DARK,
    PAGE,
    PAPER,
    POWERED_BY_COMPANY,
    POWERED_BY_PRODUCT,
    RULE,
    _brand_data_uri,
    _font_faces,
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
        report_id=f"PS-{ist(now).strftime('%Y%m%d')}-{str(patient.id)[:8].upper()}",
        clinic_name=clinic.name if clinic else "",
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        patient_details=details,
        generated_at=now,
        generated_by=names.get(user_id, ""),
        own_scope=scope == CapabilityScope.OWN,
        series=build_series(sessions),
        sessions=rows,
        referrals=referrals,
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
            f'fill="{tint}" stroke="{RULE}" stroke-width="0.4"/>'
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
    wordmark = _brand_data_uri("av_logo_wordmark_white.png")
    mark = _brand_data_uri("av_mark.png")
    brand = (
        f'<img class="wordmark" src="{wordmark}" alt="{POWERED_BY_COMPANY}" />'
        if wordmark
        else f'<span class="clinic">{POWERED_BY_COMPANY}</span>'
    )
    footer_mark = f'<img class="footer-mark" src="{mark}" alt="" />' if mark else ""
    scope_note = (
        '<p class="scope">This summary includes only the screenings sent by '
        f"{_esc(data.generated_by)}.</p>"
        if data.own_scope
        else ""
    )
    details = " &middot; ".join(_esc(d) for d in data.patient_details)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{_esc(REPORT_TITLE)}</title>
<style>
    {_font_faces()}
    @page {{
        size: A4;
        margin: 27mm 0 18mm 0;
        background-color: {PAGE};
        @top-center {{ content: element(letterhead); width: 100%; vertical-align: top; }}
        @bottom-center {{ content: element(runningFooter); width: 100%; vertical-align: top; }}
    }}
    body {{
        font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: {INK}; margin: 0; padding: 0 14mm; font-size: 9pt; line-height: 1.45;
    }}
    .letterhead {{
        position: running(letterhead); width: 100%;
        background: linear-gradient(115deg, {MIDNIGHT} 0%, {MIDNIGHT_2} 55%, {DEEP_TEAL} 100%);
        padding: 5mm 14mm 4.5mm 14mm; color: #ffffff; box-sizing: border-box;
    }}
    .letterhead table {{ width: 100%; border-collapse: collapse; }}
    .letterhead td {{ vertical-align: middle; padding: 0; }}
    .letterhead p {{ margin: 0; }}
    .wordmark {{ height: 9mm; }}
    .clinic {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 13pt; }}
    .lh-right {{ text-align: right; }}
    .lh-title {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 11.5pt; color: #ffffff; }}
    .lh-sub {{ font-size: 7.6pt; color: {ON_DARK}; }}
    .lh-accent {{ color: {LIME}; font-weight: 700; }}
    .running-footer {{ position: running(runningFooter); width: 100%; padding: 0 14mm; box-sizing: border-box; }}
    .running-footer table {{ width: 100%; border-top: 0.3mm solid {RULE}; border-collapse: collapse; }}
    .running-footer td {{ padding-top: 2.5mm; font-size: 6.6pt; color: {MUTED}; }}
    .footer-mark {{ height: 3.4mm; vertical-align: middle; margin-right: 1.5mm; }}
    .powered {{ letter-spacing: 0.06em; font-weight: 600; }}
    .page::after {{ content: "Page " counter(page) " of " counter(pages); }}
    .patient {{
        background: {PAPER}; border: 0.3mm solid {RULE}; border-radius: 2.5mm;
        padding: 4mm 5mm; margin-top: 2mm;
    }}
    .patient table {{ width: 100%; border-collapse: collapse; }}
    .patient td {{ vertical-align: top; padding: 0; }}
    .patient .name {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 13pt; margin: 0; }}
    .patient .meta {{ margin: 1mm 0 0 0; color: {MUTED}; }}
    .patient .right {{ text-align: right; font-size: 7.8pt; color: {MUTED}; }}
    .patient .right strong {{ color: {INK}; }}
    .scope {{ margin: 2.5mm 0 0 0; font-size: 7.8pt; color: {BRAND_DARK}; }}
    h2 {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 10.5pt;
        margin: 6mm 0 2.5mm 0; padding-left: 2.5mm; border-left: 0.9mm solid {GROVE};
    }}
    .trend {{ background: {PAPER}; border: 0.3mm solid {RULE}; border-radius: 2.5mm; padding: 3mm 4mm 2mm 4mm; margin-bottom: 3mm; page-break-inside: avoid; }}
    .trend-title {{ margin: 0 0 1.5mm 0; font-weight: 700; }}
    .muted {{ color: {MUTED}; font-weight: 400; font-size: 7.6pt; }}
    .hint {{ margin: 1mm 0 0 0; font-size: 7.4pt; color: {MUTED}; }}
    table.grid {{ width: 100%; border-collapse: collapse; background: {PAPER}; font-size: 8.4pt; }}
    table.grid th {{
        text-align: left; font-size: 7pt; text-transform: uppercase; letter-spacing: 0.05em;
        color: {MUTED}; border-bottom: 0.4mm solid {RULE}; padding: 2mm 2.5mm;
    }}
    table.grid td {{ border-bottom: 0.25mm solid {RULE}; padding: 2mm 2.5mm; vertical-align: top; }}
    table.grid tr {{ page-break-inside: avoid; }}
    .flag {{ display: inline-block; font-size: 7pt; font-weight: 700; color: {FLAG}; border: 0.3mm solid {FLAG}; border-radius: 1.5mm; padding: 0.3mm 1.6mm; margin: 0 1mm 0.8mm 0; }}
    .flag.risk {{ background: {FLAG}; color: #ffffff; }}
    .none {{ color: {MUTED}; }}
    .note {{ color: {MUTED}; }}
    .empty {{ color: {MUTED}; font-style: italic; }}
    .disclaimer {{ margin-top: 7mm; padding-top: 3mm; border-top: 0.3mm solid {RULE}; font-size: 7.4pt; color: {MUTED}; }}
    .closing {{ page-break-inside: avoid; }}
    .sign {{ margin-top: 10mm; width: 100%; border-collapse: collapse; page-break-inside: avoid; }}
    .sign td {{ width: 45%; border-top: 0.3mm solid {INK}; padding-top: 1.5mm; font-size: 7.4pt; color: {MUTED}; }}
    .sign td.gap {{ width: 10%; border: none; }}
</style>
</head>
<body>
<div class="letterhead"><table><tr>
    <td>{brand}</td>
    <td class="lh-right">
        <p class="lh-title">{_esc(REPORT_TITLE)}</p>
        <p class="lh-sub">{_esc(data.clinic_name)} &middot; <span class="lh-accent">Confidential clinical record</span></p>
    </td>
</tr></table></div>

<div class="running-footer"><table><tr>
    <td>{footer_mark}<span class="powered">POWERED BY {POWERED_BY_COMPANY} &bull; {POWERED_BY_PRODUCT}</span></td>
    <td style="text-align:right">{_esc(data.report_id)} &middot; <span class="page"></span></td>
</tr></table></div>

<div class="patient"><table><tr>
    <td>
        <p class="name">{_esc(data.patient_name)}</p>
        <p class="meta">{details}</p>
    </td>
    <td class="right">
        Generated <strong>{_esc(display_datetime(data.generated_at))}</strong><br/>
        By <strong>{_esc(data.generated_by)}</strong><br/>
        Report ID {_esc(data.report_id)}
    </td>
</tr></table>
{scope_note}
</div>

<h2>Score trend</h2>
{_trend_sections(data.series)}

<h2>Completed screenings</h2>
{_sessions_table(data.sessions)}

<h2>Referral actions</h2>
{_referrals_table(data.referrals)}

<div class="closing">
<p class="disclaimer">{_esc(DISCLAIMER)}</p>
<table class="sign"><tr>
    <td>Treating physiotherapist, name and signature</td><td class="gap"></td><td>Date</td>
</tr></table>
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
