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

import html
from datetime import date
from typing import Any

from weasyprint import HTML

from app.services.posture.classifier import SEVERITY_LABELS
from app.services.report_letterhead import (
    ClinicBrand,
    PatientBox,
    age_sex_text,
    clinical_band_html,
    clinical_footer_html,
    clinical_page_css,
    patient_box_html,
)
from app.services.posture.reference_ranges import (
    RANGE_HEADING,
    SCREENING_NOTE,
    SOURCES_HEADING,
    screening_range,
    source_lines,
)
from app.services.posture.signature_svg import render_signature_svg

# Palette, "powered by" words and brand assets moved to app/services/brand.py
# (14 Nov 2026) so the shared report letterhead does not import this module.
# Re-exported here under the old names for existing importers.
from app.services.brand import (  # noqa: F401
    BRAND,
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
    ZEBRA,
    BAND_TINT,
    RULE_SOFT,
    brand_data_uri as _brand_data_uri,
    font_faces as _font_faces,
)

CLINIC_NAME = "Aarogya Virohan"
REPORT_TITLE = "Posture Assessment Report"

# Letterhead, 17 November 2026: the shared report letterhead
# (app/services/report_letterhead.py, D-036), the same header the exercise
# prescription and invoice carry. The clinic is the signed-in clinic, read
# from the clinics row by the route, never from the report body the client
# posts, and never a placeholder name. Without a clinic name the shared
# header falls back to Aarogya Virohan only.
LETTERHEAD_SUBTITLE = REPORT_TITLE


def clinic_brand(clinic: dict | None) -> ClinicBrand:
    """The letterhead from the route's clinic dict (posture/clinic_letterhead.py)."""
    clinic = clinic if isinstance(clinic, dict) else {}
    brand = clinic.get("brand")
    if isinstance(brand, ClinicBrand):
        return brand
    logo = clinic.get("logoSrc") or ""
    logo = logo if isinstance(logo, str) and logo.startswith("data:image/png;base64,") else ""
    return ClinicBrand(name=str(clinic.get("name") or "").strip(), logo_src=logo)


def footer_reference(report_id: str) -> str:
    """Document number in the bottom band (D-043). No patient data."""
    return report_id or ""


# Severity -> (text colour, background). Deliberately sober: this is printed
# and read by a clinician, not a dashboard badge.
SEVERITY_STYLES: dict[str, tuple[str, str]] = {
    "none": ("#15803d", "#f0fdf4"),
    "mild": ("#a16207", "#fefce8"),
    "moderate": ("#c2410c", "#fff7ed"),
    "severe": ("#b91c1c", "#fef2f2"),
    "insufficient_data": ("#64748b", "#f8fafc"),
    "not_available": ("#64748b", "#f8fafc"),
    "under_review": ("#64748b", "#f8fafc"),
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
    {"none", "insufficient_data", "not_available", "under_review"}
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


def _range_html(param_id: str) -> str:
    """
    The Normal range cell. The embedded Inter subset has no \u2264 or \u2265,
    and WeasyPrint prints a blank for them, so the symbol alone is set in a
    system face that has it (Liberation Sans on the server image).
    """
    text = _esc(screening_range(param_id))
    for sym in ("\u2264", "\u2265"):
        text = text.replace(sym, f'<span class="sym">{sym}</span>')
    return text


def _measurement_rows(measurements: list[dict]) -> str:
    """Render the measurement table body for one view."""

    if not measurements:
        return (
            '<tr><td colspan="4" class="empty">No measurements available '
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
                <td class="range">{_range_html(str(m.get("paramId") or ""))}</td>
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
    "guided capture, but without the guided camera’s tilt correction. "
    "Compare them with later visits with that in mind."
)

# "Viewed from the side" captions removed on 13 October 2026: the plane
# titles already say which view each is.


def _view_section(title: str, view: dict, key: str = "") -> str:
    """
    Render one anatomical plane, the annotated photograph beside its
    measurements. 19 October 2026, founders asked for bigger photographs:
    the side plane has page 1 to itself under the patient box (photo
    128 mm), front and back share page 2 (photo 108 mm each), and the
    signature and closing block go to page 3.
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
    # 27 October 2026: a guided capture is levelled from the phone's own
    # tilt reading. Said once, in the same line, only when it was applied.
    # A new report always carries the key; None there means the device could
    # not report its tilt. Older reports have no key and print as before.
    level = view.get("levelCorrection")
    if view.get("captureSource") == "camera":
        if isinstance(level, dict) and isinstance(level.get("degrees"), (int, float)):
            source_text += f", levelled by {abs(level['degrees']):.1f}°"
        elif "levelCorrection" in view and level is None:
            source_text += ", tilt not measured"

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
    <section class="plane plane-{key}">
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
                        <colgroup>
                            <col class="c-param" /><col class="c-value" /><col class="c-range" /><col class="c-finding" />
                        </colgroup>
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th class="num">Value</th>
                                <th>{_esc(RANGE_HEADING)}</th>
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

    # Default size, the same drawing the web report shows.
    svg = render_signature_svg(signature)

    rows = []
    for r in signature["regions"]:
        worst = r.get("worst")
        if worst is None:
            params = r.get("parameters") or []
            if not params:
                text = "No parameter"
            elif any(p.get("severity") == "under_review" for p in params):
                text = "Under review"
            else:
                text = "Not measured"
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

    # 19 October 2026: the chart takes the full width of the page (founders
    # asked for a bigger diagram) and the regions sit under it in two
    # columns, head to toe down the left column first.
    half = (len(rows) + 1) // 2
    left, right = rows[:half], rows[half:]

    return f"""
    <section class="bio-signature">
        <h2>Biomechanical Signature</h2>
        <div class="sig-chart">{svg}</div>
        <p class="key">Each axis is one measurement. A point sits on the ring of
        its grade, normal at the centre and severe at the edge, so a smaller
        shape is a better result. A region shows the worst grade among its
        measurements.</p>
        <table class="sig-regions">
            <tr>
                <td class="sig-col"><table class="region-list">{"".join(left)}</table></td>
                <td class="sig-gap"></td>
                <td class="sig-col"><table class="region-list">{"".join(right)}</table></td>
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
    BR-l: the patient box every clinical report shares (same labels, same
    order). Height, which only the posture report records, follows on its
    own line under the box.
    """

    patient = report.get("patient") or {}
    age = patient.get("age")
    try:
        age = int(age) if _present(age) else None
    except (TypeError, ValueError):
        age = None
    height = patient.get("heightCm")
    height_line = (
        f'<p class="pb-extra"><span>Height</span> {height:g}&nbsp;cm</p>'
        if isinstance(height, (int, float)) and not isinstance(height, bool)
        else ""
    )
    box = patient_box_html(
        PatientBox(
            name=str(patient.get("name") or ""),
            patient_id=str(patient.get("caseRef") or ""),
            age_sex=age_sex_text(age, patient.get("gender")),
            date=html.unescape(_display_date(patient.get("assessmentDate"))),
            therapist=str(patient.get("clinician") or ""),
            report_no=str(report.get("reportId") or ""),
        )
    )
    return f"""
    <p class="doc-title">{_esc(REPORT_TITLE)}</p>
    {box}
    {height_line}
    """


def _sources_section(views: dict | None, closing: str = "") -> str:
    """
    Normal ranges: basis and sources, its own short section on page 3 above
    the sign-off and disclaimer (Onkar's review, 17 November 2026), one line
    per measure. The basis text comes from reference_ranges.py on the
    server, never from the posted report; the name in front of it is the
    row's own label, the same text the table prints (escaped here as it is
    there), so a measure has one name on every page.
    """
    # 23 Nov 2026 (Posture fixes lane): `closing` (sign-off and notes) is
    # printed inside the last two source lines' keep-together block, so when
    # page 3 is full the sign-off moves to the next page with those lines
    # and never stands alone on the last page.
    lines = [
        f'<p class="src"><strong>{_esc(name)}:</strong> {_esc(text)}</p>'
        for name, text in source_lines(views)
    ]
    head, tail = lines[:-2], lines[-2:]
    return (
        '<div class="sources-section">'
        f'<p class="sources-tag">{_esc(SOURCES_HEADING)}</p>'
        f'<p class="src lead">{_esc(SCREENING_NOTE)}</p>'
        f'{"".join(head)}<div class="keep-last">{"".join(tail)}{closing}</div></div>'
    )


def build_report_html(report: dict, clinic: dict | None = None) -> str:
    """
    Assemble the full clinical report document. `clinic` is the signed-in
    clinic as built by the route: {"name", "logoSrc", "details"}.
    """

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

    brand = clinic_brand(clinic)

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

    closing_html = f"""<div class="closing">
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
"""

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
    {_font_faces()}

    {clinical_page_css(brand)}
    body {{ font-size: 9.3pt; }}
    .pb-extra {{ margin: -2mm 0 4mm 0; font-size: 8.6pt; }}
    .pb-extra span {{ color: {MUTED}; font-weight: 600; margin-right: 2mm; }}

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
        table-layout: fixed;
    }}
    /* The photograph is the evidence the numbers come from, so it gets the
       full height of its cell, with no letterbox around a portrait image. */
    .photo-cell {{
        width: 57mm;
        vertical-align: top;
        padding-right: 5mm;
        text-align: center;
    }}
    /* 19 October 2026: bigger photographs, on the founders' word. Front
       and back share page 2 at 108 mm; the side plane is alone on page 1
       under the patient box, so it gets the room that is left there. */
    .plane-photo {{
        height: 108mm;
        width: auto;
        max-width: 57mm;
        object-fit: contain;
        border-radius: 3mm;
    }}
    .plane-side .plane-photo {{
        height: 128mm;
    }}
    .plane-front {{
        page-break-before: always;
    }}
    /* Signature, synthesis and the closing block always start page 3. */
    .summary-page {{
        page-break-before: always;
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
        width: 120mm;
        vertical-align: top;
    }}

    /* One fixed grid for the three plane tables (Onkar's review,
       17 November 2026): the photo cell and the data cell have fixed
       widths, and so do the four columns, so Parameter, Value, Normal
       range and Finding start at the same x on every page. */
    .measurements {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }}
    /* Finding is sized for the longest pill, "MODERATE DEVIATION" (about
       37 mm with the cell padding), 17 November 2026. */
    .measurements col.c-param {{ width: 37mm; }}
    .measurements col.c-value {{ width: 17mm; }}
    .measurements col.c-range {{ width: 25mm; }}
    .measurements col.c-finding {{ width: 41mm; }}
    .measurements th {{
        white-space: nowrap;
    }}
    .measurements th {{
        text-align: left;
        font-size: 6.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: {INK};
        background: {BAND_TINT};
        padding: 1.6mm 2.5mm;
    }}
    .measurements td {{
        padding: 2.2mm 2.5mm;
        font-size: 9pt;
        vertical-align: middle;
    }}
    .measurements tbody tr + tr td {{
        border-top: 0.2mm solid {RULE_SOFT};
    }}
    .measurements .param {{
        color: {INK};
    }}
    /* Normal range: same size and colour as the parameter name. */
    .measurements .range {{
        color: {INK};
        white-space: nowrap;
    }}
    .measurements .range .sym {{
        font-family: 'Liberation Sans', Arial, 'DejaVu Sans', sans-serif;
    }}
    .measurements .value {{
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
        font-weight: 700;
        font-size: 9.8pt;
        color: {MIDNIGHT};
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
        white-space: nowrap;
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
        background: #ffffff;
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
    .sig-chart {{
        text-align: center;
        border-top: 1px solid {RULE};
        padding-top: 1.5mm;
    }}
    /* 128 mm wide, 98 mm tall: the largest that still keeps a report with
       long summaries and a full synthesis on three pages. Labels print at
       about 9 pt. */
    .sig-chart svg {{
        width: 102mm; /* 128 mm until 17 Nov 2026: about 20% smaller so the report stays three pages */
        height: auto;
    }}
    .sig-regions {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 3mm;
    }}
    .sig-regions td {{
        vertical-align: top;
        padding: 0;
    }}
    .sig-col {{
        width: 47%;
    }}
    .sig-gap {{
        width: 6%;
    }}
    .region-list {{
        border-collapse: collapse;
        font-size: 9.4pt;
        color: {INK};
        width: 100%;
    }}
    .region-list td {{
        padding: 1.3mm 0;
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
        font-size: 8pt;
        color: {MUTED};
        text-align: center;
        margin: 1.5mm 12mm 0 12mm;
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
    .closing,
    .keep-last {{
        page-break-inside: avoid;
        break-inside: avoid;
    }}
    .sign-off {{
        margin-top: 8px;
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
        height: 7mm;
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
        margin-top: 6px;
        border: 1px solid {RULE};
        background: #ffffff;
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
    /* Normal ranges: basis and sources (17 November 2026). Minimum 8 pt. */
    .sources-section {{
        margin-top: 3mm;
    }}
    .sources-section .sources-tag {{
        font-size: 6.4pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: {GROVE};
        margin: 0 0 1.2mm 0;
    }}
    .sources-section .src {{
        font-size: 8pt;
        line-height: 1.3;
        color: {INK};
        margin: 0 0 0.4mm 0;
    }}
    .sources-section .src.lead {{
        color: {MUTED};
    }}
    .sources-section .src strong {{
        font-weight: 600;
    }}
    .analysis-version {{
        margin: 6px 0 0 0;
        font-size: 6.5pt;
        color: {MUTED};
    }}
</style>
</head>
<body>

{clinical_band_html(brand)}
{clinical_footer_html(brand, footer_reference(report_id))}

{_patient_box(report)}

{_view_section("Sagittal (Side) Plane", views.get("side") or {}, "side")}
{_view_section("Coronal (Front) Plane", views.get("front") or {}, "front")}
{_view_section("Posterior (Back) Plane", views.get("back") or {}, "back")}

<div class="summary-page">
{_biomech_signature_section(report.get("signature"))}

{_synthesis_section(report.get("synthesis") or {})}

{_sources_section(views, closing_html)}
</div>

</body>
</html>
"""


def generate_posture_pdf(report: dict, clinic: dict | None = None) -> bytes:
    """Render the report dict to PDF bytes, under the signed-in clinic's letterhead."""

    html_content = build_report_html(report, clinic)

    return HTML(string=html_content).write_pdf()
