"""
Clinical PDF generation for the posture report.

The report was previously "exported" via window.print() in the browser, which
produced a printout of the on-screen dashboard: page breaks fell wherever the
screen layout happened to end, the browser stamped its own URL and timestamp
on every page, and interactive controls appeared in the patient's document.

This module renders the same report data as a document designed for paper,
using WeasyPrint (already a dependency, see prescription_service.py). Styling
follows the prescription PDF so both documents read as the same clinic's.
"""

from __future__ import annotations

import html
from typing import Any

from weasyprint import HTML

from app.services.posture.classifier import SEVERITY_LABELS
from app.services.posture.signature_svg import render_signature_svg

CLINIC_NAME = "Aarogya Virohan"
CLINIC_SUBTITLE = "Clinical Posture Assessment"
BRAND = "#ff7a00"

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


def _esc(value: Any) -> str:
    """Escape a value for safe inclusion in the HTML template."""
    if value is None:
        return ""
    return html.escape(str(value))


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
            value_text = f"{_esc(value)}{_esc(unit)}"

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
    "upload": "Uploaded photo, capture protocol not checked",
}


def _view_section(title: str, view: dict) -> str:
    """Render one anatomical plane: annotated image beside its measurements."""

    photo = view.get("photoUrl") or ""

    if photo:
        image_block = f'<img class="plane-photo" src="{photo}" alt="{_esc(title)}" />'
    else:
        image_block = (
            '<div class="photo-missing">Annotated image unavailable</div>'
        )

    accuracy = view.get("accuracy")
    accuracy_text = (
        f"Landmark visibility: {accuracy * 100:.1f}%"
        if isinstance(accuracy, (int, float))
        else ""
    )

    # Founders, 10 October 2026: a guided camera capture and an uploaded
    # photo are measured the same way, but only the capture is checked
    # against the protocol (framing, camera height, distance), so the two
    # are not equally comparable across visits. The report has carried
    # captureSource since 3 October without printing it. Reports saved
    # before then have no value, and print nothing.
    source_text = CAPTURE_SOURCE_TEXT.get(view.get("captureSource") or "", "")
    if source_text:
        accuracy_text = (
            f"{accuracy_text}<br>{source_text}" if accuracy_text else source_text
        )

    interpretation = _esc(view.get("interpretation")) or "&nbsp;"

    return f"""
    <section class="plane">
        <table class="plane-head">
            <tr>
                <td><h2>{_esc(title)}</h2></td>
                <td class="accuracy">{accuracy_text}</td>
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
                                <th>Value</th>
                                <th>Finding</th>
                            </tr>
                        </thead>
                        <tbody>
                            {_measurement_rows(view.get('measurements') or [])}
                        </tbody>
                    </table>
                </td>
            </tr>
        </table>

        <p class="interpretation">{interpretation}</p>
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

    svg = render_signature_svg(signature, width=360, height=220)

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


def build_report_html(report: dict) -> str:
    """Assemble the full clinical report document."""

    patient = report.get("patient") or {}
    views = report.get("views") or {}

    # Stamped so two reports for the same patient are only compared when
    # they came from the same analysis code. Grades move when thresholds,
    # sign conventions or calibration change.
    analysis_version = report.get("analysisVersion")

    # Global Stability Index removed from the report on 10 October 2026 by the founders (Q5): a single
    # score masks a localised finding behind an average, and its weights were
    # never sourced. calculate_global_index stays in scoring.py with nothing
    # calling it. The founders' replacement, a regional profile, is not built
    # yet. See docs/decisions.md, 10 October.

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
    @page {{
        size: A4;
        margin: 16mm 14mm;

        @bottom-left {{
            content: "{CLINIC_NAME} – Clinical Posture Assessment";
            font-family: Helvetica, Arial, sans-serif;
            font-size: 7.5pt;
            color: #64748b;
        }}
        @bottom-right {{
            content: "Page " counter(page) " of " counter(pages);
            font-family: Helvetica, Arial, sans-serif;
            font-size: 7.5pt;
            color: #64748b;
        }}
    }}

    body {{
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #0f172a;
        margin: 0;
        padding: 0;
        line-height: 1.45;
        font-size: 9.5pt;
    }}

    .header {{
        border-bottom: 2px solid {BRAND};
        padding-bottom: 10px;
        margin-bottom: 14px;
    }}
    .clinic-title {{
        font-size: 20pt;
        font-weight: bold;
        color: {BRAND};
        margin: 0 0 3px 0;
    }}
    .clinic-subtitle {{
        font-size: 8.5pt;
        color: #475569;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }}

    .meta-table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 16px;
    }}
    .meta-table td {{
        padding: 4px 8px;
        vertical-align: top;
        font-size: 9pt;
        border-bottom: 1px solid #f1f5f9;
    }}
    .meta-table .label {{
        font-weight: bold;
        color: #475569;
        width: 16%;
        text-transform: uppercase;
        font-size: 7.5pt;
    }}
    .meta-table .value {{
        color: #0f172a;
        width: 34%;
    }}

    .plane {{
        margin-bottom: 16px;
        page-break-inside: avoid;
    }}
    .plane-head {{
        width: 100%;
        border-collapse: collapse;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 8px;
    }}
    .plane-head td {{
        padding: 0 0 4px 0;
        vertical-align: bottom;
    }}
    .plane-head h2 {{
        font-size: 12pt;
        color: #0f172a;
        margin: 0;
    }}
    .plane-head .accuracy {{
        text-align: right;
        font-size: 8pt;
        color: #64748b;
        white-space: nowrap;
    }}

    .plane-body {{
        width: 100%;
        border-collapse: collapse;
    }}
    .photo-cell {{
        width: 34%;
        vertical-align: top;
        padding-right: 10px;
    }}
    .plane-photo {{
        width: 100%;
        max-height: 78mm;
        object-fit: contain;
        border: 1px solid #e2e8f0;
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
        font-size: 7.5pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #475569;
        border-bottom: 1px solid #cbd5e1;
        padding: 3px 6px;
    }}
    .measurements td {{
        padding: 3px 6px;
        border-bottom: 1px solid #f1f5f9;
        font-size: 9pt;
    }}
    .measurements .param {{
        color: #334155;
        width: 52%;
    }}
    .measurements .value {{
        font-weight: bold;
        width: 16%;
    }}
    .measurements .severity span {{
        display: inline-block;
        padding: 1px 7px;
        border-radius: 3px;
        font-size: 7.5pt;
        font-weight: bold;
        text-transform: uppercase;
    }}
    .measurements .empty {{
        color: #94a3b8;
        font-style: italic;
    }}

    .interpretation {{
        font-size: 8.5pt;
        color: #334155;
        margin: 6px 0 0 0;
        padding: 5px 8px;
        background: #f8fafc;
        border-left: 3px solid {BRAND};
    }}

    .bio-signature {{
        margin-top: 12px;
        page-break-inside: avoid;
    }}
    .bio-signature h2 {{
        font-size: 12pt;
        margin: 0 0 6px 0;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 4px;
    }}
    .bio-signature-grid {{
        width: 100%;
        border-collapse: collapse;
    }}
    .bio-signature-grid td {{
        vertical-align: middle;
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
        font-size: 8.5pt;
        color: #334155;
        width: 100%;
    }}
    .region-list td {{
        padding: 3px 0;
        border-bottom: 1px solid #f1f5f9;
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
    }}
    .region-list .sig-none {{
        color: #64748b;
        background: #f8fafc;
        font-weight: 400;
    }}
    .bio-signature .key {{
        font-size: 7pt;
        color: #94a3b8;
        margin: 6px 0 0 0;
    }}

    .synthesis {{
        margin-top: 18px;
        page-break-inside: avoid;
    }}
    .synthesis h2 {{
        font-size: 12pt;
        margin: 0 0 8px 0;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 4px;
    }}
    .synthesis-grid {{
        width: 100%;
        border-collapse: collapse;
    }}
    .synthesis-grid td {{
        vertical-align: top;
        width: 50%;
        padding: 0 8px 0 0;
    }}
    .synthesis-grid h3 {{
        font-size: 8pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: {BRAND};
        margin: 0 0 5px 0;
    }}
    .synthesis-grid ul {{
        margin: 0;
        padding-left: 14px;
        font-size: 8.5pt;
        color: #334155;
    }}
    .synthesis-grid li {{
        margin-bottom: 2px;
    }}
    .synthesis-grid .empty {{
        color: #94a3b8;
        font-style: italic;
        list-style: none;
        margin-left: -14px;
    }}

    .index-block {{
        margin-top: 16px;
        border: 1px solid #e2e8f0;
        padding: 10px 14px;
        page-break-inside: avoid;
    }}
    .index-block .label {{
        font-size: 7.5pt;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #475569;
        margin: 0;
    }}
    .index-block .score {{
        font-size: 20pt;
        font-weight: bold;
        color: {BRAND};
        margin: 2px 0 0 0;
    }}
    .index-block .descriptor {{
        font-size: 9pt;
        color: #334155;
        margin: 0;
    }}
    .index-block .index-basis {{
        font-size: 7pt;
        color: #94a3b8;
        margin: 3px 0 0 0;
    }}

    .signature {{
        margin-top: 22px;
        width: 100%;
        border-collapse: collapse;
        page-break-inside: avoid;
    }}
    .signature td {{
        padding-top: 26px;
        border-top: 1px solid #cbd5e1;
        font-size: 8pt;
        color: #64748b;
    }}
    .signature .sig-name {{
        width: 46%;
    }}
    .signature .sig-date {{
        width: 46%;
    }}
    .signature .sig-spacer {{
        width: 8%;
        border-top: none;
    }}

    .side {{
        display: block;
        margin-top: 2px;
        font-size: 7.5pt;
        font-weight: 400;
        color: #64748b;
    }}

    .side-note {{
        margin-top: 14px;
        font-size: 7.5pt;
        color: #94a3b8;
    }}

    .analysis-version {{
        margin-top: 6px;
        font-size: 6.5pt;
        color: #94a3b8;
    }}

    .disclaimer {{
        margin-top: 18px;
        border-top: 1px solid #e2e8f0;
        padding-top: 8px;
        font-size: 7.5pt;
        color: #64748b;
        line-height: 1.5;
    }}
</style>
</head>
<body>

<div class="header">
    <p class="clinic-title">{CLINIC_NAME}</p>
    <p class="clinic-subtitle">{CLINIC_SUBTITLE}</p>
</div>

<table class="meta-table">
    <tr>
        <td class="label">Patient</td>
        <td class="value">{_esc(patient.get('name'))}</td>
        <td class="label">Case Reference</td>
        <td class="value">{_esc(patient.get('caseRef'))}</td>
    </tr>
    <tr>
        <td class="label">Age</td>
        <td class="value">{_esc(patient.get('age'))}</td>
        <td class="label">Assessment Date</td>
        <td class="value">{_esc(patient.get('assessmentDate'))}</td>
    </tr>
    <tr>
        <td class="label">Clinician</td>
        <td class="value">{_esc(patient.get('clinician'))}</td>
        <td class="label"></td>
        <td class="value"></td>
    </tr>
</table>

{_view_section("Sagittal (Side) Plane", views.get("side") or {})}
{_view_section("Coronal (Front) Plane", views.get("front") or {})}
{_view_section("Posterior (Back) Plane", views.get("back") or {})}

{_biomech_signature_section(report.get("signature"))}

{_synthesis_section(report.get("synthesis") or {})}

<table class="signature">
    <tr>
        <td class="sig-name">Assessing Physiotherapist</td>
        <td class="sig-spacer"></td>
        <td class="sig-date">Date</td>
    </tr>
</table>

<p class="side-note">{SIDE_NOTE}</p>
<p class="disclaimer">{DISCLAIMER}</p>
{f'<p class="analysis-version">Analysis version {_esc(analysis_version)}. Values and grades are only comparable with reports carrying the same version.</p>' if analysis_version else ''}

</body>
</html>
"""


def generate_posture_pdf(report: dict) -> bytes:
    """Render the report dict to PDF bytes."""

    html_content = build_report_html(report)

    return HTML(string=html_content).write_pdf()
