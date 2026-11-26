"""
Shared report letterhead: the clinic's branding on the left, Aarogya Virohan
on the right.

Founders' rule of 12 November 2026: "the clinic is the hero, Aarogya Virohan
is the backend partner". On every patient-facing document the clinic's logo
and name sit top-left as the primary brand and the Aarogya Virohan wordmark
sits top-right, smaller. A clinic without branding gets an Aarogya Virohan
only letterhead, wordmark on the left as before. This replaces the 23 October
feedback (items 6 and 7, our logo top-left). The exercise prescription and
the invoice / receipt PDFs use this file; the posture report has its own
letterhead in the posture module and is not changed here.

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
import html
import io
import logging
import re
from collections.abc import Awaitable, Callable
from functools import cache

from app.services.brand import (
    DEEP_TEAL,
    GROVE,
    INK,
    LIME,
    MIDNIGHT,
    MUTED,
    POWERED_BY_COMPANY,
    POWERED_BY_PRODUCT,
    RULE,
    brand_data_uri,
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


# Logo trim: clinics upload logos with large empty margins (a 1080 px square
# with a small wordmark in the middle). Empty margins are cut before sizing so
# the logo itself fills the letterhead box. Transparent margins are cut by
# alpha; an opaque background is cut only when all four corners share one
# colour (otherwise the "background" may be part of the logo).
_TRIM_ALPHA = 16
_TRIM_DIFF = 24
_TRIM_PAD = 0.02


def _trim_background(img):  # PIL RGBA image in, PIL RGBA image out
    from PIL import Image, ImageChops

    w, h = img.size
    alpha = img.getchannel("A")
    if alpha.getextrema()[0] < 250:
        box = alpha.point(lambda a: 255 if a > _TRIM_ALPHA else 0).getbbox()
    else:
        rgb = img.convert("RGB")
        corners = [rgb.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
        if any(max(abs(a - b) for a, b in zip(c, corners[0], strict=True)) > _TRIM_DIFF for c in corners):
            return img
        bg = Image.new("RGB", (w, h), corners[0])
        diff = ImageChops.difference(rgb, bg).convert("L")
        box = diff.point(lambda v: 255 if v > _TRIM_DIFF else 0).getbbox()
        if box and min(corners[0]) >= _LIGHT_BG:
            img = _clear_light_background(img)
    if not box:
        return img
    pad = max(2, round(_TRIM_PAD * max(box[2] - box[0], box[3] - box[1])))
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(w, box[2] + pad), min(h, box[3] + pad))
    return img if box == (0, 0, w, h) else img.crop(box)


# An opaque logo on a white (or near-white) canvas shows as a white box on a
# tinted page (the prescription page is cream). The light background that
# touches the edges is made transparent by flood fill from the four corners;
# light areas enclosed by the artwork (inside letters) are kept.
_LIGHT_BG = 235
_FILL_THRESH = 28


def _clear_light_background(img):  # PIL RGBA image in, PIL RGBA image out
    from PIL import ImageDraw

    img = img.copy()
    w, h = img.size
    for xy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if img.getpixel(xy)[3] != 0:
            ImageDraw.floodfill(img, xy, (255, 255, 255, 0), thresh=_FILL_THRESH)
    return img


def _normalise(raw: bytes) -> str:
    """Re-encode any readable raster image as a small PNG data URI."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(raw)) as img:
        img.load()
        img = ImageOps.exif_transpose(img)
        img = _trim_background(img.convert("RGBA"))
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
    # White, shallow, print-friendly header that belongs to the clinic only:
    # logo and name on the left, the clinic's contacts on the right, one
    # accent rule underneath. Aarogya Virohan appears in the footer only.
    return f"""
.letterhead {{ position: running(letterhead); width: 100%; box-sizing: border-box;
  padding: {LH_PAD_TOP_MM}mm 14mm 0 14mm; }}
.lh {{ width: 100%; border-collapse: collapse; }}
.lh td {{ vertical-align: middle; padding: 0; }}
.lh-rule {{ height: {LH_RULE_MM}mm; margin-top: {LH_PAD_BOTTOM_MM}mm; border-radius: 0.4mm;
  background: linear-gradient(90deg, {MIDNIGHT} 0%, {DEEP_TEAL} 70%, {LIME} 100%); }}
.lh-clinic {{ text-align: left; }}
.lh-logo {{ width: 1%; padding-right: 3.5mm !important; }}
.lh-logo .tile {{ height: 13mm; text-align: center; line-height: 13mm; }}
.lh-logo .tile img {{ vertical-align: middle; }}
.av-only {{ width: 1%; padding-right: 3.5mm !important; }}
.av-round {{ width: 14mm; height: 14mm; display: block; }}
.clinic-name {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800;
  font-size: 13pt; line-height: 1.18; color: {MIDNIGHT}; }}
.clinic-name.long {{ font-size: 11pt; }}
.clinic-name.xlong {{ font-size: 9.8pt; }}
.lh-sub {{ font-size: 7pt; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase;
  color: {GROVE}; margin-top: 1.2mm; }}
.lh-contact-cell {{ width: {LH_CONTACT_W_MM}mm; padding: 0 5mm 0 5mm !important; vertical-align: middle; }}
.lh-contact {{ border-collapse: collapse; margin-left: auto; }}
.lh-divider {{ width: 0; border-left: 0.35mm solid #cfd6dc; }}
.lh-mark {{ width: 1%; padding-left: 5mm !important; text-align: right; }}
.lh-contact td {{ padding: 0.35mm 0 !important; vertical-align: top; }}
.lh-contact .ic {{ width: 4.6mm; padding-top: 0.55mm !important; }}
.lh-contact .ic img {{ width: 2.8mm; height: 2.8mm; display: block; }}
.lh-contact .cv {{ font-size: 7.4pt; line-height: 1.32; color: {INK}; overflow-wrap: anywhere; }}
.lh-contact .ck {{ font-size: 6pt; font-weight: 700; letter-spacing: 0.8px; color: {MUTED};
  margin-right: 1.2mm; }}
"""


# --------------------------------------------------------------------------
# Clinic details on the letterhead (D-036). One set of rules for every
# report: only filled fields are shown, in a fixed order, separators only
# between filled values, so a missing field never leaves a gap.
# --------------------------------------------------------------------------
NAME_LONG = 30
NAME_XLONG = 45
_PINCODE = re.compile(r"^\d{6}$")


def _filled(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def format_address(
    address_line: str | None,
    city: str | None = None,
    state: str | None = None,
    pincode: str | None = None,
) -> str:
    """'line, city, state pincode'; parts already inside the line are not repeated."""
    line, city_, state_, pin = (_filled(v) for v in (address_line, city, state, pincode))
    low = line.lower()
    parts = [line] if line else []
    if city_ and city_.lower() not in low:
        parts.append(city_)
    tail = " ".join(
        v
        for v in (
            state_ if state_ and state_.lower() not in low else "",
            pin if _PINCODE.match(pin) and pin not in line else "",
        )
        if v
    )
    if tail:
        parts.append(tail)
    return ", ".join(parts)


def format_website(value: str | None) -> str:
    """Show a website without the scheme and the trailing slash."""
    site = _filled(value)
    site = re.sub(r"^https?://", "", site, flags=re.IGNORECASE)
    return site.rstrip("/")


ClinicDetail = tuple[str, str]  # (label, HTML-escaped value)
IDS_LABELS = ("Reg. No.", "GSTIN")


def clinic_details(
    *,
    address_line: str | None = None,
    city: str | None = None,
    state: str | None = None,
    pincode: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    registration_number: str | None = None,
    gstin: str | None = None,
) -> list[ClinicDetail]:
    """
    The clinic's details as (label, value) pairs in a fixed order: Address,
    Phone, Email, Website, Reg. No., GSTIN. Values are HTML-escaped. Empty
    fields are dropped, so nothing is ever shown as an empty label.
    """
    items = (
        ("Address", format_address(address_line, city, state, pincode)),
        ("Phone", _filled(phone)),
        ("Email", _filled(email)),
        ("Website", format_website(website)),
        ("Reg. No.", _filled(registration_number)),
        ("GSTIN", _filled(gstin)),
    )
    return [(label, html.escape(value)) for label, value in items if value]


def clinic_detail_lines(**fields: str | None) -> list[str]:
    """
    The same details as plain lines (one item per line, ids prefixed with
    their label), for places that show them as a list.
    """
    return [
        f"{label} {value}" if label in IDS_LABELS else value
        for label, value in clinic_details(**fields)
    ]



# Header geometry (mm). `letterhead_page_top_mm` adds these up so every
# report's @page top margin fits the header; the contact block height is
# estimated from the number of lines (address wrap capped), erring tall.
LH_PAD_TOP_MM = 5.2
LH_PAD_BOTTOM_MM = 3.0
LH_RULE_MM = 0.8
LH_BODY_GAP_MM = 6.0
LH_BRAND_MM = 14.0          # logo / Aarogya Virohan mark height
LH_LINE_MM = 3.4            # one contact line
LH_CONTACT_W_MM = 58        # contact column incl. padding
_ADDRESS_CHARS_PER_LINE = 40
_ADDRESS_MAX_LINES = 3


def _detail_line_count(details: list[ClinicDetail]) -> int:
    lines = 0
    for label, value in details:
        if label == "Address":
            n = len(html.unescape(value))
            lines += min(_ADDRESS_MAX_LINES, max(1, -(-n // _ADDRESS_CHARS_PER_LINE)))
        else:
            lines += 1
    return lines


def letterhead_page_top_mm(details: list[ClinicDetail] | None) -> float:
    """
    @page top margin that fits the header with these details, so the header
    never runs into the body however many details a clinic has filled in.
    Without details it is 29 mm (27 mm before D-036; 2 mm more space under
    the header rule).
    """
    content = max(LH_BRAND_MM, LH_LINE_MM * _detail_line_count(details or []))
    return round(LH_PAD_TOP_MM + content + LH_PAD_BOTTOM_MM + LH_RULE_MM + LH_BODY_GAP_MM, 1)


# Small line icons for the contact block (stroke only, print friendly).
_ICON_PATHS = {
    "Address": '<path d="M12 21s-6-5.4-6-10a6 6 0 0 1 12 0c0 4.6-6 10-6 10z"/><circle cx="12" cy="11" r="2.2"/>',
    "Phone": '<path d="M5 4h3l2 5-2.5 1.5a11 11 0 0 0 6 6L15 14l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    "Email": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5 12 13l8.5-6.5"/>',
    "Website": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
}


@cache
def _icon_uri(label: str) -> str:
    paths = _ICON_PATHS.get(label)
    if not paths:
        return ""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{GROVE}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{paths}</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode("ascii")


def _contact_html(details: list[ClinicDetail]) -> str:
    """The clinic's contact block: one item per row, icon or short label first."""
    if not details:
        return ""
    rows = []
    for label, value in details:
        icon = _icon_uri(label)
        if icon:
            rows.append(
                f'<tr><td class="ic"><img src="{icon}" alt="{html.escape(label)}" /></td>'
                f'<td class="cv">{value}</td></tr>'
            )
        else:
            rows.append(
                f'<tr><td class="ic"></td><td class="cv"><span class="ck">'
                f"{html.escape(label).upper()}</span>{value}</td></tr>"
            )
    return '<td class="lh-contact-cell"><table class="lh-contact">' + "".join(rows) + "</table></td>"


def _name_class(clinic_name_html: str) -> str:
    n = len(html.unescape(clinic_name_html))
    return "clinic-name xlong" if n > NAME_XLONG else "clinic-name long" if n > NAME_LONG else "clinic-name"


# --------------------------------------------------------------------------
# Running footer shared by the prescription and invoice / receipt PDFs
# (D-036): "Powered by Aarogya Virohan • AV Suite" on the left, page count
# on the right. No patient name or ID in the footer (founders, 13 Nov).
# --------------------------------------------------------------------------
def footer_css() -> str:
    # The footer exactly as it was before D-036 (centred, old Aarogya Virohan
    # mark), minus the patient name and prescription reference: founders
    # 14 Nov, no patient data in the footer. The page count is on its own
    # centred line, inline text, where WeasyPrint fills counter(pages).
    # border-box (the only change in look): the old footer's 14 mm padding
    # was added to 100% width, so its top line ran past the right margin
    # and the centred text sat about 7 mm right of centre.
    return f"""
.running-footer {{ position: running(runningFooter); width: 100%; padding: 0 14mm; text-align: center;
  box-sizing: border-box; }}
.running-footer .inner {{ border-top: 1px solid {RULE}; padding-top: 2.4mm; }}
.running-footer .powered {{ font-size: 7pt; letter-spacing: 0.9px; color: {MUTED}; }}
.running-footer .powered .by {{ font-weight: 700; }}
.running-footer .powered .company {{ font-weight: 700; color: {MIDNIGHT}; }}
.running-footer .powered .dot {{ color: {GROVE}; margin: 0 3px; }}
.running-footer .powered .product {{ font-weight: 700; color: {GROVE}; }}
.running-footer .powered .mark {{ height: 3.6mm; width: auto; vertical-align: -0.9mm; margin-right: 1.6mm; }}
.running-footer .meta {{ margin-top: 1.2mm; font-size: 6.8pt; color: {MUTED}; }}
.running-footer .meta .page::after {{ content: "Page " counter(page) " of " counter(pages); }}
.running-footer .meta .sep {{ margin: 0 1.6mm; color: {GROVE}; }}
"""


def footer_html(reference: str = "") -> str:
    """
    Shared footer. `reference` is the document number shown before the page
    count, e.g. "Rx RX-7B825459" or "Invoice INV-0042" (D-038): page 2 of a
    long prescription then still says which document it belongs to, without
    any patient data. Empty reference = page count only.
    """

    mark = brand_data_uri("av_mark.png")
    footer_mark = f'<img class="mark" src="{mark}" alt="" />' if mark else ""
    ref = reference.strip()
    ref_html = (
        f'<span class="ref">{html.escape(ref)}</span><span class="sep">&middot;</span>' if ref else ""
    )
    return f"""<div class="running-footer"><div class="inner">
  <p class="powered">{footer_mark}<span class="by">POWERED BY</span>
    <span class="company">{POWERED_BY_COMPANY}</span><span class="dot">&bull;</span><span class="product">{POWERED_BY_PRODUCT}</span></p>
  <p class="meta">{ref_html}<span class="page"></span></p>
</div></div>"""


# Clinic logo box in the letterhead, in millimetres. Square logos keep the
# old 11 mm square inside a 13 mm tile; wide wordmarks (most clinic logos)
# keep the 11 mm height and grow sideways up to LOGO_MAX_W_MM, so they are
# not shrunk into a square tile until the text is unreadable.
LOGO_H_MM = 11.0
LOGO_MAX_W_MM = 40.0
LOGO_TILE_PAD_MM = 2.0


def _png_size(data_uri: str) -> tuple[int, int] | None:
    """Width and height from the IHDR chunk of a base64 PNG data URI."""
    prefix = "data:image/png;base64,"
    if not data_uri.startswith(prefix):
        return None
    try:
        head = base64.b64decode(data_uri[len(prefix) : len(prefix) + 44])
    except (binascii.Error, ValueError):
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    width = int.from_bytes(head[16:20], "big")
    height = int.from_bytes(head[20:24], "big")
    return (width, height) if width > 0 and height > 0 else None


def _logo_box_mm(data_uri: str) -> tuple[float, float, float]:
    """(image width, image height, tile width) in mm, keeping the logo's ratio."""
    size = _png_size(data_uri)
    if size is None:
        return LOGO_H_MM, LOGO_H_MM, LOGO_H_MM + LOGO_TILE_PAD_MM
    w, h = size
    if w <= h:  # square or tall: fit the 11 mm square as before
        return round(LOGO_H_MM * w / h, 2), LOGO_H_MM, LOGO_H_MM + LOGO_TILE_PAD_MM
    width, height = LOGO_H_MM * w / h, LOGO_H_MM
    if width > LOGO_MAX_W_MM:
        width, height = LOGO_MAX_W_MM, LOGO_MAX_W_MM * h / w
    return round(width, 2), round(height, 2), round(width + LOGO_TILE_PAD_MM, 2)


def letterhead_html(
    subtitle_html: str,
    clinic_name_html: str = "",
    clinic_logo_src: str = "",
    details: list[ClinicDetail] | None = None,
) -> str:
    """
    The running header. Arguments are already HTML-escaped by the caller
    (`clinic_details` escapes its own values); `clinic_logo_src` must be a
    data URI from `resolve_clinic_logo`.

    With a clinic name: clinic logo, name and document type on the left; the
    clinic's contacts next; then a thin standing rule and the Aarogya
    Virohan mark on the far right, so the contacts read as the clinic's.
    Without a clinic name: Aarogya Virohan mark, name and document type. Size the page's top margin with
    `letterhead_page_top_mm(details)`.
    """
    rule = '<div class="lh-rule"></div>'
    if not clinic_name_html:
        av_src = brand_data_uri("av_logo_round.png")
        mark = (
            f'<td class="av-only"><img class="av-round" src="{av_src}" alt="Aarogya Virohan" /></td>'
            if av_src
            else ""
        )
        return f"""
<div class="letterhead"><table class="lh"><tr>
  {mark}<td class="lh-av-name"><p class="clinic-name">Aarogya Virohan</p>
  <p class="lh-sub">{subtitle_html}</p></td>
</tr></table>{rule}</div>
"""
    # Aarogya Virohan mark on the far right, kept apart from the clinic's
    # contacts by a thin standing rule, so the contacts read as the clinic's.
    av_src = brand_data_uri("av_logo_round.png")
    mark = f'<td class="lh-mark"><img class="av-round" src="{av_src}" alt="Aarogya Virohan" /></td>' if av_src else ""
    divider = '<td class="lh-divider"></td>' if mark and details else ""
    logo = ""
    if clinic_logo_src:
        img_w, img_h, tile_w = _logo_box_mm(clinic_logo_src)
        logo = (
            f'<td class="lh-logo"><div class="tile" style="width: {tile_w}mm">'
            f'<img src="{clinic_logo_src}" alt="" '
            f'style="width: {img_w}mm; height: {img_h}mm" /></div></td>'
        )
    return f"""
<div class="letterhead"><table class="lh"><tr>
  {logo}<td class="lh-clinic"><p class="{_name_class(clinic_name_html)}">{clinic_name_html}</p>
  <p class="lh-sub">{subtitle_html}</p></td>
  {_contact_html(details or [])}{divider}{mark}
</tr></table>{rule}</div>
"""


# ==========================================================================
# Clinical report letterhead, Round 4 (Shivank sir, 26 Nov 2026; tracks/crm
# BR-b..BR-n). Used by the exercise prescription, the posture report and the
# psychosocial report. Invoices and receipts are plain black and white and
# do not use any of this (BR-m).
#
# Page anatomy, every page:
#   top band (teal, full width): clinic logo box + display doctor name,
#     clinic phone, clinic email on the left; Aarogya Virohan round logo on
#     the right.
#   body on pure white, faint Aarogya Virohan round mark in the centre.
#   clinic block on white just above the bottom band: full name, address,
#     website (each only if set).
#   bottom band (teal): "Powered by Aarogya Virohan . AV Suite", document
#     number, "Page x of y".
# ==========================================================================

from dataclasses import dataclass  # noqa: E402

from app.services.brand import (  # noqa: E402
    BAND_END,
    BAND_START,
    BAND_TINT,
    ON_DARK,
    ON_DARK_STRONG,
    RULE_SOFT,
    RULE_STRONG,
)

# Logo background modes (clinics.logo_bg_mode, BR-b).
LOGO_BG_AS_IS = "as_is"
LOGO_BG_WHITE = "white"
LOGO_BG_TRANSPARENT = "transparent"
LOGO_BG_MODES = (LOGO_BG_AS_IS, LOGO_BG_WHITE, LOGO_BG_TRANSPARENT)

# Upload rules (BR-g). The upload limit is on the file the user picks; what
# is stored is the server-resized copy, capped by MAX_LOGO_BYTES.
LOGO_UPLOAD_MAX_BYTES = 2 * 1024 * 1024
LOGO_MIN_SHORT_SIDE_PX = 200
LOGO_MAX_ASPECT = 4.0
LOGO_STORE_MAX_PX = 800
LOGO_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


class LogoRejected(ValueError):
    """An uploaded logo breaks one of the upload rules; the message is user facing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _decode_data_uri(value: str) -> bytes:
    match = _DATA_URI.match(value.strip()) if isinstance(value, str) else None
    if not match:
        raise LogoRejected("LOGO_FORMAT", "Please upload the logo as a PNG, JPG or WebP image.")
    try:
        return base64.b64decode(re.sub(r"\s", "", match.group(2)), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise LogoRejected("LOGO_UNREADABLE", "This image could not be read. Please choose another file.") from exc


def _png_uri(img) -> str:
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def prepare_uploaded_logo(value: str, max_bytes: int) -> str:
    """
    Check an uploaded logo (data URI) against the upload rules and return the
    copy to store: same picture, at most LOGO_STORE_MAX_PX on the long side,
    re-encoded (PNG, or JPEG for an opaque photo-like image when PNG would
    not fit), never larger than `max_bytes`. Raises LogoRejected with a user
    facing message for every rule.
    """
    from PIL import Image, ImageOps, UnidentifiedImageError

    raw = _decode_data_uri(value)
    if len(raw) > LOGO_UPLOAD_MAX_BYTES:
        raise LogoRejected("LOGO_TOO_LARGE", "The logo file is larger than 2 MB. Please choose a smaller file.")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format
            probe.load()
            img = ImageOps.exif_transpose(probe)
            img = img.convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise LogoRejected("LOGO_UNREADABLE", "This image could not be read. Please choose another file.") from exc
    if fmt not in LOGO_FORMATS:
        raise LogoRejected("LOGO_FORMAT", "Please upload the logo as a PNG, JPG or WebP image.")
    w, h = img.size
    if min(w, h) < LOGO_MIN_SHORT_SIDE_PX:
        raise LogoRejected(
            "LOGO_TOO_SMALL",
            f"The logo is {w} x {h} px. It needs at least {LOGO_MIN_SHORT_SIDE_PX} px on the shorter side.",
        )
    if max(w, h) / min(w, h) > LOGO_MAX_ASPECT:
        raise LogoRejected(
            "LOGO_ASPECT",
            "The logo is too long and thin. Width and height may differ by at most 4 times (1:4 to 4:1).",
        )
    img.thumbnail((LOGO_STORE_MAX_PX, LOGO_STORE_MAX_PX), Image.LANCZOS)
    side = LOGO_STORE_MAX_PX
    while True:
        stored = _png_uri(img)
        if data_uri_size(stored) <= max_bytes:
            return stored
        if img.getchannel("A").getextrema()[0] == 255:
            out = io.BytesIO()
            img.convert("RGB").save(out, format="JPEG", quality=88, optimize=True)
            if out.tell() <= max_bytes:
                return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")
        side = int(side * 0.8)
        if side < LOGO_MIN_SHORT_SIDE_PX:
            raise LogoRejected("LOGO_TOO_LARGE", "The logo could not be made small enough. Please choose a simpler image.")
        img.thumbnail((side, side), Image.LANCZOS)


def data_uri_size(value: str) -> int:
    payload = value.split(",", 1)[1] if "," in value else ""
    return (len(payload) * 3) // 4 - payload[-2:].count("=")


def render_logo_for_mode(stored: str, mode: str) -> str:
    """
    The letterhead copy of a stored logo for the clinic's background mode,
    made once at save time (BR-b). as_is and white keep the picture exactly
    as uploaded (white only adds a tile in the PDF); transparent removes the
    plain background with the trim + flood fill that used to run on every
    logo. Returns "" when the stored value is not a usable image.
    """
    from PIL import Image, ImageOps

    try:
        raw = _decode_data_uri(stored)
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            img = ImageOps.exif_transpose(img).convert("RGBA")
    except Exception as exc:  # LogoRejected, not an image, truncated
        logger.warning("Clinic logo skipped: %s", type(exc).__name__)
        return ""
    if mode == LOGO_BG_TRANSPARENT:
        img = _trim_background(img)
        if img.getchannel("A").getextrema()[0] >= 250:
            img = _clear_light_background(img)
    img.thumbnail((LOGO_MAX_PX, LOGO_MAX_PX), Image.LANCZOS)
    return _png_uri(img)


def logo_low_contrast_share(data_uri: str) -> float:
    """
    Share (0..1) of the logo's outline pixels whose WCAG contrast against the
    band is below 3:1. The outline is where the logo meets the band: visible
    pixels next to a transparent pixel or on the image edge. An opaque logo
    is judged by its own background (its edge); dark text on a transparent
    background by the text itself.
    """
    from PIL import Image

    try:
        raw = base64.b64decode(data_uri.split(",", 1)[1])
        with Image.open(io.BytesIO(raw)) as img:
            img = img.convert("RGBA")
            img.thumbnail((160, 160))
    except Exception:
        return 0.0
    w, h = img.size
    px = img.load()
    bands = [_luminance(_hex_rgb(c)) for c in (BAND_START, BAND_END)]

    def clear(x: int, y: int) -> bool:
        return x < 0 or y < 0 or x >= w or y >= h or px[x, y][3] < 128

    edge = low = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128 or not any(clear(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                continue
            edge += 1
            lum = _luminance((r, g, b))
            if min((max(lum, v) + 0.05) / (min(lum, v) + 0.05) for v in bands) < 3.0:
                low += 1
    return round(low / edge, 3) if edge else 1.0


LOGO_LOW_CONTRAST_SHARE = 0.25


def logo_needs_contrast_warning(data_uri: str, mode: str) -> bool:
    """Settings shows the low-contrast warning (BR-g); never for the white tile."""
    if mode == LOGO_BG_WHITE or not data_uri:
        return False
    return logo_low_contrast_share(data_uri) >= LOGO_LOW_CONTRAST_SHARE


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _luminance(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@dataclass
class ClinicBrand:
    """Everything the clinical letterhead shows. Plain text, escaped here."""

    name: str = ""
    logo_src: str = ""  # PNG data URI from render_logo_for_mode / resolve_clinic_logo
    logo_bg_mode: str = LOGO_BG_AS_IS
    doctor_name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""  # already formatted with format_address
    website: str = ""


# Geometry (mm). A4 = 210 x 297.
BAND_TOP_MM = 24.0
BAND_BOTTOM_MM = 10.0
BODY_GAP_TOP_MM = 6.0
CLINIC_LINE_MM = 4.0
REPORT_NO_LINE_MM = 4.5
FOOTER_MARK_MM = 3.4
CLINIC_BLOCK_PAD_MM = 3.0
SIDE_MM = 14.0
LOGO_BOX_W_MM = 36.0
LOGO_BOX_H_MM = 15.0
LOGO_TILE_PAD_MM = 1.6
AV_LOGO_MM = 12.0
WATERMARK_MM = 92.0


def clinic_block_lines(brand: ClinicBrand) -> list[str]:
    """Full name, address, website: only the ones that are set, no gaps."""
    return [v for v in (_filled(brand.name), _filled(brand.address), format_website(brand.website)) if v]


def clinical_page_margins_mm(brand: ClinicBrand) -> tuple[float, float]:
    """(top, bottom) @page margins for this clinic."""
    lines = len(clinic_block_lines(brand))
    block = REPORT_NO_LINE_MM + lines * CLINIC_LINE_MM + CLINIC_BLOCK_PAD_MM * 2
    return BAND_TOP_MM + BODY_GAP_TOP_MM, round(BAND_BOTTOM_MM + block, 1)


def _fit_box(data_uri: str, box_w: float, box_h: float) -> tuple[float, float]:
    size = _png_size(data_uri)
    if size is None:
        return box_h, box_h
    w, h = size
    scale = min(box_w / w, box_h / h)
    return round(w * scale, 2), round(h * scale, 2)


def clinical_page_css(brand: ClinicBrand, *, watermark: bool = True) -> str:
    """
    @page rules and the shared styles of the clinical letterhead, footer,
    patient box and tinted strips. The page body is white; the caller adds
    its own content styles after this.
    """
    from app.services.brand import watermark_data_uri

    top, bottom = clinical_page_margins_mm(brand)
    mark = watermark_data_uri() if watermark else ""
    mark_css = (
        f'background-image: url("{mark}"); background-repeat: no-repeat; '
        f"background-position: center 52%; background-size: {WATERMARK_MM}mm auto;"
        if mark
        else ""
    )
    band = f"linear-gradient(90deg, {BAND_START} 0%, {BAND_END} 100%)"
    return f"""
@page {{
  size: A4;
  margin: {top}mm 0 {bottom}mm 0;
  background-color: #ffffff;
  {mark_css}
  @top-center {{ content: element(clinicalBand); width: 100%; vertical-align: top; }}
  @bottom-center {{ content: element(clinicalFooter); width: 100%; vertical-align: bottom; }}
}}
body {{ font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: {INK};
  margin: 0; padding: 0 {SIDE_MM}mm; line-height: 1.45; font-size: 9.5pt; }}
.cl-band p, .cl-footer p, .patient-box p, .strip, .doc-title {{ margin: 0; }}
h1, h2, h3, .heading {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; }}

.cl-band {{ position: running(clinicalBand); width: 100%; height: {BAND_TOP_MM}mm; box-sizing: border-box;
  padding: {(BAND_TOP_MM - LOGO_BOX_H_MM) / 2}mm {SIDE_MM}mm 0 {SIDE_MM}mm; background: {band}; }}
.cl-band table {{ width: 100%; height: {LOGO_BOX_H_MM}mm; border-collapse: collapse; }}
.cl-band td {{ vertical-align: middle; padding: 0; }}
.cl-band p {{ margin: 0; }}
.cl-logo {{ width: {LOGO_BOX_W_MM}mm; height: {LOGO_BOX_H_MM}mm; text-align: left; }}
.cl-logo .box {{ width: {LOGO_BOX_W_MM}mm; height: {LOGO_BOX_H_MM}mm; line-height: {LOGO_BOX_H_MM}mm; }}
.cl-logo img {{ vertical-align: middle; }}
.cl-logo .tile {{ display: inline-block; background: #ffffff; border-radius: 2mm;
  padding: {LOGO_TILE_PAD_MM}mm; line-height: 0; vertical-align: middle; }}
.cl-who {{ padding-left: 4.5mm !important; }}
.cl-doctor {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 11.5pt;
  line-height: 1.2; color: #ffffff; }}
.cl-contact {{ font-size: 8pt; line-height: 1.45; color: {ON_DARK_STRONG}; margin-top: 0.8mm !important; }}
.cl-contact .sep {{ color: {ON_DARK}; margin: 0 1.6mm; }}
.cl-av {{ width: {AV_LOGO_MM}mm; text-align: right; }}
.cl-av img {{ width: {AV_LOGO_MM}mm; height: {AV_LOGO_MM}mm; display: block; }}

.cl-footer {{ position: running(clinicalFooter); width: 100%; }}
.cl-clinic {{ padding: {CLINIC_BLOCK_PAD_MM}mm {SIDE_MM}mm; background: #ffffff; }}
.cl-clinic p {{ margin: 0; font-size: 8pt; line-height: {CLINIC_LINE_MM}mm; color: {MUTED}; text-align: center; }}
.cl-clinic p.name {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 8.6pt;
  color: {INK}; }}
.cl-clinic p.reportno {{ text-align: left; font-size: 7.4pt; line-height: {REPORT_NO_LINE_MM}mm; color: {MUTED};
  letter-spacing: 0.2px; }}
.cl-clinic p.reportno b {{ font-weight: 600; }}
.cl-bottom {{ height: {BAND_BOTTOM_MM}mm; box-sizing: border-box; padding: {(BAND_BOTTOM_MM - 4) / 2}mm {SIDE_MM}mm 0 {SIDE_MM}mm;
  background: {band}; }}
.cl-bottom table {{ width: 100%; height: 4mm; border-collapse: collapse; }}
.cl-bottom td {{ vertical-align: middle; padding: 0; font-size: 7.2pt; color: {ON_DARK_STRONG};
  letter-spacing: 0.3px; white-space: nowrap; }}
.cl-bottom .powered img {{ width: {FOOTER_MARK_MM}mm; height: {FOOTER_MARK_MM}mm; vertical-align: middle;
  margin: 0 1.6mm 0.3mm 0; }}
.cl-bottom .powered b {{ color: #ffffff; font-weight: 700; }}
.cl-bottom .pages {{ text-align: right; }}
.cl-bottom .pages::after {{ content: "Page " counter(page) " of " counter(pages); }}

.patient-box {{ width: 100%; border-collapse: collapse; border: 0.3mm solid {RULE_STRONG};
  border-radius: 2.5mm; margin: 0 0 4mm 0; }}
.patient-box td {{ padding: 1.6mm 4mm; vertical-align: baseline; width: 50%; }}
.patient-box tr + tr td {{ border-top: 0.2mm solid {RULE_SOFT}; }}
.patient-box .k {{ display: inline-block; width: 30mm; font-size: 7.4pt; font-weight: 600; color: {MUTED}; }}
.patient-box .v {{ font-size: 9.5pt; font-weight: 600; color: {INK}; }}
.patient-box .v.name {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 10.5pt; }}

.strip {{ background: {BAND_TINT}; border-left: 0.8mm solid {BAND_END}; padding: 1.6mm 3mm;
  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 10.5pt; color: {INK};
  margin: 0 0 3mm 0; }}
.doc-title {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 14pt;
  color: {INK}; margin: 0 0 3mm 0; letter-spacing: 0.2px; }}
table.grid th {{ background: {BAND_TINT}; color: {INK}; font-weight: 600; font-size: 8pt; text-align: left; }}
"""


def clinical_band_html(brand: ClinicBrand) -> str:
    """Top band: clinic logo box + doctor / phone / email left, AV round logo right."""
    logo = ""
    if brand.logo_src:
        pad = LOGO_TILE_PAD_MM * 2 if brand.logo_bg_mode == LOGO_BG_WHITE else 0.0
        w, h = _fit_box(brand.logo_src, LOGO_BOX_W_MM - pad, LOGO_BOX_H_MM - pad)
        img = f'<img src="{brand.logo_src}" alt="" style="width: {w}mm; height: {h}mm" />'
        if brand.logo_bg_mode == LOGO_BG_WHITE:
            img = f'<span class="tile">{img}</span>'
        logo = f'<td class="cl-logo"><div class="box">{img}</div></td>'
    contacts = [html.escape(v) for v in (_filled(brand.phone), _filled(brand.email)) if v]
    contact_html = (
        '<p class="cl-contact">' + '<span class="sep">&middot;</span>'.join(contacts) + "</p>" if contacts else ""
    )
    doctor = _filled(brand.doctor_name)
    who = f'<p class="cl-doctor">{html.escape(doctor)}</p>' if doctor else ""
    av = brand_data_uri("av_logo_round.png")
    av_html = f'<td class="cl-av"><img src="{av}" alt="Aarogya Virohan" /></td>' if av else ""
    who_class = "cl-who" if logo else "cl-who first"
    return (
        f'<div class="cl-band"><table><tr>{logo}'
        f'<td class="{who_class}">{who}{contact_html}</td>{av_html}</tr></table></div>'
    )


def clinical_footer_html(brand: ClinicBrand, document_number: str) -> str:
    """
    Footer of every clinical page (Onkar 27 Nov 00:12): on white, the report
    number small and left, then the clinic block centred (name bold,
    address, website; only lines that are set); under it the teal band with
    the white AV mark + "Powered by" on the left and "Page x of y" right.
    """
    from app.services.brand import av_mark_white_data_uri

    lines = clinic_block_lines(brand)
    name = _filled(brand.name)
    block = "".join(
        f'<p class="{"name" if i == 0 and line == name else "line"}">{html.escape(line)}</p>'
        for i, line in enumerate(lines)
    )
    number = document_number.strip()
    report_no = f'<p class="reportno">Report No. <b>{html.escape(number)}</b></p>' if number else '<p class="reportno">&nbsp;</p>'
    mark = av_mark_white_data_uri()
    mark_html = f'<img src="{mark}" alt="" />' if mark else ""
    return f"""<div class="cl-footer"><div class="cl-clinic">{report_no}{block}</div>
<div class="cl-bottom"><table><tr>
  <td class="powered">{mark_html}Powered by <b>Aarogya Virohan</b> &middot; <b>AV Suite</b></td>
  <td class="pages"></td>
</tr></table></div></div>"""


@dataclass
class PatientBox:
    """BR-l: the same labels in the same order on Rx, posture and psychosocial."""

    name: str
    patient_id: str = ""
    age_sex: str = ""
    date: str = ""
    therapist: str = ""
    report_no: str = ""


def age_sex_text(age: int | None, sex: str | None) -> str:
    parts = [f"{age} Y" if isinstance(age, int) and age >= 0 else "", (sex or "").strip().capitalize()]
    return " / ".join(p for p in parts if p)


def patient_box_html(box: PatientBox) -> str:
    """Three rows, two columns. An empty value prints as an en dash, so the
    grid never shifts between reports."""

    def cell(label: str, value: str, extra: str = "") -> str:
        shown = html.escape(value.strip()) if value and value.strip() else "&ndash;"
        return f'<td><span class="k">{label}</span><span class="v{extra}">{shown}</span></td>'

    rows = (
        (cell("Patient name", box.name, " name"), cell("Patient ID", box.patient_id)),
        (cell("Age / Sex", box.age_sex), cell("Date", box.date)),
        (cell("Treating therapist", box.therapist), cell("Report No.", box.report_no)),
    )
    return '<table class="patient-box">' + "".join(f"<tr>{a}{b}</tr>" for a, b in rows) + "</table>"


async def letterhead_logo(
    stored: str | None,
    mode: str | None,
    rendered: str | None = None,
    fetch: Callable[[str], Awaitable[bytes | None]] | None = None,
) -> str:
    """
    The logo for the clinical letterhead. The copy made at save time
    (`clinics.branding_logo_render`) is used when there is one; a logo saved
    before Round 4 is processed here the same way, from the stored data URI,
    or downloaded with `fetch` when it is an https URL.
    """
    mode = mode if mode in LOGO_BG_MODES else LOGO_BG_AS_IS
    if rendered and rendered.startswith("data:image/png;base64,"):
        return rendered
    if not stored or not isinstance(stored, str):
        return ""
    value = stored.strip()
    if value.lower().startswith("data:"):
        if len(value) > LOGO_MAX_CHARS:
            return ""
        return render_logo_for_mode(value, mode)
    if value.lower().startswith("https://") and fetch is not None:
        try:
            raw = await fetch(value)
        except Exception as exc:  # network, timeout
            logger.warning("Clinic logo download failed: %s", type(exc).__name__)
            return ""
        if not raw or len(raw) > LOGO_MAX_BYTES:
            return ""
        return render_logo_for_mode("data:image/png;base64," + base64.b64encode(raw).decode("ascii"), mode)
    return ""
