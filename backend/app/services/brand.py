"""
Shared Aarogya Virohan brand: palette, "powered by" words, and the brand
images and fonts embedded as data URIs.

Every PDF (posture report, exercise prescription, invoice, receipt) and the
shared report letterhead take these from here. They used to live in
posture/pdf_service.py, which made report_letterhead import the posture
module; the posture report could then not use the letterhead without a
circular import. posture/pdf_service.py re-exports the old names.
"""

from __future__ import annotations

import base64
import io
from functools import lru_cache
from pathlib import Path

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

# The image and font files still live in posture/brand (the posture report
# was their first user). Moving the files themselves is a separate step.
BRAND_DIR = Path(__file__).parent / "posture" / "brand"


@lru_cache(maxsize=None)
def brand_data_uri(filename: str) -> str:
    """
    Embed a brand image as a data URI, so the PDF never depends on a base
    URL or on the working directory WeasyPrint happens to run from. Returns
    an empty string when the file is missing, and the template then leaves
    the logo out instead of failing the whole report.
    """

    path = BRAND_DIR / filename
    if not path.is_file():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@lru_cache(maxsize=None)
def font_faces() -> str:
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
        path = BRAND_DIR / "fonts" / filename
        if not path.is_file():
            continue
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
            f"font-style: normal; src: url(data:font/woff;base64,{encoded}) format('woff'); }}"
        )
    return "\n".join(rules)


# Prescription watermark (D-038, Onkar 14 Nov 2026): the new round mark,
# faded to WATERMARK_OPACITY. WeasyPrint has no opacity for @page
# backgrounds, so the fade is baked into the image here. To drop the
# watermark (if the founders say no), set WATERMARK_FILE = "".
WATERMARK_FILE = "av_logo_round.png"
WATERMARK_OPACITY = 0.06
WATERMARK_WHITE = 235  # luminance at or above this counts as the white background


@lru_cache(maxsize=None)
def watermark_data_uri() -> str:
    """The watermark as a faded PNG data URI; empty when switched off or missing."""

    if not WATERMARK_FILE:
        return ""
    path = BRAND_DIR / WATERMARK_FILE
    if not path.is_file():
        return ""
    from PIL import Image

    with Image.open(path) as source:
        image = source.convert("RGBA")
    # The mark sits on a white disc; faded, that disc would show as a pale
    # patch on the cream page. Near-white pixels are dropped, the artwork kept.
    red, green, blue, alpha = image.split()
    light = Image.merge("RGB", (red, green, blue)).convert("L").point(lambda v: 0 if v >= WATERMARK_WHITE else 255)
    alpha = Image.composite(alpha, Image.new("L", image.size, 0), light)
    image.putalpha(alpha.point(lambda a: round(a * WATERMARK_OPACITY)))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
