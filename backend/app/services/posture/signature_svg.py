"""
Radar drawing of the Biomechanical Signature, one axis per parameter,
grouped head to toe. Drawn here, on the server, so the web report and the
PDF show the identical picture.

Each point sits on the ring of its grade: normal innermost, severe
outermost, so a smaller shape is a better one. A parameter that could not
be measured gets its axis and a grey "not measured" label but no point, so
it can never be read as sitting on any ring. The ring key is printed
beside the chart by the page (RING_LABELS), not inside it, where the
outline would cover it.
"""

import math
from html import escape
from typing import Any

# Same colours as the PDF badges (pdf_service.SEVERITY_STYLES).
COLOUR = {
    "none": "#15803d",
    "mild": "#a16207",
    "moderate": "#c2410c",
    "severe": "#b91c1c",
}
GREY = "#94a3b8"

RING_LABELS = ["Normal", "Mild", "Moderate", "Severe"]

SHORT_LABEL = {
    "PT-L01": "Forward head",
    "PT-A01": "Head tilt",
    "PT-P02": "Shoulder level",
    "PT-P01": "Trunk shift",
    "PT-L05": "Trunk lean",
    "PT-A04": "Pelvis",
    "PT-L06": "Knee, side",
}


def _short(p: dict[str, Any]) -> str:
    pid = p.get("paramId")
    if pid in ("PT-A05", "PT-A06"):
        label = p.get("label") or ""
        if label.startswith("Left"):
            return "Left knee"
        if label.startswith("Right"):
            return "Right knee"
        return "Knee"
    return SHORT_LABEL.get(pid, p.get("label") or "")


def render_signature_svg(signature: dict[str, Any], width: int = 440, height: int = 320) -> str:
    params = [p for r in signature.get("regions") or [] for p in r.get("parameters") or []]
    cx, cy = width / 2, height / 2
    outer = height * 0.33
    ring = lambda t: outer * (t + 1) / 4  # noqa: E731

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="Biomechanical signature">'
    ]

    for t in range(len(RING_LABELS)):
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring(t):.1f}" fill="none" '
            f'stroke="#e2e8f0" stroke-width="1"/>'
        )

    n = len(params)
    if n == 0:
        parts.append("</svg>")
        return "".join(parts)

    points: list[tuple[float, float, dict[str, Any]]] = []
    for i, p in enumerate(params):
        # Half a step off vertical, so no label sits on top of the chart's
        # vertical centre line.
        a = math.radians(-90 + 360 * (i + 0.5) / n)
        ex, ey = cx + outer * math.cos(a), cy + outer * math.sin(a)
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="#e2e8f0" stroke-width="1"/>'
        )
        lx, ly = cx + (outer + 16) * math.cos(a), cy + (outer + 16) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.3 else ("start" if math.cos(a) > 0 else "end")
        measured = p.get("tier") is not None
        label = escape(_short(p))
        second = "" if measured else (
            f'<tspan x="{lx:.1f}" dy="10" font-size="7.5">not measured</tspan>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{ly + 3:.1f}" font-size="8.5" text-anchor="{anchor}" '
            f'fill="{"#334155" if measured else GREY}" '
            f'font-family="Helvetica, Arial, sans-serif">{label}{second}</text>'
        )
        if measured:
            r = ring(p["tier"])
            points.append((cx + r * math.cos(a), cy + r * math.sin(a), p))

    measured_pts = [(x, y) for x, y, _ in points]
    if len(measured_pts) >= 3:
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in measured_pts)
        parts.append(
            f'<polygon points="{d}" fill="#0f172a" fill-opacity="0.06" '
            f'stroke="#0f172a" stroke-width="1.2" stroke-linejoin="round"/>'
        )

    for x, y, p in points:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" '
            f'fill="{COLOUR[p["severity"]]}" stroke="#ffffff" stroke-width="1"/>'
        )

    parts.append("</svg>")
    return "".join(parts)
