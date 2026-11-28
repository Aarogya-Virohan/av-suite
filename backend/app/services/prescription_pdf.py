"""
Exercise prescription PDF: template, image embedding and rendering.

The look follows the posture report (app/services/posture/pdf_service.py):
same palette, fonts, letterhead band, cream page, watermark and "powered by"
footer. The brand helpers come from app/services/brand.py, shared with the
posture report, so both documents stay in step when the brand changes.

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

from app.services.brand import (
    BAND_END,
    BAND_TINT,
    INK,
    MUTED,
    RULE_SOFT,
    font_faces,
)
from app.services.report_letterhead import (
    ClinicBrand,
    PatientBox,
    age_sex_text,
    clinical_band_html,
    clinical_footer_html,
    clinical_page_css,
    format_address,
    letterhead_logo,
    patient_box_html,
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

# Stop-pain line closing every prescription (plan C5, EL-D-015). Founders can
# change the wording at any time; it lives only here.
SAFETY_NOTE = (
    "Stop and contact your physiotherapist if you feel sharp pain, dizziness, "
    "chest pain or numbness."
)
CAREGIVER_LABEL = "Caregiver-assisted"
SAFETY_RED = "#b03a2e"  # the safety line's rule, as before Round 4

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
    # EL-D-013 / EL-D-014: caregiver label and the side the therapist picked.
    rx_mode: str = "PATIENT"
    side: str | None = None


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
    # "ADP-000003"; empty = row left out. Label on the PDF is "Patient ID".
    patient_id: str | None = None
    # Raw clinics.branding_logo_url; resolved into clinic_logo_src at render.
    clinic_logo: str | None = None
    clinic_logo_src: str = ""
    # Clinic profile shown on the letterhead (D-036); empty fields are left out.
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    # Round 4 (BR-b, BR-h, BR-l, D-043).
    display_doctor_name: str | None = None
    logo_bg_mode: str = "as_is"
    clinic_logo_render: str | None = None
    document_number: str | None = None
    patient_age: int | None = None
    patient_sex: str | None = None


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
            bg = Image.new("RGB", img.size, (255, 255, 255))  # white page (Round 4)
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


def clinic_brand(doc: RxDoc) -> ClinicBrand:
    """The letterhead for this prescription (Round 4, BR-e..BR-i)."""
    return ClinicBrand(
        name=doc.clinic_name or "",
        logo_src=doc.clinic_logo_src,
        logo_bg_mode=doc.logo_bg_mode,
        doctor_name=doc.display_doctor_name or "",
        phone=doc.phone or "",
        email=doc.email or "",
        address=format_address(doc.address_line, doc.city, doc.state, doc.pincode),
        website=doc.website or "",
    )


def document_number(doc: RxDoc) -> str:
    """D-043 number stored on the row; the old reference for a row without one."""
    return doc.document_number or rx_reference(doc.rx_id)


def _patient_box(doc: RxDoc, on: date) -> str:
    age = doc.patient_age
    if doc.patient_dob:
        age = age_on(doc.patient_dob, on)
    return patient_box_html(
        PatientBox(
            name=doc.patient_name,
            patient_id=doc.patient_id or "",
            age_sex=age_sex_text(age, doc.patient_sex),
            date=display_date(on),
            therapist=doc.physio_name or "",
            report_no=document_number(doc),
        )
    )


def _photos_html(item: RxItem) -> str:
    photos = [p for p in item.photo_srcs if p][:2]
    if len(photos) == 2:
        return (
            '<table class="pair"><tr>'
            + "".join(f'<td><img src="{p}" alt="" /></td>' for p in photos)
            + "</tr></table>"
        )
    if photos:
        return f'<img src="{photos[0]}" alt="" />'
    if item.image_src:
        return f'<img src="{item.image_src}" alt="" />'
    return '<div class="noimg">Image not available</div>'


def _exercise_card(index: int, item: RxItem) -> str:
    """BR-j: picture on the left half, name, description and dose on the right."""
    hold = f"{item.hold}&nbsp;s" if item.hold else "&ndash;"
    note = (
        f'<p class="ex-note"><span>Therapist note</span>{_esc(item.note)}</p>'
        if item.note
        else ""
    )
    # Only the brief description prints (plan C3).
    instructions = f'<p class="ex-instr">{_esc(item.instructions)}</p>' if item.instructions else ""
    flags = ""
    if item.side in ("left", "right"):
        flags += f'<span class="ex-flag">{_esc(item.side.capitalize())} side</span>'
    if item.rx_mode == "CAREGIVER":
        flags += f'<span class="ex-flag">{_esc(CAREGIVER_LABEL)}</span>'
    part = f'<p class="ex-part">{_esc(item.body_part)}</p>' if item.body_part else ""
    return f"""
<table class="ex-card"><tr>
  <td class="ex-img"><div class="in">{_photos_html(item)}</div></td>
  <td class="ex-body"><div class="in">
    <p class="ex-title"><span class="ex-num">{index}.</span> {_esc(display_title(item.title))}</p>
    {part}
    {f'<p class="ex-flags">{flags}</p>' if flags else ""}
    {instructions}
    <table class="dose grid"><tr><th>Sets</th><th>Reps</th><th>Hold</th><th>Frequency</th></tr>
      <tr><td>{item.sets}</td><td>{item.reps}</td><td>{hold}</td><td>{_esc(item.frequency)}</td></tr></table>
    {note}
  </div></td>
</tr></table>
"""


# BR-j: exercises per page. 3 chosen (Onkar 26 Nov 23:42); 3 is
# only allowed while the picture stays at least 55 mm tall and the body text
# at least 9.5 pt. Card heights below are sized so the first page (which
# also carries the patient box) holds the same number as the pages after it.
EXERCISES_PER_PAGE = 3
_CARD_H_MM = {2: 94.0, 3: 59.0}
_CARD_GAP_MM = 4.0
_CARD_PAD_MM = 2.0


def card_image_height_mm(per_page: int) -> float:
    return _CARD_H_MM[per_page] - 2 * _CARD_PAD_MM


def build_prescription_html(doc: RxDoc, per_page: int | None = None) -> str:
    per_page = per_page or EXERCISES_PER_PAGE
    if per_page not in _CARD_H_MM:
        raise ValueError("per_page must be 2 or 3")
    on = ist_date(doc.prescribed_on)
    brand = clinic_brand(doc)
    cards = "".join(_exercise_card(i + 1, it) for i, it in enumerate(doc.items))
    card_h = _CARD_H_MM[per_page]
    img_h = card_image_height_mm(per_page)
    notes = (
        f'<div class="guidance"><p class="strip">Therapist guidance</p><p>{_esc(doc.physio_notes)}</p></div>'
        if doc.physio_notes
        else ""
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<title>{_esc(DOC_TITLE)} - {_esc(doc.patient_name)}</title>
<style>
{font_faces()}
{clinical_page_css(brand)}
p {{ margin: 0; }}
.ex-card {{ width: 100%; height: {card_h}mm; border-collapse: collapse; table-layout: fixed;
  border: 0.3mm solid {RULE_SOFT}; border-radius: 2.5mm; margin: 0;
  page-break-inside: avoid; }}
.ex-card + .ex-card {{ margin-top: {_CARD_GAP_MM}mm; }}
.ex-card td {{ vertical-align: top; padding: 0; }}
.ex-card td.ex-img, .ex-card td.ex-body {{ width: 50%; }}
.ex-img .in {{ height: {img_h}mm; padding: {_CARD_PAD_MM}mm; text-align: center; }}
.ex-body .in {{ padding: {_CARD_PAD_MM}mm {_CARD_PAD_MM}mm {_CARD_PAD_MM}mm 4mm; }}
.ex-img img {{ max-width: 100%; max-height: {img_h}mm; width: auto; height: auto; }}
.pair {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
.pair td {{ width: 50%; padding: 0 0.8mm; text-align: center; vertical-align: middle; }}
.noimg {{ height: {img_h}mm; line-height: {img_h}mm; color: {MUTED}; font-size: 8pt;
  border: 0.3mm dashed {RULE_SOFT}; border-radius: 2mm; }}
.ex-title {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 12pt;
  line-height: 1.25; color: {INK}; }}
.ex-num {{ color: {BAND_END}; }}
.ex-part {{ font-size: 8pt; font-weight: 600; color: {MUTED}; margin-top: 0.8mm !important; }}
.ex-flags {{ margin-top: 1.6mm !important; }}
.ex-flag {{ display: inline-block; font-size: 8pt; font-weight: 600; color: {INK}; background: {BAND_TINT};
  border: 0.2mm solid {RULE_SOFT}; border-radius: 1.4mm; padding: 0.4mm 1.8mm; margin-right: 1.4mm; }}
.ex-instr {{ font-size: 9.5pt; line-height: 1.45; margin-top: 2.4mm !important; }}
table.dose {{ width: 100%; border-collapse: collapse; margin-top: 3mm; }}
table.dose th, table.dose td {{ padding: 1.2mm 2mm; border: 0.2mm solid {RULE_SOFT}; text-align: left; }}
table.dose td {{ font-size: 10pt; font-weight: 700; }}
.ex-note {{ margin-top: 2.4mm !important; font-size: 9.5pt; }}
.ex-note span {{ display: block; font-size: 7.6pt; font-weight: 600; color: {MUTED}; }}
.closing {{ page-break-inside: avoid; margin-top: 5mm; }}
.guidance {{ margin-bottom: 4mm; }}
.safety {{ font-size: 9.5pt; border-left: 0.8mm solid {SAFETY_RED}; padding-left: 3mm; }}
</style></head>
<body>
{clinical_band_html(brand)}
{clinical_footer_html(brand, document_number(doc))}
<p class="doc-title">{_esc(DOC_TITLE)}</p>
{_patient_box(doc, on)}
{cards}
<div class="closing">
  {notes}
  <p class="strip">Safety</p>
  <p class="safety">{_esc(SAFETY_NOTE)}</p>
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
        letterhead_logo(doc.clinic_logo, doc.logo_bg_mode, doc.clinic_logo_render, fetch_logo),
    )
    doc.clinic_logo_src = logo
    for it in doc.items:
        it.image_src = images.get(it.image_url or "", "")
    html_content = build_prescription_html(doc)
    return await asyncio.to_thread(_render, html_content)
