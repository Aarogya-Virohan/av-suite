"""
Clinical PDF generation for the posture report.

The report was previously "exported" via window.print() in the browser, which
produced a printout of the on-screen dashboard: page breaks fell wherever the
screen layout happened to end, the browser stamped its own URL and timestamp
on every page, and interactive controls appeared in the patient's document.

This module renders the same report data as a document designed for paper,
using WeasyPrint (already a dependency, see prescription_service.py).

Design, 11 October 2026: branded after the founders' references (logo top
left, logo watermark, "powered by" footer), then a first design pass: the
photograph sized as the evidence it is, the capture source shown as a flag
rather than a grey footnote, empty intake fields left out, dates written
the way Indian clinical reports write them, a printed report ID, and a
separate sign-off block. The web report (frontend/posture-tool, components
under src/components/report) follows the same layout.

Brand, 13 October 2026: direction B (Midnight letterhead on a cream page)
with a clinic letterhead that falls back to Aarogya Virohan until clinic
details come from the marketplace, and a patient box with every intake field.
"""

from __future__ import annotations

import base64
import html
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from weasyprint import HTML

from app.services.posture.classifier import SEVERITY_LABELS
from app.services.posture.signature_svg import render_signature_svg

CLINIC_NAME = "Aarogya Virohan"
REPORT_TITLE = "Posture Assessment Report"

# Brand, 13 October 2026: direction B of the brand canvas, chosen by Onkar.
# The AV Suite CRM palette ("Midnight & Grove") for the letterhead and
# accents, a cream page, and the logo teal kept for the logo's own world.
# Everything brand related lives in these constants. Severity colours are
# NOT brand colours and stay as they were (the four colour scale the
# founders confirmed on 10 October). The founders have not signed off the
# colour scheme yet (question Q9 of the 12 October batch).
MIDNIGHT = "#0b1238"       # letterhead start, headings
MIDNIGHT_2 = "#121f4a"     # letterhead middle
DEEP_TEAL = "#1b4a54"      # letterhead end
GROVE = "#1c7a54"          # section marks, small accent text
LIME = "#c1ff72"           # only on the dark letterhead
BRAND = "#4e888f"          # logo teal
BRAND_DARK = "#3b6a70"     # logo teal, darker, for small text
INK = "#141a33"            # body text
MUTED = "#5d6380"          # labels (5.9:1 on the page colour)
ON_DARK = "#c9d0ea"        # secondary text on the letterhead
PAGE = "#f8f4ea"           # cream page
PAPER = "#fffdf7"          # boxes on the page
RULE = "#e3dccb"           # hairlines
ZEBRA = "#f3eee2"          # alternate table rows

# Footer, Onkar 13 October 2026: the Aarogya Virohan mark, then "POWERED BY
# AAROGYA VIROHAN . AV SUITE". The bracketed tagline "(A Clinical Exercise
# Prescription Tool)" removed on his word; this report prescribes no
# exercise (founders, 1b).
POWERED_BY_COMPANY = "AAROGYA VIROHAN"
POWERED_BY_PRODUCT = "AV SUITE"

# Letterhead fallback, 13 October 2026. Clinic details will come from the
# marketplace (AV Suite core) once clinics join; until then every report
# carries these. Values as given by Onkar on 13 October, who called them
# placeholders: "AV Clinic" stands in for a clinic name.
AV_FALLBACK = {
    "clinicName": "AV Clinic",
    "phone": "+91 88680 00760",
    "email": "aarogyavirohan@gmail.com",
}

_BRAND_DIR = Path(__file__).parent / "brand"


@lru_cache(maxsize=None)
def _brand_data_uri(filename: str) -> str:
    """
    Embed a brand image as a data URI, so the PDF never depends on a base
    URL or on the working directory WeasyPrint happens to run from. Returns
    an empty string when the file is missing, and the template then leaves
    the logo out instead of failing the whole report.
    """

    path = _BRAND_DIR / filename
    if not path.is_file():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@lru_cache(maxsize=None)
def _font_faces() -> str:
    """
    @font-face rules for the two brand typefaces, embedded as data URIs so
    the PDF looks the same on every server whatever fonts it has installed.
    Files and their OFL licences are in brand/fonts. A missing file is left
    out and the stack falls back to Helvetica or Arial.
    """

    faces = (
        ("Plus Jakarta Sans", 700, "plus-jakarta-sans-latin-700-normal.woff"),
        ("Plus Jakarta Sans", 800, "plus-jakarta-sans-latin-800-normal.woff"),
        ("Inter", 400, "inter-latin-400-normal.woff"),
        ("Inter", 600, "inter-latin-600-normal.woff"),
        ("Inter", 700, "inter-latin-700-normal.woff"),
    )
    rules = []
    for family, weight, filename in faces:
        path = _BRAND_DIR / "fonts" / filename
        if not path.is_file():
            continue
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
            f"font-style: normal; src: url(data:font/woff;base64,{encoded}) format('woff'); }}"
        )
    return "\n".join(rules)


# A clinic logo arrives inside the report body the client posts, so only an
# inline PNG or JPEG is accepted. Anything else (a remote URL, SVG, a file
# path) is ignored and the clinic's initials are shown instead, so a report
# can never make the server fetch or read something.
_LOGO_DATA_URI = re.compile(r"^data:image/(png|jpeg);base64,[A-Za-z0-9+/]+={0,2}$")
_LOGO_MAX_CHARS = 3_000_000


def _safe_logo(value: Any) -> str:
    if not isinstance(value, str) or len(value) > _LOGO_MAX_CHARS:
        return ""
    return value if _LOGO_DATA_URI.match(value) else ""


def _initials(name: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name) if w]
    return "".join(w[0] for w in words[:2]).upper()


def _letterhead(report: dict) -> str:
    """
    The dark band at the top of every page. With clinic details (report
    ["branding"], to come from the marketplace) it is the clinic's own
    letterhead: logo and name on the left, the head doctor in the middle,
    contact on the right. Without them it is Aarogya Virohan's, with the
    assessing physiotherapist from the intake form on the right.
    Empty fields are left out, never printed as blank labels.
    """

    branding = report.get("branding")
    branding = branding if isinstance(branding, dict) else {}
    patient = report.get("patient") or {}

    def col(lines: list[str]) -> str:
        lines = [line for line in lines if line]
        return f'<td class="lh-col">{"".join(lines)}</td>' if lines else ""

    sep = '<td class="lh-sep"></td>'

    if _present(branding.get("clinicName")):
        name = str(branding["clinicName"]).strip()
        logo = _safe_logo(branding.get("logo"))
        tile = (
            f'<img src="{logo}" alt="" />'
            if logo
            else f'<span class="initials">{_esc(_initials(name))}</span>'
        )
        clinic = (
            f'<td class="lh-clinic"><table class="lh-id"><tr>'
            f'<td class="tile">{tile}</td>'
            f'<td><p class="clinic-name">{_esc(name)}</p>'
            + (
                f'<p class="lh-sub">{_esc(branding.get("addressLine"))}</p>'
                if _present(branding.get("addressLine"))
                else ""
            )
            + "</td></tr></table></td>"
        )
        doctor = col([
            f'<p class="doc-name">{_esc(branding.get("doctorName"))}</p>'
            if _present(branding.get("doctorName")) else "",
            f'<p class="doc-degree">{_esc(branding.get("doctorDegree"))}</p>'
            if _present(branding.get("doctorDegree")) and _present(branding.get("doctorName")) else "",
            f'<p class="lh-sub">Reg. No. {_esc(branding.get("doctorRegNo"))}</p>'
            if _present(branding.get("doctorRegNo")) and _present(branding.get("doctorName")) else "",
        ])
        contact = col([
            f'<p class="lh-strong">{_esc(branding.get(k))}</p>' if k == "phone"
            else f'<p class="lh-sub">{_esc(branding.get(k))}</p>'
            for k in ("phone", "email", "website")
            if _present(branding.get(k))
        ])
        cells = [clinic] + [c for c in (doctor, contact) if c]
    else:
        wordmark = _brand_data_uri("av_logo_wordmark_white.png")
        mark = (
            f'<img class="av-wordmark" src="{wordmark}" alt="{CLINIC_NAME}" />'
            if wordmark
            else f'<p class="clinic-name">{CLINIC_NAME}</p>'
        )
        contact_line = " &nbsp;&middot;&nbsp; ".join(
            _esc(AV_FALLBACK[k]) for k in ("phone", "email") if AV_FALLBACK.get(k)
        )
        clinic = (
            f'<td class="lh-clinic">{mark}'
            + (f'<p class="lh-sub av-contact">{contact_line}</p>' if contact_line else "")
            + "</td>"
        )
        assessor = col([
            '<p class="lh-label">Assessing physiotherapist</p>'
            if _present(patient.get("clinician")) else "",
            f'<p class="doc-name">{_esc(patient.get("clinician"))}</p>'
            if _present(patient.get("clinician")) else "",
        ])
        cells = [clinic] + ([assessor] if assessor else [])

    return (
        '<div class="letterhead"><table class="lh"><tr>'
        + sep.join(cells)
        + "</tr></table></div>"
    )


# Severity -> (text colour, background). Deliberately sober: this is printed
# and read by a clinician, not a dashboard badge.
SEVERITY_STYLES: dict[str, tuple[str, str]] = {
    "none": ("#15803d", "#f0fdf4"),
    "mild": ("#a16207", "#fefce8"),
    "moderate": ("#c2410c", "#fff7ed"),
    "severe": ("#b91c1c", "#fef2f2"),
    "insufficient_data": ("#64748b", "#f8fafc"),
    "not_available": ("#64748b", "#f8fafc"),
}

# Wording supplied by the founders, verbatim, 10 October 2026 (Q6), for the
# dashboard and the patient PDF. The frontend carries the same text in
# ReportCard.tsx. Do not reword without going back to them.
DISCLAIMER = (
    "<strong>This structural screening report is generated via automated 2D "
    "optical tracking. It highlights static biomechanical asymmetries to "
    "predict localized tissue loading. It is not a standalone clinical "
    "diagnosis and must be correlated with patient symptoms and functional "
    "movement by a licensed physiotherapist.</strong>"
)

# Separate from DISCLAIMER above, which carries the founders' sign-off and is
# not to be edited here. This one is ours and only explains a convention.
SIDE_NOTE = "Left and right refer to the patient's own sides."

# A direction is only meaningful once the magnitude itself is a finding. Below
# that, sub-millimetre landmark noise decides the side, and printing it would
# put a direction on every healthy patient. The side stays in the report JSON
# either way, so tracking a direction over time is unaffected.
SIDE_HIDDEN_SEVERITIES = frozenset(
    {"none", "insufficient_data", "not_available"}
)

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _esc(value: Any) -> str:
    """Escape a value for safe inclusion in the HTML template."""
    if value is None:
        return ""
    return html.escape(str(value))


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _display_date(value: Any) -> str:
    """
    "2026-10-11" -> "11 Oct 2026". ISO dates read as a database value on a
    clinical document, and 11/10 against 10/11 is ambiguous across readers.
    Anything that is not an ISO date is printed as it came.
    """

    if not _present(value):
        return ""
    try:
        d = date.fromisoformat(str(value)[:10])
    except ValueError:
        return _esc(value)
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


# Units that sit against the number. Every other unit (mm) takes a space,
# as SI writing does: "12.2 mm", but "73.2°".
_TIGHT_UNITS = frozenset({"\u00b0", "%"})


def _number(value: Any) -> str:
    """
    One decimal, always (founders, 13 October 2026, Q4). The values arrive
    already rounded to one place by report_builder.display_value, so 12.0
    would otherwise print as 12 beside 2.4 in the same column. This only
    pads; it does not round anything the backend has not already rounded.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _esc(value)
    return f"{value:.1f}"


def _value_with_unit(value: Any, unit: str) -> str:
    if not unit:
        return _number(value)
    joiner = "" if unit in _TIGHT_UNITS else "&nbsp;"
    return f"{_number(value)}{joiner}{_esc(unit)}"


def _measurement_rows(measurements: list[dict]) -> str:
    """Render the measurement table body for one view."""

    if not measurements:
        return (
            '<tr><td colspan="3" class="empty">No measurements available '
            "for this view.</td></tr>"
        )

    rows: list[str] = []

    for m in measurements:
        severity = str(m.get("severity", "not_available"))
        colour, background = SEVERITY_STYLES.get(
            severity, SEVERITY_STYLES["not_available"]
        )

        value = m.get("value")
        unit = m.get("unit") or ""

        # A missing value means the parameter could not be computed for this
        # capture -- show it as unmeasured rather than as a zero or a blank,
        # so a clinician cannot read it as a normal finding.
        if value is None or value == "":
            # A neutral placeholder on purpose. The finding column alongside
            # already carries the reason and the action, so spelling it out
            # again here would say the same thing twice and could drift.
            value_text = "&ndash;"
        else:
            value_text = _value_with_unit(value, unit)

        side_text = m.get("sideLabel")

        if side_text is None or severity in SIDE_HIDDEN_SEVERITIES:
            param_cell = _esc(m.get("label"))
        else:
            param_cell = (
                f'{_esc(m.get("label"))}'
                f'<span class="side">{_esc(side_text)}</span>'
            )

        rows.append(
            f"""
            <tr>
                <td class="param">{param_cell}</td>
                <td class="value">{value_text}</td>
                <td class="severity">
                    <span style="color:{colour};background:{background};">
                        {_esc(m.get('severityLabel'))}
                    </span>
                </td>
            </tr>
            """
        )

    return "".join(rows)


CAPTURE_SOURCE_TEXT: dict[str, str] = {
    "camera": "Guided camera capture",
    "upload": "Uploaded photo",
}

# Printed once, in the notes at the end, when any view was uploaded. Until
# 11 October 2026 each uploaded view carried an amber "capture protocol not
# checked" flag. The PDF goes to the patient as well as the clinician, and
# three amber warnings read to a patient as "this test was done wrong",
# while the fact itself only matters for comparing visits. The fact stays on
# every view, in plain words; the explanation is said once, calmly.
UPLOAD_NOTE = (
    "Views marked “Uploaded photo” were measured the same way as a "
    "guided capture, but were not taken with the guided camera’s level "
    "check. Compare them with later visits with that in mind."
)

# "Viewed from the side" captions removed on 13 October 2026: the plane
# titles already say which view each is.


def _view_section(title: str, view: dict, key: str = "") -> str:
    """
    Render one anatomical plane. Since 11 October 2026 two planes share a
    page, so the annotated photograph, the evidence every number comes
    from, is printed large (92 mm tall) beside the measurements.
    """

    photo = view.get("photoUrl") or ""

    if photo:
        image_block = f'<img class="plane-photo" src="{photo}" alt="{_esc(title)}" />'
    else:
        image_block = (
            '<div class="photo-missing">Annotated image unavailable</div>'
        )


    # Founders, 10 October 2026: a guided camera capture and an uploaded
    # photo are measured the same way, but only the capture is checked
    # against the protocol (framing, camera height, distance), so the two
    # are not equally comparable across visits. Reports saved before
    # 3 October have no value and print nothing.
    source_text = CAPTURE_SOURCE_TEXT.get(view.get("captureSource") or "", "")

    details = []
    if source_text:
        details.append(("Photograph", source_text))
    details_html = "".join(
        f'<tr><td class="d-label">{label}</td><td class="d-value">{value}</td></tr>'
        for label, value in details
    )
    details_block = (
        f'<table class="photo-details">{details_html}</table>' if details_html else ""
    )

    interpretation = _esc(view.get("interpretation"))
    summary = (
        f'<div class="interpretation"><p class="tag">Summary</p><p>{interpretation}</p></div>'
        if interpretation
        else ""
    )


    return f"""
    <section class="plane">
        <table class="plane-head">
            <tr>
                <td><h2>{_esc(title)}</h2></td>
            </tr>
        </table>

        <table class="plane-body">
            <tr>
                <td class="photo-cell">{image_block}</td>
                <td class="data-cell">
                    <table class="measurements">
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th class="num">Value</th>
                                <th>Finding</th>
                            </tr>
                        </thead>
                        <tbody>
                            {_measurement_rows(view.get('measurements') or [])}
                        </tbody>
                    </table>
                    {summary}
                    {details_block}
                </td>
            </tr>
        </table>
    </section>
    """


def _biomech_signature_section(signature: dict | None) -> str:
    """
    Founders' Q5, 10 October 2026: the regional profile that replaces the
    global score. Redrawn here from the signature data, not taken from any
    SVG the client sends back. Reports saved before 11 October have no
    signature and print nothing.
    """

    if not signature or not signature.get("regions"):
        return ""

    svg = render_signature_svg(signature, width=380, height=175)

    rows = []
    for r in signature["regions"]:
        worst = r.get("worst")
        if worst is None:
            text = "No parameter" if not r.get("parameters") else "Not measured"
            badge = f'<span class="sig-none">{text}</span>'
        else:
            colour, background = SEVERITY_STYLES[worst]
            badge = (
                f'<span style="color:{colour};background:{background};">'
                f"{_esc(SEVERITY_LABELS[worst])}</span>"
            )
        rows.append(
            f'<tr><td class="region">{_esc(r.get("label"))}</td>'
            f'<td class="grade">{badge}</td></tr>'
        )

    return f"""
    <section class="bio-signature">
        <h2>Biomechanical Signature</h2>
        <table class="bio-signature-grid">
            <tr>
                <td class="chart">{svg}</td>
                <td class="regions">
                    <table class="region-list">{"".join(rows)}</table>
                    <p class="key">Each axis is one measurement. Inner ring normal,
                    then mild and moderate, outer ring severe. A region shows the
                    worst grade among its measurements.</p>
                </td>
            </tr>
        </table>
    </section>
    """


def _synthesis_section(synthesis: dict) -> str:
    """
    Render the muscle-balance summary. No exercises since 11 October 2026:
    the founders removed them from the automated report (answer 1b), so
    the tool flags and the physiotherapist prescribes.
    """

    def _list(items: list[str]) -> str:
        if not items:
            return '<li class="empty">None identified</li>'
        return "".join(f"<li>{_esc(i)}</li>" for i in items)

    return f"""
    <section class="synthesis">
        <h2>Clinical Synthesis</h2>

        <table class="synthesis-grid">
            <tr>
                <td>
                    <h3>Likely Hypertonic</h3>
                    <ul>{_list(synthesis.get('hypertonic') or [])}</ul>
                </td>
                <td>
                    <h3>Likely Inhibited</h3>
                    <ul>{_list(synthesis.get('inhibited') or [])}</ul>
                </td>
            </tr>
        </table>
    </section>
    """


def _patient_box(report: dict) -> str:
    """
    Every intake field, in a rounded box under the letterhead, two columns
    of label and value. A field left empty at intake is left out rather
    than printed as a blank label: an empty "Assessed by" on a clinical
    document reads as an omission, not as "not given".
    """

    patient = report.get("patient") or {}
    report_id = report.get("reportId") or ""
    branding = report.get("branding")
    has_clinic = isinstance(branding, dict) and _present(branding.get("clinicName"))

    age = patient.get("age")
    age_text = f"{_esc(age)} Y" if _present(age) else ""
    age_sex = " / ".join(v for v in (age_text, _esc(patient.get("gender"))) if _present(v))

    height = patient.get("heightCm")
    height_text = (
        f"{height:g}&nbsp;cm" if isinstance(height, (int, float)) and not isinstance(height, bool) else ""
    )

    name = _esc(patient.get("name"))
    left = [
        ("Patient name", f'<span class="pname">{name}</span>' if _present(name) else ""),
        ("Age / Sex", age_sex),
        ("Height", height_text),
        ("Case ref.", _esc(patient.get("caseRef"))),
    ]
    right = [
        ("Report ID", f'<span class="nowrap">{_esc(report_id)}</span>' if report_id else ""),
        ("Assessed on", _display_date(patient.get("assessmentDate"))),
        # With a clinic letterhead the head doctor is in the band and the
        # assessing physiotherapist is here. In the Aarogya Virohan fallback
        # the assessing physiotherapist is already in the band, so this row
        # names the clinic instead (13 October 2026, Onkar).
        ("Assessed by", _esc(patient.get("clinician"))) if has_clinic
        else ("Clinic", _esc(AV_FALLBACK.get("clinicName"))),
    ]

    def half(rows: list[tuple[str, str]]) -> str:
        body = "".join(
            f'<tr><td class="pb-label">{label}</td><td class="pb-value">{value}</td></tr>'
            for label, value in rows
            if value
        )
        return f'<table class="pb-half">{body}</table>'

    return f"""
    <table class="patient-box">
        <tr>
            <td class="pb-col">{half(left)}</td>
            <td class="pb-divider"></td>
            <td class="pb-col">{half(right)}</td>
        </tr>
    </table>
    <div class="doc-title">
        <p class="t">{REPORT_TITLE.upper()}</p>
    </div>
    """


def build_report_html(report: dict) -> str:
    """Assemble the full clinical report document."""

    patient = report.get("patient") or {}
    views = report.get("views") or {}
    report_id = report.get("reportId") or ""

    # Stamped so two reports for the same patient are only compared when
    # they came from the same analysis code. Grades move when thresholds,
    # sign conventions or calibration change.
    analysis_version = report.get("analysisVersion")

    # Global Stability Index removed from the report on 10 October 2026 by
    # the founders (Q5): a single score masks a localised finding behind an
    # average, and its weights were never sourced. calculate_global_index
    # stays in scoring.py with nothing calling it. Its replacement is the
    # Biomechanical Signature below.

    # In the footer of every page, so a loose second page still says whose
    # report it is (the letterhead names the clinic, not the patient).
    footer_who = " &nbsp;&middot;&nbsp; ".join(
        v for v in (_esc(patient.get("name")), _esc(report_id)) if _present(v)
    )
    footer_who_html = (
        f'<span class="who">{footer_who}</span>&nbsp;&nbsp;&middot;&nbsp;&nbsp;'
        if footer_who
        else ""
    )

    mark = _brand_data_uri("av_mark.png")
    footer_mark = f'<img class="mark" src="{mark}" alt="" />' if mark else ""

    # The logo mark, already faded in the file itself, centred behind every
    # page. WeasyPrint has no background opacity, so the fading is baked
    # into the PNG: 5.5 percent since 13 October 2026, darker on Onkar's
    # word (2.5 could not be seen on the cream page). Boxes and table rows
    # are opaque, so it shows only between them.
    watermark = _brand_data_uri("av_watermark.png")
    watermark_css = (
        f'background-image: url("{watermark}"); background-repeat: no-repeat; '
        f"background-position: center 55%; background-size: 95mm auto;"
        if watermark
        else ""
    )

    any_upload = any(
        (views.get(k) or {}).get("captureSource") == "upload" for k in ("side", "front", "back")
    )
    upload_note = f'<p class="side-note">{UPLOAD_NOTE}</p>' if any_upload else ""

    version_line = (
        f'<p class="analysis-version">Analysis version {_esc(analysis_version)}. '
        "Values and grades are only comparable with reports carrying the same "
        "version.</p>"
        if analysis_version
        else ""
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
    {_font_faces()}

    /* Side margins are zero so the letterhead runs edge to edge; the body
       carries the 14 mm side margins instead. */
    @page {{
        size: A4;
        margin: 31mm 0 20mm 0;
        background-color: {PAGE};
        {watermark_css}

        @top-center {{
            content: element(letterhead);
            width: 100%;
            vertical-align: top;
        }}
        @bottom-center {{
            content: element(runningFooter);
            width: 100%;
            vertical-align: top;
        }}
    }}

    body {{
        font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: {INK};
        margin: 0;
        padding: 0 14mm;
        line-height: 1.45;
        font-size: 9.3pt;
    }}

    /* Letterhead, repeated on every page. */
    .letterhead {{
        position: running(letterhead);
        width: 100%;
        background: linear-gradient(115deg, {MIDNIGHT} 0%, {MIDNIGHT_2} 55%, {DEEP_TEAL} 100%);
        padding: 5mm 14mm 4.6mm 14mm;
        color: #ffffff;
    }}
    .lh {{
        width: 100%;
        border-collapse: collapse;
    }}
    .lh td {{
        vertical-align: middle;
        padding: 0;
    }}
    .lh p {{
        margin: 0;
    }}
    .lh-clinic {{
        width: 46%;
        padding-right: 5mm !important;
    }}
    .lh-col {{
        padding: 0 4mm !important;
    }}
    .lh-sep {{
        width: 0.3mm;
        background: rgba(255, 255, 255, 0.22);
    }}
    .lh-id {{
        border-collapse: collapse;
    }}
    .lh-id td {{
        vertical-align: middle;
    }}
    .lh-id .tile {{
        width: 13mm;
        height: 13mm;
        background: #ffffff;
        border-radius: 3.2mm;
        text-align: center;
        padding: 0 !important;
    }}
    .lh-id .tile img {{
        max-width: 11mm;
        max-height: 11mm;
        vertical-align: middle;
    }}
    .lh-id .tile .initials {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 800;
        font-size: 13pt;
        color: {GROVE};
    }}
    .lh-id td + td {{
        padding-left: 3.5mm !important;
    }}
    .clinic-name {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 800;
        font-size: 12.5pt;
        line-height: 1.2;
        color: #ffffff;
    }}
    .av-wordmark {{
        height: 8.5mm;
        width: auto;
        display: block;
    }}
    .av-contact {{
        margin-top: 2mm !important;
    }}
    .lh-sub {{
        font-size: 7.6pt;
        color: {ON_DARK};
        line-height: 1.5;
        margin-top: 0.6mm !important;
    }}
    .lh-strong {{
        font-size: 7.8pt;
        font-weight: 600;
        color: #ffffff;
    }}
    .lh-label {{
        font-size: 6.4pt;
        font-weight: 700;
        letter-spacing: 1.1px;
        text-transform: uppercase;
        color: {ON_DARK};
        margin-bottom: 1mm !important;
    }}
    .doc-name {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 700;
        font-size: 10pt;
        color: #ffffff;
    }}
    .doc-degree {{
        font-size: 7.8pt;
        font-weight: 600;
        color: {LIME};
        margin-top: 0.4mm !important;
    }}

    /* Footer, repeated on every page: "powered by", then whose report and
       the page count. */
    .running-footer {{
        position: running(runningFooter);
        width: 100%;
        padding: 0 14mm;
        text-align: center;
    }}
    .running-footer .inner {{
        border-top: 1px solid {RULE};
        padding-top: 2.4mm;
    }}
    .running-footer p {{
        margin: 0;
    }}
    .running-footer .powered {{
        font-size: 7pt;
        letter-spacing: 0.9px;
        color: {MUTED};
    }}
    .running-footer .powered .by {{
        font-weight: 700;
        color: {MUTED};
    }}
    .running-footer .powered .company {{
        font-weight: 700;
        color: {MIDNIGHT};
    }}
    .running-footer .powered .dot {{
        color: {GROVE};
        margin: 0 3px;
    }}
    .running-footer .powered .product {{
        font-weight: 700;
        color: {GROVE};
    }}
    .running-footer .powered .mark {{
        height: 3.6mm;
        width: auto;
        vertical-align: -0.9mm;
        margin-right: 1.6mm;
    }}
    .running-footer .meta {{
        margin-top: 1.2mm;
        font-size: 6.8pt;
        color: {MUTED};
    }}
    .running-footer .meta .page::after {{
        content: "Page " counter(page) " of " counter(pages);
    }}

    /* Patient box. */
    .patient-box {{
        width: 100%;
        border-collapse: separate;
        border: 1.3px solid #d9d1bf;
        border-radius: 4mm;
        background: {PAPER};
        margin: 0 0 3.4mm 0;
    }}
    .patient-box .pb-col {{
        width: 50%;
        vertical-align: top;
        padding: 2.6mm 5mm;
    }}
    .patient-box .pb-divider {{
        width: 0.3mm;
        background: {RULE};
        padding: 0;
    }}
    .pb-half {{
        border-collapse: collapse;
        width: 100%;
    }}
    .pb-half td {{
        padding: 0.7mm 0;
        vertical-align: baseline;
    }}
    .pb-label {{
        width: 27mm;
        font-size: 6.6pt;
        font-weight: 700;
        letter-spacing: 0.9px;
        text-transform: uppercase;
        color: {MUTED};
        white-space: nowrap;
    }}
    .pb-value {{
        font-size: 9pt;
        font-weight: 600;
        color: {INK};
    }}
    .pb-value .pname {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 700;
        font-size: 10.5pt;
    }}
    .nowrap {{
        white-space: nowrap;
    }}

    .doc-title {{
        text-align: center;
        margin: 0 0 3.6mm 0;
    }}
    .doc-title p {{
        margin: 0;
    }}
    .doc-title .t {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 800;
        font-size: 12.5pt;
        letter-spacing: 2.2px;
        color: {MIDNIGHT};
    }}
    .doc-title .s {{
        font-size: 7.8pt;
        color: {MUTED};
        margin-top: 0.8mm;
    }}

    /* Section headings, one style throughout: a Grove dot, Midnight text. */
    h2 {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 700;
        font-size: 11.5pt;
        color: {MIDNIGHT};
        margin: 0;
        line-height: 1.15;
    }}
    h2::before {{
        content: "";
        display: inline-block;
        width: 2.1mm;
        height: 2.1mm;
        border-radius: 50%;
        background: {GROVE};
        margin-right: 2.4mm;
        vertical-align: 0.4mm;
    }}

    .plane {{
        margin-bottom: 3.4mm;
        page-break-inside: avoid;
    }}
    .plane-head {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 2.6mm;
    }}
    .plane-head td {{
        padding: 0;
        vertical-align: bottom;
    }}
    .plane-head .meta-right {{
        text-align: right;
        white-space: nowrap;
    }}
    .plane-head .caption {{
        font-size: 6.6pt;
        font-weight: 700;
        color: {MUTED};
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .plane-body {{
        width: 100%;
        border-collapse: collapse;
    }}
    /* The photograph is the evidence the numbers come from, so it gets the
       full height of its cell, with no letterbox around a portrait image. */
    .photo-cell {{
        width: 1%;
        vertical-align: top;
        padding-right: 5mm;
        text-align: center;
    }}
    .plane-photo {{
        height: 80mm;
        width: auto;
        max-width: 72mm;
        border-radius: 3mm;
    }}
    .photo-missing {{
        width: 45mm;
        border: 1px dashed #c9c1ad;
        border-radius: 3mm;
        color: {MUTED};
        font-size: 7.6pt;
        text-align: center;
        padding: 30px 8px;
    }}
    .data-cell {{
        vertical-align: top;
    }}

    .measurements {{
        width: 100%;
        border-collapse: collapse;
    }}
    .measurements th {{
        text-align: left;
        font-size: 6.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: {MUTED};
        padding: 0 2.5mm 1.8mm 2.5mm;
    }}
    .measurements td {{
        padding: 2.2mm 2.5mm;
        font-size: 9pt;
        vertical-align: middle;
    }}
    .measurements tbody tr:nth-child(even) td {{
        background: {ZEBRA};
    }}
    .measurements .param {{
        color: {INK};
        width: 52%;
    }}
    .measurements .value {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 700;
        font-size: 9.8pt;
        color: {MIDNIGHT};
        width: 16%;
        white-space: nowrap;
        text-align: right;
        padding-right: 4mm;
    }}
    .measurements th.num {{
        text-align: right;
        padding-right: 4mm;
    }}
    .measurements .severity span {{
        display: inline-block;
        padding: 1.6px 8px;
        border-radius: 8px;
        font-size: 6.8pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }}
    .measurements .empty {{
        color: {MUTED};
        font-style: italic;
    }}

    .interpretation {{
        margin: 3mm 0 0 0;
        padding: 2.4mm 3.2mm;
        background: {PAPER};
        border: 1px solid {RULE};
        border-radius: 2.5mm;
    }}
    .interpretation p {{
        margin: 0;
        font-size: 8.6pt;
        color: {INK};
        line-height: 1.45;
    }}
    .interpretation .tag {{
        font-size: 6.4pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: {GROVE};
        margin-bottom: 0.6mm;
    }}
    .photo-details {{
        margin-top: 2.6mm;
        border-collapse: collapse;
        font-size: 7.4pt;
    }}
    .photo-details td {{
        padding: 0.4mm 0;
    }}
    .photo-details .d-label {{
        color: {MUTED};
        padding-right: 12px;
        white-space: nowrap;
    }}
    .photo-details .d-value {{
        color: {INK};
    }}

    .bio-signature {{
        margin-top: 3mm;
        page-break-inside: avoid;
    }}
    .bio-signature h2,
    .synthesis h2 {{
        margin-bottom: 2.4mm;
    }}
    .bio-signature-grid {{
        width: 100%;
        border-collapse: collapse;
        border-top: 1px solid {RULE};
    }}
    .bio-signature-grid td {{
        vertical-align: middle;
        padding-top: 6px;
    }}
    .bio-signature-grid .chart {{
        width: 50%;
    }}
    .bio-signature-grid .chart svg {{
        width: 100%;
        height: auto;
    }}
    .region-list {{
        border-collapse: collapse;
        font-size: 8.8pt;
        color: {INK};
        width: 100%;
    }}
    .region-list td {{
        padding: 3px 0;
        border-bottom: 1px solid {RULE};
    }}
    .region-list .grade {{
        text-align: right;
    }}
    .region-list .grade span {{
        font-size: 6.8pt;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 8px;
        white-space: nowrap;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    .region-list .sig-none {{
        color: {MUTED};
        background: transparent;
        font-weight: 400 !important;
        text-transform: none !important;
    }}
    .bio-signature .key {{
        font-size: 7pt;
        color: {MUTED};
        margin: 7px 0 0 0;
    }}

    .synthesis {{
        margin-top: 3mm;
        page-break-inside: avoid;
    }}
    .synthesis-grid {{
        width: 100%;
        border-collapse: collapse;
        border-top: 1px solid {RULE};
    }}
    .synthesis-grid td {{
        vertical-align: top;
        width: 50%;
        padding: 8px 8px 0 0;
    }}
    .synthesis-grid h3 {{
        font-size: 6.6pt;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: {GROVE};
        margin: 0 0 5px 0;
    }}
    /* Muscles run inline, separated by commas: one per line cost a line of
       page height per muscle and pushed the sign-off to a third page. */
    .synthesis-grid ul {{
        margin: 0;
        padding: 0;
        font-size: 9pt;
        color: {INK};
        list-style: none;
        line-height: 1.6;
    }}
    .synthesis-grid li {{
        display: inline-block;
        white-space: nowrap;
        margin-right: 5px;
    }}
    .synthesis-grid li:not(:last-child)::after {{
        content: ",";
    }}
    .synthesis-grid .empty {{
        color: {MUTED};
        font-style: italic;
    }}

    /* Sign-off and notes travel together. When a long report pushes them
       off page 2, both move to the next page as one closing block, instead
       of the disclaimer sitting alone on a page (seen 12 October 2026). */
    .closing {{
        page-break-inside: avoid;
    }}
    .sign-off {{
        margin-top: 16px;
        width: 100%;
        border-collapse: collapse;
        page-break-inside: avoid;
    }}
    .sign-off td {{
        vertical-align: bottom;
        width: 44%;
        padding: 0;
    }}
    .sign-off .gap {{
        width: 12%;
    }}
    .sign-off .space {{
        height: 9mm;
        border-bottom: 1px solid #b9b1a0;
    }}
    .sign-off .caption {{
        font-size: 7.5pt;
        color: {MUTED};
        padding-top: 4px;
    }}

    .side {{
        display: block;
        margin-top: 1px;
        font-size: 7.3pt;
        font-weight: 400;
        color: {MUTED};
    }}

    .notes {{
        margin-top: 10px;
        border: 1px solid {RULE};
        background: {PAPER};
        border-radius: 2.5mm;
        padding: 2.4mm 3.4mm;
        page-break-inside: avoid;
    }}
    .notes .disclaimer-tag {{
        font-size: 6.4pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: {GROVE};
        margin: 0 0 3px 0;
    }}
    /* The founders' wording, unchanged. Set in the regular weight: a block
       of bold grey type at this size reads as shouting. */
    .notes .disclaimer {{
        font-size: 7.5pt;
        color: {INK};
        line-height: 1.5;
        margin: 0;
    }}
    .notes .disclaimer strong {{
        font-weight: 400;
    }}
    .notes .side-note {{
        font-size: 7pt;
        color: {MUTED};
        margin: 5px 0 0 0;
    }}
    .analysis-version {{
        margin: 6px 0 0 0;
        font-size: 6.5pt;
        color: {MUTED};
    }}
</style>
</head>
<body>

{_letterhead(report)}

<div class="running-footer">
    <div class="inner">
        <p class="powered">
            {footer_mark}<span class="by">POWERED BY</span>
            <span class="company">{POWERED_BY_COMPANY}</span><span class="dot">&bull;</span><span class="product">{POWERED_BY_PRODUCT}</span>
        </p>
        <p class="meta">{footer_who_html}<span class="page"></span></p>
    </div>
</div>

{_patient_box(report)}

{_view_section("Sagittal (Side) Plane", views.get("side") or {}, "side")}
{_view_section("Coronal (Front) Plane", views.get("front") or {}, "front")}
{_view_section("Posterior (Back) Plane", views.get("back") or {}, "back")}

{_biomech_signature_section(report.get("signature"))}

{_synthesis_section(report.get("synthesis") or {})}

<div class="closing">
<table class="sign-off">
    <tr>
        <td><div class="space"></div><div class="caption">Assessing physiotherapist, name and signature</div></td>
        <td class="gap"></td>
        <td><div class="space"></div><div class="caption">Date</div></td>
    </tr>
</table>

<div class="notes">
    <p class="disclaimer-tag">Disclaimer</p>
    <p class="disclaimer">{DISCLAIMER}</p>
    <p class="side-note">{SIDE_NOTE}</p>
    {upload_note}
    {version_line}
</div>
</div>

</body>
</html>
"""


def generate_posture_pdf(report: dict) -> bytes:
    """Render the report dict to PDF bytes."""

    html_content = build_report_html(report)

    return HTML(string=html_content).write_pdf()
