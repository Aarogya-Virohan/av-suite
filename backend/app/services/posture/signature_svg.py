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

17 November 2026 (coordinator review of v4): each axis carries its table
row's label word for word, wrapped to fit, and the ring names moved off the
vertical centre line, where the "Normal" pill covered two points, into the
gap between two axes that is clear of every point and the outline.
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

# Axis names, 17 November 2026 (coordinator review): the row's own label,
# the exact text the report table prints, so the chart can never call a
# measure something the table does not. Long names wrap; the words do not
# change.

FONT = "Inter, Helvetica, Arial, sans-serif"
LABEL_SIZE = 15  # 13 until 17 Nov 2026; raised with the smaller PDF chart so axis names stay at 8 pt or more
RING_LABEL_SIZE = 13  # 10 until 17 Nov 2026, same reason

# 540 since 17 Nov 2026 (520 before) so the full table labels fit beside
# the chart: 15 units on the 102 mm PDF chart is still 8.0 pt.
DEFAULT_WIDTH = 540
DEFAULT_HEIGHT = 400


# Width of one character, as a share of the font size, used only to decide
# where a name wraps. Measured on the rendered PDF: Inter runs about 0.50 em
# a character in these labels.
CHAR_W = 0.52
# The ring-name pills keep the width formula they had before.
PILL_CHAR_W = 0.6
SIDE_MARGIN = 4


def _text_w(text: str, size: float) -> float:
    return len(text) * size * CHAR_W


def _wrap(name: str, room: float) -> list[str]:
    """
    The label in as few lines as fit `room` units, broken at spaces, and
    after a hyphen only when one word is wider than the room on its own.
    The words and their case stay exactly as the table prints them.
    """
    words: list[str] = []
    for word in name.split():
        if _text_w(word, LABEL_SIZE) <= room or "-" not in word:
            words.append(word)
            continue
        piece = ""
        for part in word.split("-")[:-1]:
            if piece and _text_w(piece + part + "-", LABEL_SIZE) > room:
                words.append(piece)
                piece = ""
            piece += part + "-"
        last = word.split("-")[-1]
        if piece and _text_w(piece + last, LABEL_SIZE) > room:
            words.append(piece)
            piece = ""
        words.append(piece + last)
    lines: list[str] = []
    for word in words:
        joined = f"{lines[-1]} {word}" if lines and not lines[-1].endswith("-") else (
            f"{lines[-1]}{word}" if lines else word
        )
        if lines and _text_w(joined, LABEL_SIZE) <= room:
            lines[-1] = joined
        else:
            lines.append(word)
    return lines or [name]


def _seg_hits_rect(x1, y1, x2, y2, rx0, ry0, rx1, ry1) -> bool:
    """Whether the segment touches the rectangle (Liang-Barsky clip)."""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rx0), (dx, rx1 - x1), (-dy, y1 - ry0), (dy, ry1 - y1)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def _circle_hits_rect(x, y, r, rx0, ry0, rx1, ry1) -> bool:
    nx, ny = min(max(x, rx0), rx1), min(max(y, ry0), ry1)
    return (x - nx) ** 2 + (y - ny) ** 2 < r * r


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
    angles: list[float] = []
    label_boxes: list[tuple[float, float, float, float]] = []
    for i, p in enumerate(params):
        # Half a step off vertical, so no axis runs up the chart's vertical
        # centre line, where the ring names are printed.
        a = math.radians(-90 + 360 * (i + 0.5) / n)
        angles.append(a)
        ex, ey = cx + outer * math.cos(a), cy + outer * math.sin(a)
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="#d6dde6" stroke-width="1"/>'
        )
        gap = 12
        lx, ly = cx + (outer + gap) * math.cos(a), cy + (outer + gap) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.3 else ("start" if math.cos(a) > 0 else "end")
        measured = p.get("tier") is not None
        if anchor == "start":
            room = width - lx - SIDE_MARGIN
        elif anchor == "end":
            room = lx - SIDE_MARGIN
        else:
            room = 2 * min(lx, width - lx) - 2 * SIDE_MARGIN
        name_lines = _wrap(p.get("label") or "", room)
        lines = len(name_lines) + (0 if measured else 1)
        # Labels below the chart hang down from the ring, labels above sit
        # on it, side labels are centred on the axis.
        s = math.sin(a)
        if s > 0.3:
            y0 = ly + LABEL_SIZE * 0.8
        elif s < -0.3:
            y0 = ly - (lines - 1) * LABEL_SIZE * 1.05 - 2
        else:
            y0 = ly + LABEL_SIZE * 0.35 - (lines - 1) * LABEL_SIZE * 0.5
        # One <text> per line: WeasyPrint anchors a shorter first line of a
        # multi-tspan text="end" label against the widest line, so a three
        # line name printed ragged (seen 17 Nov 2026).
        rows = [(line, LABEL_SIZE) for line in name_lines]
        if not measured:
            note = "under review" if p.get("severity") == "under_review" else "not measured"
            rows.append((note, LABEL_SIZE - 2))
        for k, (line, size) in enumerate(rows):
            tw = _text_w(line, size)
            bx0 = lx - tw if anchor == "end" else (lx - tw / 2 if anchor == "middle" else lx)
            by = y0 + k * LABEL_SIZE * 1.05
            label_boxes.append((bx0, by - size * 0.8, bx0 + tw, by + size * 0.25))
            parts.append(
                f'<text x="{lx:.1f}" y="{y0 + k * LABEL_SIZE * 1.05:.1f}" font-size="{size}" '
                f'text-anchor="{anchor}" fill="{"#1f2a44" if measured else GREY}" '
                f'font-family="{FONT}">{escape(line)}</text>'
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

    # Ring names, 17 November 2026 (coordinator review of v4). Until then
    # they ran up the vertical centre line and the "Normal" pill covered
    # the two points either side of it. Now "Normal" sits on the centre,
    # where no point can ever be (a point sits on a ring line, the
    # innermost at ring(0), and the outline stays outside that ring when
    # every axis is measured), as the key says: normal at the centre.
    # Mild, Moderate and Severe sit in their own bands along the bisector
    # of one gap between two axes: the gap where none of them touches a
    # point or the outline, nearest the top when several are clear. Each
    # starts mid-band and may move up to ten units along the bisector,
    # inside its band, to clear the outline. When no one gap clears all
    # three (an outline that zigzags across the bands), a name that would
    # touch goes to the nearest gap where it is clear. (With an unmeasured
    # axis the outline skips it and can pass behind the centre pill; no
    # point can.) Same pills as before: a small
    # paper coloured pill so a grid line never cuts through the text. (A
    # text halo through paint-order is not supported by WeasyPrint: it
    # painted the stroke over the letters.)
    clear = 4.0
    dot_r = 5.5 + 1.5 + clear
    edges = [
        (*measured_pts[k], *measured_pts[(k + 1) % len(measured_pts)])
        for k in range(len(measured_pts))
    ] if len(measured_pts) >= 2 else []

    def pill(t: int, gap: float, shift: float = 0.0) -> tuple[float, float, float, float]:
        w = len(RING_LABELS[t]) * RING_LABEL_SIZE * PILL_CHAR_W + 8
        h = RING_LABEL_SIZE + 4
        r_mid = 0.0 if t == 0 else (ring(t - 1) + ring(t)) / 2 + shift
        px, py = cx + r_mid * math.cos(gap), cy + r_mid * math.sin(gap)
        return px - w / 2, py - h / 2, px + w / 2, py + h / 2

    # 23 Nov 2026 (Posture fixes lane): the three names were placed one by
    # one, so in a gap near the horizontal the 38 unit bands were narrower
    # than the pills and Mild sat on top of Moderate ("M Mildoderate"), and
    # a name moved to another gap could land on an axis name. Now every
    # candidate spot is also checked against the pills already placed and
    # against the axis names; when no bisector is clear, the name may sit
    # anywhere along its band (every 5 degrees).
    band = ring(1) - ring(0)
    limit = max(0.0, band / 2 - (RING_LABEL_SIZE + 4) / 2 - 1)
    shifts = [0.0] + [s * d for d in (2.0, 4.0, 6.0, 8.0, 10.0) if d <= limit + 4 for s in (-1, 1)]
    placed: list[tuple[float, float, float, float]] = []
    pad = 3.0

    def _rects_hit(a, b) -> bool:
        return a[0] < b[2] + pad and b[0] < a[2] + pad and a[1] < b[3] + pad and b[1] < a[3] + pad

    def hits(t: int, gap: float, shift: float) -> int:
        x0, y0, x1, y1 = rect = pill(t, gap, shift)
        box = (x0 - clear, y0 - clear, x1 + clear, y1 + clear)
        count = sum(_circle_hits_rect(x, y, dot_r, x0, y0, x1, y1) for x, y, _ in points)
        count += sum(_seg_hits_rect(*e, *box) for e in edges)
        count += 3 * sum(_rects_hit(rect, b) for b in label_boxes)
        count += 5 * sum(_rects_hit(rect, b) for b in placed)
        return count

    def place(t: int, gap: float) -> tuple[int, float]:
        """(touches, shift) of the clearest spot for ring name t in this gap."""
        return min((hits(t, gap, d), abs(d), d) for d in shifts)[0::2]

    gaps = [math.radians(-90 + 360 * i / n) for i in range(n)]
    sweep = [math.radians(-90 + 5 * k) for k in range(72)]

    def near_top(g: float) -> float:
        return 1 - math.cos(g + math.pi / 2)

    def try_gap(gap: float) -> list[tuple[float, float]] | None:
        """All three names on this bisector, clear of everything, or None."""
        spots = []
        for t in range(1, len(RING_LABELS)):
            k, d = place(t, gap)
            if k:
                del placed[len(placed) - len(spots):]
                return None
            spots.append((gap, d))
            placed.append(pill(t, gap, d))
        return spots

    placed.append(pill(0, 0.0))
    spots: list[tuple[float, float]] | None = None
    for g in sorted(gaps, key=near_top):
        spots = try_gap(g)
        if spots:
            break
    if not spots:
        # Each name on its own: a clear bisector first, then anywhere along
        # its band, nearest the top; least touches when nothing is clear.
        spots = []
        for t in range(1, len(RING_LABELS)):
            cands = sorted(gaps, key=near_top) + sorted(sweep, key=near_top)
            scored = [(place(t, g), i, g) for i, g in enumerate(cands)]
            (k, d), _, g = min(scored, key=lambda z: (z[0][0], z[1]))
            spots.append((g, d))
            placed.append(pill(t, g, d))
    all_spots = [(0.0, 0.0)] + spots

    for t, name in enumerate(RING_LABELS):
        x0, y0, x1, y1 = pill(t, *all_spots[t])
        h = y1 - y0
        parts.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" '
            f'height="{h:.1f}" rx="{h / 2:.1f}" fill="#fffdf7" fill-opacity="0.92"/>'
        )
        parts.append(
            f'<text x="{(x0 + x1) / 2:.1f}" y="{y1 - 3.5:.1f}" '
            f'font-size="{RING_LABEL_SIZE}" text-anchor="middle" '
            f'fill="{COLOUR[_RING_KEYS[t]]}" font-weight="600" font-family="{FONT}">'
            f"{name}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)
