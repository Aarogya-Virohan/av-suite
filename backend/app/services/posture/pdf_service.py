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
"""

from __future__ import annotations

import base64
import html
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from weasyprint import HTML

from app.services.posture.classifier import SEVERITY_LABELS
from app.services.posture.signature_svg import render_signature_svg

CLINIC_NAME = "Aarogya Virohan"
CLINIC_SUBTITLE = "Clinical Posture Assessment"
REPORT_TITLE = "Posture Assessment Report"

# Brand, 11 October 2026. Colours are taken from the logo itself: the
# charcoal of the wordmark and the teal of the hands. The founders said the
# full colour scheme is still to be discussed, so everything brand related
# lives in these constants and nothing else in the file hard codes it.
# Severity colours are NOT brand colours and stay as they were (the four
# colour scale the founders confirmed on 10 October).
BRAND = "#4e888f"          # logo teal
BRAND_DARK = "#3b6a70"     # teal for small text, darker for contrast on white
INK = "#2f3336"            # logo charcoal, body headings
MUTED = "#6b7378"          # labels
FAINT = "#8a9296"          # footnotes
RULE = "#d9e3e4"           # hairlines
TINT = "#f3f7f7"           # panel background

# Footer wording as given by Onkar, 11 October 2026:
# "(c) POWERED BY AAROGYA VIROHAN . AV SUITE . (A CLINICAL EXERCISE
# PRESCRIPTION TOOL)". "Exercise" corrected from "Excercise" in the
# message. The tagline describes AV Suite as a whole; this report itself
# prescribes no exercise (founders, 1b).
POWERED_BY_COMPANY = "AAROGYA VIROHAN"
POWERED_BY_PRODUCT = "AV SUITE"
POWERED_BY_TAGLINE = "(A CLINICAL EXERCISE PRESCRIPTION TOOL)"

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
    Two decimals, always. The values arrive rounded to two places, so
    11.90 came through as 11.9 and sat beside 2.36 in the same column. This
    only pads; it does not change any value. (How many decimals the report
    should carry at all is a founder question, see decisions.md.)
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _esc(value)
    return f"{value:.2f}"


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

VIEW_CAPTION = {
    "side": "Viewed from the side",
    "front": "Viewed from the front",
    "back": "Viewed from behind",
}


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

    accuracy = view.get("accuracy")
    accuracy_text = (
        f"{accuracy * 100:.1f}%" if isinstance(accuracy, (int, float)) else ""
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
    if accuracy_text:
        details.append(("Landmark visibility", accuracy_text))
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

    caption = VIEW_CAPTION.get(key, "")
    caption_html = f'<span class="caption">{caption}</span>' if caption else ""

    return f"""
    <section class="plane">
        <table class="plane-head">
            <tr>
                <td><h2>{_esc(title)}</h2></td>
                <td class="meta-right">{caption_html}</td>
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


def _patient_band(patient: dict, report_id: str) -> str:
    """
    Patient details, three to a row. A field left empty at intake is left
    out rather than printed as a blank label: an empty "Clinician" on a
    clinical document reads as an omission, not as "not given".
    """

    age_sex = " / ".join(
        _esc(v) for v in (patient.get("age"), patient.get("gender")) if _present(v)
    )

    items = [
        ("Patient", _esc(patient.get("name"))),
        ("Age / Sex", age_sex),
        ("Case ref.", _esc(patient.get("caseRef"))),
        ("Clinician", _esc(patient.get("clinician"))),
        ("Assessed", _display_date(patient.get("assessmentDate"))),
        ("Report ID", f'<span class="nowrap">{_esc(report_id)}</span>' if report_id else ""),
    ]
    items = [(label, value) for label, value in items if value]

    cells = [
        f'<td class="label">{label}</td><td class="value">{value}</td>'
        for label, value in items
    ]
    while len(cells) % 3:
        cells.append('<td class="label"></td><td class="value"></td>')

    rows = "".join(
        "<tr>" + "".join(cells[i:i + 3]) + "</tr>" for i in range(0, len(cells), 3)
    )
    return f'<table class="meta-table">{rows}</table>'


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

    # Under the title on every page, so a loose second page still says whose
    # report it is.
    header_sub = " &nbsp;&middot;&nbsp; ".join(
        v
        for v in (_esc(patient.get("name")), _display_date(patient.get("assessmentDate")))
        if v
    ) or CLINIC_SUBTITLE

    logo = _brand_data_uri("av_logo_wordmark.png")
    logo_block = (
        f'<img src="{logo}" alt="{CLINIC_NAME}" />'
        if logo
        else f'<span class="logo-text">{CLINIC_NAME}</span>'
    )

    # The logo mark, already faded in the file itself, centred behind every
    # page. WeasyPrint has no background opacity, so the fading is baked
    # into the PNG (2.5 percent since 11 October; 4.5 crossed the tables).
    watermark = _brand_data_uri("av_watermark.png")
    page_background = (
        f'background: url("{watermark}") no-repeat center 50%; '
        f"background-size: 95mm auto;"
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
    @page {{
        size: A4;
        margin: 27mm 14mm 22mm 14mm;
        {page_background}

        @top-left {{
            content: element(runningHeader);
            width: 100%;
            vertical-align: bottom;
            padding-bottom: 4mm;
        }}
        @bottom-center {{
            content: element(runningFooter);
            width: 100%;
            vertical-align: top;
            padding-top: 3mm;
        }}
    }}

    body {{
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: {INK};
        margin: 0;
        padding: 0;
        line-height: 1.45;
        font-size: 9.5pt;
    }}

    /* Repeated on every page: logo left, document title right. */
    .running-header {{
        position: running(runningHeader);
        width: 100%;
        border-collapse: collapse;
        border-bottom: 1.5px solid {BRAND};
    }}
    .running-header td {{
        padding: 0 0 7px 0;
        vertical-align: bottom;
    }}
    .running-header .logo img {{
        height: 9.5mm;
        width: auto;
        display: block;
    }}
    .running-header .logo .logo-text {{
        font-size: 16pt;
        color: {INK};
        letter-spacing: 0.3px;
    }}
    .running-header .doc {{
        text-align: right;
    }}
    .running-header .doc-title {{
        font-size: 10.5pt;
        font-weight: 700;
        color: {INK};
        letter-spacing: 0.2px;
        margin: 0;
    }}
    .running-header .doc-sub {{
        font-size: 7pt;
        color: {BRAND_DARK};
        text-transform: uppercase;
        letter-spacing: 1.4px;
        margin: 2px 0 0 0;
    }}

    /* Repeated on every page: centred "Powered by", then the page count. */
    .running-footer {{
        position: running(runningFooter);
        width: 100%;
        border-top: 1px solid {RULE};
        padding-top: 5px;
        text-align: center;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }}
    .running-footer .powered {{
        margin: 0;
        font-size: 8pt;
        color: {INK};
        letter-spacing: 0.9px;
    }}
    .running-footer .powered .by {{
        font-size: 7pt;
        font-weight: 700;
        color: {BRAND_DARK};
    }}
    .running-footer .powered .company {{
        font-size: 7pt;
        font-weight: 700;
        color: {INK};
    }}
    .running-footer .powered .dot {{
        color: {BRAND};
        margin: 0 3px;
    }}
    .running-footer .powered .product {{
        font-size: 8.5pt;
        font-weight: 700;
        color: {BRAND_DARK};
    }}
    .running-footer .powered .tagline {{
        font-size: 6.5pt;
        color: {MUTED};
    }}
    .running-footer .legal {{
        margin: 3px 0 0 0;
        font-size: 6.5pt;
        color: {FAINT};
    }}
    .running-footer .legal .page::after {{
        content: "Page " counter(page) " of " counter(pages);
    }}

    /* Patient band. */
    .meta-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 2px 0 14px 0;
        background: {TINT};
        border: 1px solid {RULE};
    }}
    .meta-table td {{
        padding: 6px 10px;
        vertical-align: baseline;
        font-size: 9pt;
    }}
    .meta-table .label {{
        color: {MUTED};
        width: 10%;
        white-space: nowrap;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        font-size: 6.8pt;
    }}
    .meta-table .nowrap {{
        white-space: nowrap;
    }}
    .meta-table .value {{
        color: {INK};
        font-weight: 700;
        width: 23%;
    }}

    /* Section headings, one style throughout. */
    h2 {{
        font-size: 12pt;
        color: {INK};
        margin: 0;
        padding-left: 8px;
        border-left: 3px solid {BRAND};
        line-height: 1.15;
    }}

    .plane {{
        margin-bottom: 12px;
        page-break-inside: avoid;
    }}
    .plane-head {{
        width: 100%;
        border-collapse: collapse;
        border-bottom: 1px solid {RULE};
        margin-bottom: 8px;
    }}
    .plane-head td {{
        padding: 0 0 5px 0;
        vertical-align: bottom;
    }}
    .plane-head .meta-right {{
        text-align: right;
        white-space: nowrap;
    }}
    .plane-head .accuracy {{
        font-size: 7.5pt;
        color: {MUTED};
        margin-left: 6px;
    }}
    .plane-head .caption {{
        font-size: 7pt;
        color: {MUTED};
        text-transform: uppercase;
        letter-spacing: 0.9px;
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
        padding-right: 16px;
        text-align: center;
    }}
    .plane-photo {{
        height: 90mm;
        width: auto;
        max-width: 80mm;
        border: 0.8px solid {RULE};
        border-radius: 3px;
    }}
    .photo-missing {{
        border: 1px dashed #cbd5e1;
        color: #94a3b8;
        font-size: 8pt;
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
        font-size: 6.8pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.7px;
        color: {MUTED};
        border-bottom: 1px solid {RULE};
        padding: 3px 6px 4px 6px;
    }}
    .measurements td {{
        padding: 5px 6px;
        border-bottom: 1px solid #edf2f2;
        font-size: 9pt;
        vertical-align: middle;
    }}
    .measurements .param {{
        color: {INK};
        width: 52%;
    }}
    .measurements .value {{
        font-weight: 700;
        width: 16%;
        white-space: nowrap;
        text-align: right;
        padding-right: 14px;
    }}
    .measurements th.num {{
        text-align: right;
        padding-right: 14px;
    }}
    .measurements .severity span {{
        display: inline-block;
        padding: 1.5px 7px;
        border-radius: 3px;
        font-size: 7pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    .measurements .empty {{
        color: #94a3b8;
        font-style: italic;
    }}

    .data-cell {{
        padding-left: 4px;
    }}
    .measurements td {{
        padding-top: 7px;
        padding-bottom: 7px;
    }}
    .interpretation {{
        margin: 12px 0 0 0;
        padding: 8px 11px;
        background: {TINT};
        border-radius: 3px;
    }}
    .interpretation p {{
        margin: 0;
        font-size: 8.8pt;
        color: {INK};
        line-height: 1.45;
    }}
    .interpretation .tag {{
        font-size: 6.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: {BRAND_DARK};
        margin-bottom: 2px;
    }}
    .photo-details {{
        margin-top: 12px;
        border-collapse: collapse;
        font-size: 7.6pt;
    }}
    .photo-details td {{
        padding: 1.5px 0;
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
        margin-top: 12px;
        page-break-inside: avoid;
    }}
    .bio-signature h2,
    .synthesis h2 {{
        margin-bottom: 8px;
    }}
    .section-rule {{
        border-bottom: 1px solid {RULE};
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
        border-bottom: 1px solid #edf2f2;
    }}
    .region-list .grade {{
        text-align: right;
    }}
    .region-list .grade span {{
        font-size: 7pt;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 3px;
        white-space: nowrap;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    .region-list .sig-none {{
        color: #64748b;
        background: #f8fafc;
        font-weight: 400 !important;
        text-transform: none !important;
    }}
    .bio-signature .key {{
        font-size: 7pt;
        color: {FAINT};
        margin: 7px 0 0 0;
    }}

    .synthesis {{
        margin-top: 12px;
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
        font-size: 7pt;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: {BRAND_DARK};
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
    }}
    .synthesis-grid li {{
        margin-right: 5px;
    }}
    .synthesis-grid li:not(:last-child)::after {{
        content: ",";
    }}
    .synthesis-grid .empty {{
        color: #94a3b8;
        font-style: italic;
    }}

    /* Sign-off, kept well apart from the synthesis above so its lines can
       not be read as underlines of the muscle lists. */
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
        border-bottom: 1px solid #aeb8bb;
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
        border-radius: 3px;
        padding: 7px 11px;
        page-break-inside: avoid;
    }}
    .notes .disclaimer-tag {{
        font-size: 6.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: {BRAND_DARK};
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
        color: {FAINT};
    }}
</style>
</head>
<body>

<table class="running-header">
    <tr>
        <td class="logo">{logo_block}</td>
        <td class="doc">
            <p class="doc-title">{REPORT_TITLE}</p>
            <p class="doc-sub">{header_sub}</p>
        </td>
    </tr>
</table>

<div class="running-footer">
    <p class="powered">
        <span class="by">&copy; POWERED BY</span>
        <span class="company">{POWERED_BY_COMPANY}</span><span class="dot">&bull;</span><span class="product">{POWERED_BY_PRODUCT}</span><span class="dot">&bull;</span><span class="tagline">{POWERED_BY_TAGLINE}</span>
    </p>
    <p class="legal"><span class="page"></span></p>
</div>

{_patient_band(patient, report_id)}

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
