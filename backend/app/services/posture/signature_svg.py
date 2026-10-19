"""
Radar drawing of the Biomechanical Signature, one axis per parameter,
grouped head to toe. Drawn here, on the server, so the web report and the
PDF show the identical picture.

Each point sits on the ring of its grade: normal innermost, severe
outermost, so a smaller shape is a better one. A parameter that could not
be measured gets its axis and a grey "not measured" label but no point, so
it can never be read as sitting on any ring.

19 October 2026, founders asked for a bigger diagram: the chart now fills
its own full-width block on the last PDF page. The rings sit on faint bands
in the severity colours and carry their names along the top, so the chart
reads on its own without the key. Labels are 13 units: about 9 pt on the
PDF (drawn 128 mm wide) and 8.5 px on a 340 px phone screen.
"""

import math
from html import escape
from typing import Any

# Same colours as the PDF badges (pdf_service.SEVERITY_STYLES). The outline
# is the brand teal since 11 October 2026.
COLOUR = {
    "none": "#15803d",
    "mild": "#a16207",
    "moderate": "#c2410c",
    "severe": "#b91c1c",
}
GREY = "#94a3b8"

RING_LABELS = ["Normal", "Mild", "Moderate", "Severe"]
_RING_KEYS = ["none", "mild", "moderate", "severe"]

# Band tint per ring: the severity colour mixed into the paper colour,
# solid, so the bands never stack into one muddy colour where they overlap.
_PAPER = (0xFF, 0xFD, 0xF7)
_BAND_MIX = 0.10


def _tint(hex_colour: str, amount: float) -> str:
    c = [int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)]
    m = [round(p + (q - p) * amount) for p, q in zip(_PAPER, c)]
    return "#" + "".join(f"{v:02x}" for v in m)

SHORT_LABEL = {
    "PT-L01": "Forward head",
    "PT-A01": "Head tilt",
    "PT-P02": "Shoulder level",
    "PT-P01": "Trunk shift",
    "PT-L05": "Trunk lean",
    "PT-A04": "Pelvis",
    "PT-L06": "Knee, side",
}

FONT = "Inter, Helvetica, Arial, sans-serif"
LABEL_SIZE = 13
RING_LABEL_SIZE = 10

DEFAULT_WIDTH = 520
DEFAULT_HEIGHT = 400


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


def render_signature_svg(
    signature: dict[str, Any],
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> str:
    params = [p for r in signature.get("regions") or [] for p in r.get("parameters") or []]
    cx, cy = width / 2, height / 2
    # Room for a two line label above and below the outer ring.
    outer = height / 2 - 2.6 * LABEL_SIZE - 10
    ring = lambda t: outer * (t + 1) / 4  # noqa: E731

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="Biomechanical signature">'
    ]

    # Bands, outermost first so each inner disc paints over the one outside.
    for t in reversed(range(len(RING_LABELS))):
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring(t):.1f}" '
            f'fill="{_tint(COLOUR[_RING_KEYS[t]], _BAND_MIX)}" '
            f'stroke="#d6dde6" stroke-width="1"/>'
        )

    n = len(params)
    if n == 0:
        parts.append("</svg>")
        return "".join(parts)

    points: list[tuple[float, float, dict[str, Any]]] = []
    for i, p in enumerate(params):
        # Half a step off vertical, so no axis runs up the chart's vertical
        # centre line, where the ring names are printed.
        a = math.radians(-90 + 360 * (i + 0.5) / n)
        ex, ey = cx + outer * math.cos(a), cy + outer * math.sin(a)
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="#d6dde6" stroke-width="1"/>'
        )
        gap = 12
        lx, ly = cx + (outer + gap) * math.cos(a), cy + (outer + gap) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.3 else ("start" if math.cos(a) > 0 else "end")
        measured = p.get("tier") is not None
        label = escape(_short(p))
        lines = 1 if measured else 2
        # Labels below the chart hang down from the ring, labels above sit
        # on it, side labels are centred on the axis.
        s = math.sin(a)
        if s > 0.3:
            y0 = ly + LABEL_SIZE * 0.8
        elif s < -0.3:
            y0 = ly - (lines - 1) * LABEL_SIZE * 1.05 - 2
        else:
            y0 = ly + LABEL_SIZE * 0.35 - (lines - 1) * LABEL_SIZE * 0.5
        second = "" if measured else (
            f'<tspan x="{lx:.1f}" dy="{LABEL_SIZE * 1.05:.1f}" '
            f'font-size="{LABEL_SIZE - 2}">not measured</tspan>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{y0:.1f}" font-size="{LABEL_SIZE}" text-anchor="{anchor}" '
            f'fill="{"#1f2a44" if measured else GREY}" '
            f'font-family="{FONT}">{label}{second}</text>'
        )
        if measured:
            r = ring(p["tier"])
            points.append((cx + r * math.cos(a), cy + r * math.sin(a), p))

    measured_pts = [(x, y) for x, y, _ in points]
    if len(measured_pts) >= 3:
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in measured_pts)
        parts.append(
            f'<polygon points="{d}" fill="#4e888f" fill-opacity="0.16" '
            f'stroke="#3b6a70" stroke-width="2" stroke-linejoin="round"/>'
        )

    for x, y, p in points:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" '
            f'fill="{COLOUR[p["severity"]]}" stroke="#ffffff" stroke-width="1.5"/>'
        )

    # Ring names up the vertical centre line, above the outline and points,
    # each on a small paper coloured pill so a line or the outline never cuts
    # through the text. (A text halo through paint-order is not supported by
    # WeasyPrint: it painted the stroke over the letters.)
    for t, name in enumerate(RING_LABELS):
        y = cy - ring(t) + RING_LABEL_SIZE + 2
        w = len(name) * RING_LABEL_SIZE * 0.6 + 8
        h = RING_LABEL_SIZE + 4
        parts.append(
            f'<rect x="{cx - w / 2:.1f}" y="{y - RING_LABEL_SIZE - 0.5:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" rx="{h / 2:.1f}" fill="#fffdf7" fill-opacity="0.92"/>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{y:.1f}" font-size="{RING_LABEL_SIZE}" text-anchor="middle" '
            f'fill="{COLOUR[_RING_KEYS[t]]}" font-weight="600" font-family="{FONT}">'
            f"{name}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)
