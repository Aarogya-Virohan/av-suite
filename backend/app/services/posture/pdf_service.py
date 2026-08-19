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

DISCLAIMER = (
    "<strong>Screening and documentation aid &mdash; not a diagnostic device.</strong> "
    "Automated 2D landmark measurements carry inherent error and require "
    "interpretation by a qualified physiotherapist."
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
            value_text = "&mdash;"
        else:
            value_text = f"{_esc(value)}{_esc(unit)}"

        rows.append(
            f"""
            <tr>
                <td class="param">{_esc(m.get('label'))}</td>
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
        f"Landmark confidence: {accuracy * 100:.1f}%"
        if isinstance(accuracy, (int, float))
        else ""
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


def _synthesis_section(synthesis: dict) -> str:
    """Render the muscle-balance summary and corrective protocol."""

    def _list(items: list[str]) -> str:
        if not items:
            return '<li class="empty">None identified</li>'
        return "".join(f"<li>{_esc(i)}</li>" for i in items)

    protocol = synthesis.get("correctiveProtocol") or []

    if protocol:
        protocol_html = "".join(
            f"<li><span class='ex'>{_esc(p.get('exercise'))}</span>"
            f"<span class='dose'>{_esc(p.get('dosage'))}</span></li>"
            for p in protocol
        )
    else:
        protocol_html = '<li class="empty">None prescribed</li>'

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
                <td>
                    <h3>Corrective Protocol</h3>
                    <ul class="protocol">{protocol_html}</ul>
                </td>
            </tr>
        </table>
    </section>
    """


def build_report_html(report: dict) -> str:
    """Assemble the full clinical report document."""

    patient = report.get("patient") or {}
    views = report.get("views") or {}
    global_index = report.get("globalIndex") or {}

    score = global_index.get("score")
    score_text = f"{score}%" if score is not None else "&mdash;"

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
            content: "{CLINIC_NAME} — Clinical Posture Assessment";
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
        width: 24%;
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
        width: 33.3%;
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
    .protocol .ex {{
        display: block;
        font-weight: bold;
        color: #0f172a;
    }}
    .protocol .dose {{
        display: block;
        color: #64748b;
        font-size: 8pt;
        margin-bottom: 3px;
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

{_synthesis_section(report.get("synthesis") or {})}

<div class="index-block">
    <p class="label">Global Stability Index</p>
    <p class="score">{score_text}</p>
    <p class="descriptor">{_esc(global_index.get('descriptor'))}</p>
</div>

<table class="signature">
    <tr>
        <td class="sig-name">Assessing Physiotherapist</td>
        <td class="sig-spacer"></td>
        <td class="sig-date">Date</td>
    </tr>
</table>

<p class="disclaimer">{DISCLAIMER}</p>

</body>
</html>
"""


def generate_posture_pdf(report: dict) -> bytes:
    """Render the report dict to PDF bytes."""

    html_content = build_report_html(report)

    return HTML(string=html_content).write_pdf()
