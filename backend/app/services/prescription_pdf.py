"""
Exercise prescription PDF: template, image embedding and rendering.

The look follows the posture report (app/services/posture/pdf_service.py):
same palette, fonts, letterhead band, cream page, watermark and "powered by"
footer. The brand helpers are imported from there, not copied, so both
documents stay in step when the brand changes. Nothing in the posture module
is modified by this file.

Speed, 20 October 2026: the old template pointed <img> at the exercise's
remote image URL, so WeasyPrint downloaded every image one after another at
full size while blocking the event loop (about 18 s and 2.8 MB for a short
prescription). Images are now fetched here in parallel with a timeout,
shrunk with Pillow, cached in memory and embedded as data URIs, and the
render itself runs in a worker thread.
"""

from __future__ import annotations

import asyncio
import base64
import html
import io
import ipaddress
import logging
import socket
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

import httpx

from app.services.posture.pdf_service import (
    BRAND_DARK,
    GROVE,
    INK,
    MIDNIGHT,
    MUTED,
    PAGE,
    PAPER,
    POWERED_BY_COMPANY,
    POWERED_BY_PRODUCT,
    RULE,
    _brand_data_uri,
    _font_faces,
)
from app.services.report_letterhead import (
    letterhead_css,
    letterhead_html,
    resolve_clinic_logo,
)

try:
    from weasyprint import HTML
except (ImportError, OSError):  # pragma: no cover - native libs missing
    HTML = None

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
DOC_TITLE = "Home Exercise Programme"
# Founders' feedback 23 Oct 2026, item 4 (was "Physical Therapy & Rehabilitation").
LETTERHEAD_SUBTITLE = "Exercise Prescription Tool"

# Wording taken from the old browser print view (A4PrintView.tsx), not new.
SAFETY_NOTE = (
    "If you experience sharp pain during any exercise, stop immediately and "
    "contact your therapist."
)

# Image fetching limits.
IMAGE_TIMEOUT_S = 6.0
IMAGE_MAX_BYTES = 8 * 1024 * 1024
IMAGE_MAX_PX = 1400
IMAGE_CONCURRENCY = 6
IMAGE_CACHE_SIZE = 256
_MAX_REDIRECTS = 3

_image_cache: "OrderedDict[str, str]" = OrderedDict()


# --------------------------------------------------------------------------
# Data passed to the template
# --------------------------------------------------------------------------


@dataclass
class RxItem:
    title: str
    body_part: str
    instructions: str
    sets: int
    reps: int
    hold: int
    frequency: str
    note: str | None
    image_url: str | None
    image_src: str = ""
    # The clinic's own photos (front, side) as data URIs, EL-D-004. When
    # present they replace the library picture.
    exercise_id: str | None = None
    photo_srcs: list[str] = field(default_factory=list)


@dataclass
class RxDoc:
    rx_id: str
    clinic_name: str
    physio_name: str
    patient_name: str
    patient_phone: str | None
    patient_dob: date | None
    prescribed_on: datetime | None
    physio_notes: str | None
    items: list[RxItem] = field(default_factory=list)
    # Raw clinics.branding_logo_url; resolved into clinic_logo_src at render.
    clinic_logo: str | None = None
    clinic_logo_src: str = ""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def display_title(raw: str) -> str:
    """Same rule as the library (displayTitle.ts): titles show as written,
    except titles mostly in capitals ("CHIN TUCKS"), shown in sentence case."""
    title = " ".join((raw or "").split())
    letters = [c for c in title if c.isascii() and c.isalpha()]
    if not letters:
        return title
    upper = sum(1 for c in letters if c.isupper())
    text = title.lower() if upper / len(letters) >= 0.6 else title
    return text[:1].upper() + text[1:]


def _esc(value: object) -> str:
    return html.escape(str(value)) if value not in (None, "") else ""


def ist_date(value: datetime | None) -> date:
    """Calendar date in India. A naive datetime is taken as UTC."""
    if value is None:
        return datetime.now(IST).date()
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(IST).date()


def display_date(d: date) -> str:
    return d.strftime("%d %b %Y").lstrip("0")


def age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def rx_reference(rx_id: str) -> str:
    return "RX-" + rx_id.replace("-", "")[:8].upper()


def pdf_filename(patient_name: str, on: date) -> str:
    """Download name, e.g. Rx_PriyaSharma_20Oct2026.pdf (ASCII only)."""
    safe = "".join(ch for ch in patient_name.title() if ch.isascii() and ch.isalnum())
    return f"Rx_{safe or 'Patient'}_{on.strftime('%d%b%Y')}.pdf"


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------


def _is_public_host(host: str) -> bool:
    """False for loopback, private, link-local and similar addresses, so an
    exercise image URL can never make the server call into its own network."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            return False
    return bool(infos)


def _shrink_to_data_uri(raw: bytes) -> str:
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(raw)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 253, 247))  # PAPER
            bg.paste(img, mask=img.getchannel("A"))
            img = bg
        else:
            img = img.convert("RGB")
        img.thumbnail((IMAGE_MAX_PX, IMAGE_MAX_PX))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=80, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")


async def _download(client: httpx.AsyncClient, url: str) -> bytes | None:
    for _ in range(_MAX_REDIRECTS + 1):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            return None
        if not await asyncio.to_thread(_is_public_host, parts.hostname):
            return None
        async with client.stream("GET", url) as resp:
            if resp.is_redirect and "location" in resp.headers:
                url = urljoin(url, resp.headers["location"])
                continue
            if resp.status_code != 200:
                return None
            chunks, size = [], 0
            async for chunk in resp.aiter_bytes():
                size += len(chunk)
                if size > IMAGE_MAX_BYTES:
                    return None
                chunks.append(chunk)
            return b"".join(chunks)
    return None


async def _fetch_one(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> str:
    cached = _image_cache.get(url)
    if cached is not None:
        _image_cache.move_to_end(url)
        return cached
    async with sem:
        try:
            raw = await asyncio.wait_for(_download(client, url), IMAGE_TIMEOUT_S)
            if not raw:
                return ""
            data_uri = await asyncio.to_thread(_shrink_to_data_uri, raw)
        except Exception as exc:  # timeout, network, unreadable image
            logger.warning("Prescription image skipped: %s", type(exc).__name__)
            return ""
    _image_cache[url] = data_uri
    while len(_image_cache) > IMAGE_CACHE_SIZE:
        _image_cache.popitem(last=False)
    return data_uri


async def embed_images(
    urls: list[str], transport: httpx.AsyncBaseTransport | None = None
) -> dict[str, str]:
    """Fetch every distinct URL in parallel. Failed ones map to "".
    `transport` is for tests only."""
    unique = list(dict.fromkeys(u for u in urls if u))
    if not unique:
        return {}
    sem = asyncio.Semaphore(IMAGE_CONCURRENCY)
    timeout = httpx.Timeout(IMAGE_TIMEOUT_S, connect=4.0)
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, transport=transport
    ) as client:
        results = await asyncio.gather(*(_fetch_one(client, sem, u) for u in unique))
    return dict(zip(unique, results))


# --------------------------------------------------------------------------
# Template
# --------------------------------------------------------------------------


def _letterhead(doc: RxDoc) -> str:
    return letterhead_html(
        _esc(LETTERHEAD_SUBTITLE), _esc(doc.clinic_name), doc.clinic_logo_src
    )


def _patient_box(doc: RxDoc, on: date) -> str:
    age = ""
    if doc.patient_dob:
        age = f"{age_on(doc.patient_dob, on)} Y"
    left = [
        ("Patient name", f'<span class="pname">{_esc(doc.patient_name)}</span>'),
        ("Age", age),
        ("Phone", _esc(doc.patient_phone)),
    ]
    right = [
        ("Prescription", f'<span class="nowrap">{_esc(rx_reference(doc.rx_id))}</span>'),
        ("Prescribed on", display_date(on)),
        ("Exercises", str(len(doc.items))),
    ]

    def half(rows: list[tuple[str, str]]) -> str:
        body = "".join(
            f'<tr><td class="pb-label">{label}</td><td class="pb-value">{value}</td></tr>'
            for label, value in rows
            if value
        )
        return f'<table class="pb-half">{body}</table>'

    return f"""
<table class="patient-box"><tr>
  <td class="pb-col">{half(left)}</td>
  <td class="pb-divider"></td>
  <td class="pb-col">{half(right)}</td>
</tr></table>
<div class="doc-title"><p class="t">{DOC_TITLE.upper()}</p></div>
"""


def _exercise_card(index: int, item: RxItem) -> str:
    photos = [p for p in item.photo_srcs if p][:2]
    if len(photos) == 2:
        image = (
            '<table class="pair"><tr>'
            + "".join(f'<td><img class="photo" src="{p}" alt="" /></td>' for p in photos)
            + "</tr></table>"
        )
    elif photos:
        image = f'<img class="photo" src="{photos[0]}" alt="" />'
    elif item.image_src:
        image = f'<img src="{item.image_src}" alt="" />'
    else:
        image = '<div class="noimg">Image not available</div>'
    img_class = "ex-img two" if len(photos) == 2 else "ex-img"
    hold = f"{item.hold}&nbsp;s" if item.hold else "&ndash;"
    note = (
        f'<p class="ex-note"><span>Therapist note</span>{_esc(item.note)}</p>'
        if item.note
        else ""
    )
    instructions = (
        f'<p class="ex-instr">{_esc(item.instructions)}</p>' if item.instructions else ""
    )
    return f"""
<div class="ex-card">
  <p class="ex-head"><span class="ex-num">{index}</span>
    <span class="ex-title">{_esc(display_title(item.title))}</span>
    <span class="ex-part">{_esc(item.body_part)}</span></p>
  <div class="{img_class}">{image}</div>
  <table class="ex"><tr>
  <td class="ex-body">
    <table class="dose"><tr>
      <td><span class="k">Sets</span><span class="v">{item.sets}</span></td>
      <td><span class="k">Reps</span><span class="v">{item.reps}</span></td>
      <td><span class="k">Hold</span><span class="v">{hold}</span></td>
      <td class="freq"><span class="k">Frequency</span><span class="v">{_esc(item.frequency)}</span></td>
    </tr></table>
    {instructions}
    {note}
  </td>
</tr></table></div>
"""


def build_prescription_html(doc: RxDoc) -> str:
    on = ist_date(doc.prescribed_on)
    cards = "".join(_exercise_card(i + 1, it) for i, it in enumerate(doc.items))

    mark = _brand_data_uri("av_mark.png")
    footer_mark = f'<img class="mark" src="{mark}" alt="" />' if mark else ""
    watermark = _brand_data_uri("av_watermark.png")
    watermark_css = (
        f'background-image: url("{watermark}"); background-repeat: no-repeat; '
        "background-position: center 55%; background-size: 95mm auto;"
        if watermark
        else ""
    )
    footer_who = " &nbsp;&middot;&nbsp; ".join(
        v for v in (_esc(doc.patient_name), _esc(rx_reference(doc.rx_id))) if v
    )
    notes = (
        f'<div class="guidance"><p class="tag">Therapist guidance</p><p>{_esc(doc.physio_notes)}</p></div>'
        if doc.physio_notes
        else ""
    )

    # Founders' feedback items 8 and 13: clinics have no digital signature, so
    # no signature or date lines; the treating therapist is named instead and
    # the date stays in the patient box at the top.
    therapist = (
        f'<p class="therapist"><span class="k">Treating therapist</span>'
        f'<span class="v">{_esc(doc.physio_name)}</span></p>'
        if doc.physio_name
        else ""
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<title>{_esc(DOC_TITLE)} - {_esc(doc.patient_name)}</title>
<style>
{_font_faces()}
@page {{
  size: A4;
  margin: 27mm 0 20mm 0;
  background-color: {PAGE};
  {watermark_css}
  @top-center {{ content: element(letterhead); width: 100%; vertical-align: top; }}
  @bottom-center {{ content: element(runningFooter); width: 100%; vertical-align: top; }}
}}
body {{ font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: {INK};
  margin: 0; padding: 0 14mm; line-height: 1.45; font-size: 9.3pt; }}
p {{ margin: 0; }}

{letterhead_css()}
.running-footer {{ position: running(runningFooter); width: 100%; padding: 0 14mm; text-align: center; }}
.running-footer .inner {{ border-top: 1px solid {RULE}; padding-top: 2.4mm; }}
.running-footer .powered {{ font-size: 7pt; letter-spacing: 0.9px; color: {MUTED}; }}
.running-footer .powered .by {{ font-weight: 700; }}
.running-footer .powered .company {{ font-weight: 700; color: {MIDNIGHT}; }}
.running-footer .powered .dot {{ color: {GROVE}; margin: 0 3px; }}
.running-footer .powered .product {{ font-weight: 700; color: {GROVE}; }}
.running-footer .powered .mark {{ height: 3.6mm; width: auto; vertical-align: -0.9mm; margin-right: 1.6mm; }}
.running-footer .meta {{ margin-top: 1.2mm; font-size: 6.8pt; color: {MUTED}; }}
.running-footer .meta .page::after {{ content: "Page " counter(page) " of " counter(pages); }}

.patient-box {{ width: 100%; border-collapse: separate; border: 1.3px solid #d9d1bf;
  border-radius: 4mm; background: {PAPER}; margin: 0 0 3.4mm 0; }}
.patient-box .pb-col {{ width: 50%; vertical-align: top; padding: 2.6mm 5mm; }}
.patient-box .pb-divider {{ width: 0.3mm; background: {RULE}; padding: 0; }}
.pb-half {{ border-collapse: collapse; width: 100%; }}
.pb-half td {{ padding: 0.7mm 0; vertical-align: baseline; }}
.pb-label {{ width: 27mm; font-size: 6.6pt; font-weight: 700; letter-spacing: 0.9px;
  text-transform: uppercase; color: {MUTED}; white-space: nowrap; }}
.pb-value {{ font-size: 9pt; font-weight: 600; color: {INK}; }}
.pb-value .pname {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 10.5pt; }}
.nowrap {{ white-space: nowrap; }}
.doc-title {{ text-align: center; margin: 0 0 3.6mm 0; }}
.doc-title .t {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800;
  font-size: 12.5pt; letter-spacing: 2.2px; color: {MIDNIGHT}; }}

.ex-card {{ background: {PAPER}; border: 1px solid {RULE}; border-radius: 3.5mm;
  padding: 3mm; margin: 0 0 3mm 0; page-break-inside: avoid; }}
.ex {{ width: 100%; border-collapse: collapse; }}
.ex td {{ vertical-align: top; padding: 0; }}
.ex-img {{ margin: 0 0 2.5mm 0; text-align: center; background: #fff;
  border-radius: 2.5mm; border: 1px solid {RULE}; padding: 1mm; }}
.ex-img img {{ max-width: 100%; max-height: 60mm; width: auto; height: auto; display: inline-block; }}
.noimg {{ height: 14mm; border-radius: 2.5mm; border: 1px dashed {RULE};
  color: {MUTED}; font-size: 7pt; text-align: center; line-height: 14mm; }}
.ex-img.two {{ padding: 1mm; }}
.pair {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
.pair td {{ width: 50%; padding: 0 !important; vertical-align: top; text-align: center; }}
.pair td + td {{ padding-left: 2mm !important; }}
.ex-img .pair img {{ max-width: 100%; max-height: 60mm; }}
.ex-head {{ margin-bottom: 2mm; }}
.ex-num {{ display: inline-block; width: 5.6mm; height: 5.6mm; line-height: 5.6mm; border-radius: 50%;
  background: {MIDNIGHT}; color: #fff; text-align: center; font-weight: 700; font-size: 7.6pt;
  margin-right: 2mm; vertical-align: 0.3mm; }}
.ex-title {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 11pt;
  color: {MIDNIGHT}; }}
.ex-part {{ font-size: 6.6pt; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;
  color: {GROVE}; background: #e3f3ea; border-radius: 1.6mm; padding: 0.5mm 1.8mm; margin-left: 2mm;
  vertical-align: 0.5mm; }}
.dose {{ border-collapse: separate; border-spacing: 1.6mm 0; margin: 0 -1.6mm 2mm -1.6mm; }}
.dose td {{ background: #fff; border: 1px solid {RULE}; border-radius: 2mm; padding: 1.2mm 3mm;
  min-width: 13mm; }}
.dose .freq {{ min-width: 26mm; }}
.dose .k {{ display: block; font-size: 6.2pt; font-weight: 700; letter-spacing: 0.8px;
  text-transform: uppercase; color: {MUTED}; }}
.dose .v {{ display: block; font-weight: 700; font-size: 10pt; color: {INK}; }}
.ex-instr {{ font-size: 8.8pt; color: {INK}; }}
.ex-note {{ margin-top: 1.6mm; font-size: 8.4pt; color: {INK}; border-left: 0.7mm solid {GROVE};
  padding-left: 2.4mm; }}
.ex-note span {{ display: block; font-size: 6.2pt; font-weight: 700; letter-spacing: 0.8px;
  text-transform: uppercase; color: {BRAND_DARK}; }}

.closing {{ page-break-inside: avoid; margin-top: 5mm; }}
.guidance {{ background: {PAPER}; border: 1px solid {RULE}; border-radius: 3.5mm; padding: 3mm 4mm; margin-bottom: 4mm; }}
.tag {{ font-size: 6.6pt; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
  color: {MUTED}; margin-bottom: 1mm !important; }}
.safety {{ font-size: 8.4pt; color: {INK}; border-left: 0.7mm solid #b03a2e; padding-left: 2.4mm; margin-bottom: 5mm; }}
.therapist {{ font-size: 9pt; color: {INK}; }}
.therapist .k {{ font-size: 6.6pt; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
  color: {MUTED}; margin-right: 2mm; }}
.therapist .v {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; }}
</style></head>
<body>
{_letterhead(doc)}
<div class="running-footer"><div class="inner">
  <p class="powered">{footer_mark}<span class="by">POWERED BY</span>
    <span class="company">{POWERED_BY_COMPANY}</span><span class="dot">&bull;</span><span class="product">{POWERED_BY_PRODUCT}</span></p>
  <p class="meta"><span class="who">{footer_who}</span>&nbsp;&nbsp;&middot;&nbsp;&nbsp;<span class="page"></span></p>
</div></div>

{_patient_box(doc, on)}
{cards}

<div class="closing">
  {notes}
  <p class="tag">Safety</p>
  <p class="safety">{_esc(SAFETY_NOTE)}</p>
  {therapist}
</div>
</body></html>
"""


def _render(html_content: str) -> bytes:
    if HTML is None:
        raise RuntimeError(
            "PDF generation requires WeasyPrint and its native libraries."
        )
    return HTML(string=html_content).write_pdf()


async def fetch_logo(
    url: str, transport: httpx.AsyncBaseTransport | None = None
) -> bytes | None:
    """Download a remote clinic logo with the same rules as exercise images:
    https only, public hosts only, size cap, timeout. `transport` is for tests."""
    timeout = httpx.Timeout(IMAGE_TIMEOUT_S, connect=4.0)
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, transport=transport
    ) as client:
        return await asyncio.wait_for(_download(client, url), IMAGE_TIMEOUT_S)


async def render_prescription_pdf(doc: RxDoc) -> bytes:
    """Embed images and the clinic logo, build the HTML and render it off the
    event loop."""
    images, logo = await asyncio.gather(
        # Items with the clinic's own photos do not need the library picture.
        embed_images([it.image_url for it in doc.items if it.image_url and not it.photo_srcs]),
        resolve_clinic_logo(doc.clinic_logo, fetch_logo),
    )
    doc.clinic_logo_src = logo
    for it in doc.items:
        it.image_src = images.get(it.image_url or "", "")
    html_content = build_prescription_html(doc)
    return await asyncio.to_thread(_render, html_content)
