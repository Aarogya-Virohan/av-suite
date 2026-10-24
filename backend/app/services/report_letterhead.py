"""
Shared report letterhead: Aarogya Virohan logo top-left, clinic co-branding
on the right.

Founders' feedback of 23 October 2026 (Exercise Library items 4 to 7): our
single logo on the top-left of every report, the clinic's own branding on
the right, and only our branding when the clinic has none. The exercise
prescription PDF uses this first. Other reports (posture, invoice) can adopt
it in their own work; nothing in the posture module is changed by this file.

The clinic logo comes from `clinics.branding_logo_url`. The CRM settings page
saves it as a data URI of any `image/*` file under 200 KB, and the API
accepts any string, so the value can also be a remote URL or something that
is not an image at all. Every value is decoded and re-encoded with Pillow
before it reaches the PDF. Anything that cannot be read (SVG, broken data,
a private host, too large) is dropped and the letterhead shows the clinic
name without a logo.
"""

from __future__ import annotations

import base64
import binascii
import io
import logging
import re
from collections.abc import Awaitable, Callable

from app.services.posture.pdf_service import (
    DEEP_TEAL,
    LIME,
    MIDNIGHT,
    MIDNIGHT_2,
    ON_DARK,
    _brand_data_uri,
)

logger = logging.getLogger(__name__)

# Raster formats Pillow reads safely. SVG is left out on purpose: it can load
# external resources and Pillow cannot read it.
_DATA_URI = re.compile(
    r"^data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/\s]+={0,2})$", re.IGNORECASE
)
LOGO_MAX_CHARS = 3_000_000  # same cap as the posture report
LOGO_MAX_BYTES = 2 * 1024 * 1024
LOGO_MAX_PX = 400


def _normalise(raw: bytes) -> str:
    """Re-encode any readable raster image as a small PNG data URI."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(raw)) as img:
        img.load()
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGBA")
        img.thumbnail((LOGO_MAX_PX, LOGO_MAX_PX))
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def logo_from_data_uri(value: str) -> str:
    """PNG data URI for a stored data URI logo, or "" when it is not usable."""
    if len(value) > LOGO_MAX_CHARS:
        return ""
    match = _DATA_URI.match(value.strip())
    if not match:
        return ""
    try:
        raw = base64.b64decode(re.sub(r"\s", "", match.group(2)), validate=True)
    except (binascii.Error, ValueError):
        return ""
    if not raw or len(raw) > LOGO_MAX_BYTES:
        return ""
    try:
        return _normalise(raw)
    except Exception as exc:  # not an image, truncated, decompression bomb
        logger.warning("Clinic logo skipped: %s", type(exc).__name__)
        return ""


async def resolve_clinic_logo(
    value: str | None,
    fetch: Callable[[str], Awaitable[bytes | None]] | None = None,
) -> str:
    """
    Turn `clinics.branding_logo_url` into a PNG data URI for the letterhead.

    Data URIs are decoded here. An https URL is downloaded with `fetch`, which
    the caller provides with its own safety rules (public host only, timeout,
    size cap). Returns "" when there is no usable logo.
    """
    if not value or not isinstance(value, str):
        return ""
    value = value.strip()
    if value.lower().startswith("data:"):
        return logo_from_data_uri(value)
    if value.lower().startswith("https://") and fetch is not None:
        try:
            raw = await fetch(value)
        except Exception as exc:  # network, timeout
            logger.warning("Clinic logo download failed: %s", type(exc).__name__)
            return ""
        if not raw or len(raw) > LOGO_MAX_BYTES:
            return ""
        try:
            return _normalise(raw)
        except Exception as exc:
            logger.warning("Clinic logo skipped: %s", type(exc).__name__)
            return ""
    return ""


def letterhead_css() -> str:
    return f"""
.letterhead {{ position: running(letterhead); width: 100%;
  background: linear-gradient(115deg, {MIDNIGHT} 0%, {MIDNIGHT_2} 55%, {DEEP_TEAL} 100%);
  padding: 4.6mm 14mm 4.2mm 14mm; color: #fff; box-sizing: border-box; }}
.lh {{ width: 100%; border-collapse: collapse; }}
.lh td {{ vertical-align: middle; padding: 0; }}
.lh-av {{ width: 55%; }}
.lh-av .av-wordmark {{ height: 7.4mm; width: auto; display: block; }}
.lh-av .av-text {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800;
  font-size: 12.5pt; color: #fff; }}
.lh-sub {{ font-size: 7.6pt; color: {ON_DARK}; margin-top: 1.4mm; letter-spacing: 0.4px; }}
.lh-sub::after {{ content: ""; display: block; width: 8mm; height: 0.7mm; background: {LIME};
  margin-top: 1.2mm; border-radius: 1mm; }}
.lh-clinic {{ text-align: right; }}
.lh-logo {{ width: 13mm; padding-left: 3.5mm !important; }}
.lh-logo .tile {{ width: 13mm; height: 13mm; background: #fff; border-radius: 3mm;
  text-align: center; line-height: 13mm; }}
.lh-logo .tile img {{ max-width: 11mm; max-height: 11mm; vertical-align: middle; }}
.lh-label {{ font-size: 6.4pt; font-weight: 700; letter-spacing: 1.1px; text-transform: uppercase;
  color: {ON_DARK}; margin-bottom: 0.8mm; }}
.clinic-name {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800;
  font-size: 11.5pt; line-height: 1.2; color: #fff; }}
"""


def letterhead_html(
    subtitle_html: str, clinic_name_html: str = "", clinic_logo_src: str = ""
) -> str:
    """
    The running letterhead band. Arguments are already HTML-escaped by the
    caller; `clinic_logo_src` must be a data URI from `resolve_clinic_logo`.
    With no clinic name the right side is left empty (Aarogya Virohan only).
    """
    wordmark = _brand_data_uri("av_logo_wordmark_white.png")
    av = (
        f'<img class="av-wordmark" src="{wordmark}" alt="Aarogya Virohan" />'
        if wordmark
        else '<span class="av-text">Aarogya Virohan</span>'
    )
    clinic, logo = "", ""
    if clinic_name_html:
        clinic = (
            f'<td class="lh-clinic"><p class="lh-label">Clinic</p>'
            f'<p class="clinic-name">{clinic_name_html}</p></td>'
        )
        if clinic_logo_src:
            logo = (
                f'<td class="lh-logo"><div class="tile"><img src="{clinic_logo_src}" alt="" />'
                "</div></td>"
            )
    return f"""
<div class="letterhead"><table class="lh"><tr>
  <td class="lh-av">{av}<p class="lh-sub">{subtitle_html}</p></td>
  {clinic}{logo}
</tr></table></div>
"""
