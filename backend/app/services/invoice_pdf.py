"""
Invoice and payment receipt PDF (Decisions.md L-41, D-027).

Before this file the invoice "PDF" was five lines of text starting with
"%PDF", which no reader could open. The document now has the same content
the CRM prints from InvoicePreviewModal: clinic profile, patient, line items,
discount and tax with their percent, total, paid, balance, and for a receipt
the list of payments. Every value comes from the invoice, its payments, the
patient or the clinic profile; empty fields are left out and nothing is made
up (D-008, D-018). Clinics have no digital signature, so there is no
signature line (C-19).

The look is the exercise prescription PDF: shared letterhead
(app/services/report_letterhead.py), brand fonts, footer. Amounts use "Rs."
because the embedded fonts are a Latin subset without the rupee sign, and
the server may have no font that has it.
"""

from __future__ import annotations

import asyncio
import html
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from app.services.posture.pdf_service import (
    GROVE,
    INK,
    MIDNIGHT,
    MUTED,
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

IST = ZoneInfo("Asia/Kolkata")
DocKind = Literal["invoice", "receipt"]

LETTERHEAD_SUBTITLE = {"invoice": "Invoice", "receipt": "Payment Receipt"}

METHOD_LABEL = {
    "cash": "Cash",
    "upi": "UPI",
    "card": "Card",
    "bank_transfer": "Bank transfer",
    "insurance": "Insurance",
    "other": "Other",
}


@dataclass
class InvoiceLine:
    description: str
    quantity: int | str
    unit_price: Decimal | str | None
    total_price: Decimal | str | None


@dataclass
class ReceiptPayment:
    paid_on: datetime | None
    method: str
    reference: str | None
    amount: Decimal | str | None
    status: str = "completed"


@dataclass
class InvoiceDoc:
    kind: DocKind
    invoice_number: str
    status: str
    issue_date: datetime | None
    due_date: datetime | None
    clinic_name: str
    patient_name: str
    patient_phone: str | None = None
    clinic_logo: str | None = None
    clinic_logo_src: str = ""
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    phone: str | None = None
    email: str | None = None
    registration_number: str | None = None
    gstin: str | None = None
    authorised_person: str | None = None
    subtotal: Decimal | str | None = None
    discount_amount: Decimal | str | None = None
    discount_percent: Decimal | str | None = None
    tax_amount: Decimal | str | None = None
    tax_percent: Decimal | str | None = None
    total_amount: Decimal | str | None = None
    paid_amount: Decimal | str | None = None
    notes: str | None = None
    items: list[InvoiceLine] = field(default_factory=list)
    payments: list[ReceiptPayment] = field(default_factory=list)


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------


def _esc(value: object) -> str:
    return html.escape(str(value)) if value not in (None, "") else ""


def _filled(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _dec(value: Decimal | str | int | float | None) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def money(value: Decimal | str | int | float | None) -> str:
    """Rs. 1,23,456.50 (Indian grouping, two decimals)."""
    amount = _dec(value).quantize(Decimal("0.01"))
    sign = "-" if amount < 0 else ""
    whole, frac = f"{abs(amount):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"Rs. {sign}{whole}.{frac}"


def percent_text(value: Decimal | str | None) -> str | None:
    if value in (None, ""):
        return None
    try:
        n = Decimal(str(value))
    except Exception:
        return None
    text = format(n.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text}%"


def ist_date(value: datetime | date | None) -> date | None:
    """Calendar date in India. A naive datetime is taken as UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return value.astimezone(IST).date()
    return value


def display_date(value: datetime | date | None) -> str:
    d = ist_date(value)
    return d.strftime("%d %b %Y").lstrip("0") if d else ""


def pdf_filename(kind: DocKind, invoice_number: str) -> str:
    """Invoice-INV-0001.pdf / Receipt-INV-0001.pdf (ASCII, safe for headers)."""
    safe = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "-_") else "-" for ch in invoice_number)
    safe = safe.strip("-") or "invoice"
    return f"{'Receipt' if kind == 'receipt' else 'Invoice'}-{safe}.pdf"


# --------------------------------------------------------------------------
# Template
# --------------------------------------------------------------------------


def _clinic_block(doc: InvoiceDoc) -> str:
    place = ", ".join(v for v in (_filled(doc.city), _filled(doc.state)) if v)
    place_pin = " ".join(v for v in (place, _filled(doc.pincode)) if v)
    address = ", ".join(v for v in (_filled(doc.address_line), place_pin) if v)
    contacts = " &middot; ".join(_esc(v) for v in (_filled(doc.phone), _filled(doc.email)) if v)
    ids = " &middot; ".join(
        v
        for v in (
            f"Reg. No. {_esc(doc.registration_number)}" if _filled(doc.registration_number) else "",
            f"GSTIN {_esc(doc.gstin)}" if _filled(doc.gstin) else "",
        )
        if v
    )
    lines = [f'<p class="c-name">{_esc(doc.clinic_name)}</p>']
    if address:
        lines.append(f'<p class="c-line">{_esc(address)}</p>')
    if contacts:
        lines.append(f'<p class="c-line">{contacts}</p>')
    if ids:
        lines.append(f'<p class="c-line">{ids}</p>')
    return "".join(lines)


def _meta_rows(doc: InvoiceDoc) -> str:
    rows = [("Ref", _esc(doc.invoice_number)), ("Date", _esc(display_date(doc.issue_date)))]
    # A due date means nothing on a receipt for money already received.
    if doc.due_date and doc.kind == "invoice":
        rows.append(("Due", _esc(display_date(doc.due_date))))
    rows.append(("Status", f'<span class="status">{_esc(str(doc.status).replace("_", " "))}</span>'))
    return "".join(f'<tr><td class="k">{k}</td><td class="v">{v}</td></tr>' for k, v in rows if v)


def _items_table(doc: InvoiceDoc) -> str:
    if doc.items:
        body = "".join(
            f"<tr><td>{_esc(it.description)}</td><td class='num'>{_esc(it.quantity)}</td>"
            f"<td class='num'>{money(it.unit_price)}</td><td class='num'>{money(it.total_price)}</td></tr>"
            for it in doc.items
        )
    else:
        body = '<tr><td colspan="4" class="empty">No line items recorded on this invoice.</td></tr>'

    totals = [("Subtotal", money(doc.subtotal), "")]
    if _dec(doc.discount_amount) > 0:
        pct = percent_text(doc.discount_percent)
        totals.append((f"Discount{f' ({pct})' if pct else ''}", f"- {money(doc.discount_amount)}", ""))
    if _dec(doc.tax_amount) > 0:
        pct = percent_text(doc.tax_percent)
        totals.append((f"Tax{f' ({pct})' if pct else ''}", money(doc.tax_amount), ""))
    totals.append(("Total", money(doc.total_amount), "grand"))
    if doc.kind == "receipt" or _dec(doc.paid_amount) > 0:
        totals.append(("Paid", money(doc.paid_amount), ""))
        balance = _dec(doc.total_amount) - _dec(doc.paid_amount)
        if balance > 0:
            totals.append(("Balance due", money(balance), "due"))
    foot = "".join(
        f'<tr class="t {cls}"><td colspan="3" class="lbl">{_esc(label)}</td><td class="num">{_esc(val)}</td></tr>'
        for label, val, cls in totals
    )
    return f"""
<table class="items">
  <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Rate</th><th class="num">Amount</th></tr></thead>
  <tbody>{body}</tbody>
  <tbody class="totals">{foot}</tbody>
</table>"""


def _payments_table(doc: InvoiceDoc) -> str:
    if doc.kind != "receipt":
        return ""
    if not doc.payments:
        return '<div class="block"><p class="tag">Payments received</p><p class="muted">No payments recorded against this invoice.</p></div>'
    rows = []
    for p in sorted(doc.payments, key=lambda p: (ist_date(p.paid_on) or date.min)):
        mode = METHOD_LABEL.get(str(p.method), str(p.method))
        if p.status and p.status != "completed":
            mode = f"{mode} ({p.status})"
        rows.append(
            f"<tr><td>{_esc(display_date(p.paid_on))}</td><td>{_esc(mode)}</td>"
            f"<td>{_esc(p.reference) or '-'}</td><td class='num'>{money(p.amount)}</td></tr>"
        )
    return f"""
<div class="block"><p class="tag">Payments received</p>
<table class="items pay">
  <thead><tr><th>Date</th><th>Mode</th><th>Reference</th><th class="num">Amount</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table></div>"""


def build_invoice_html(doc: InvoiceDoc) -> str:
    title = "Payment Receipt" if doc.kind == "receipt" else "Invoice"
    word = "receipt" if doc.kind == "receipt" else "invoice"
    mark = _brand_data_uri("av_mark.png")
    footer_mark = f'<img class="mark" src="{mark}" alt="" />' if mark else ""
    phone = f'<p class="p-line">{_esc(doc.patient_phone)}</p>' if _filled(doc.patient_phone) else ""
    notes = (
        f'<div class="block"><p class="tag">Notes</p><p>{_esc(doc.notes)}</p></div>'
        if _filled(doc.notes)
        else ""
    )
    authorised = (
        f"<p>Authorised by {_esc(doc.authorised_person)}</p>" if _filled(doc.authorised_person) else ""
    )
    letterhead = letterhead_html(
        _esc(LETTERHEAD_SUBTITLE[doc.kind]), _esc(doc.clinic_name), doc.clinic_logo_src
    )
    footer_who = " &nbsp;&middot;&nbsp; ".join(
        v for v in (_esc(doc.clinic_name), _esc(doc.invoice_number)) if v
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<title>{_esc(title)} {_esc(doc.invoice_number)}</title>
<style>
{_font_faces()}
@page {{
  size: A4;
  margin: 27mm 0 20mm 0;
  background-color: #ffffff;
  @top-center {{ content: element(letterhead); width: 100%; vertical-align: top; }}
  @bottom-center {{ content: element(runningFooter); width: 100%; vertical-align: top; }}
}}
body {{ font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: {INK};
  margin: 0; padding: 0 14mm; line-height: 1.45; font-size: 9pt; }}
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

.head {{ width: 100%; border-collapse: collapse; margin-bottom: 5mm; }}
.head td {{ vertical-align: top; padding: 0; }}
.c-name {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 13pt; color: {MIDNIGHT}; }}
.c-line {{ font-size: 8.4pt; color: {MUTED}; margin-top: 0.8mm !important; }}
.doc {{ text-align: right; width: 42%; }}
.doc .t {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 15pt;
  letter-spacing: 1.6px; text-transform: uppercase; color: {MIDNIGHT}; }}
.meta-t {{ margin: 1.6mm 0 0 auto; border-collapse: collapse; }}
.meta-t td {{ padding: 0.5mm 0; font-size: 8.6pt; }}
.meta-t .k {{ color: {MUTED}; padding-right: 3mm; text-align: right; }}
.meta-t .v {{ font-weight: 600; text-align: right; }}
.status {{ text-transform: capitalize; }}
.bill {{ background: {PAPER}; border: 1px solid {RULE}; border-radius: 3mm; padding: 3mm 4mm; margin-bottom: 5mm; }}
.tag {{ font-size: 6.6pt; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
  color: {MUTED}; margin-bottom: 1.2mm !important; }}
.p-name {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 10.5pt; }}
.p-line {{ font-size: 8.6pt; color: {MUTED}; }}
.items {{ width: 100%; border-collapse: collapse; }}
.items th {{ text-align: left; font-size: 7pt; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;
  color: {MUTED}; border-bottom: 1.2px solid {MIDNIGHT}; padding: 1.6mm 2mm; }}
.items td {{ padding: 2mm; border-bottom: 1px solid {RULE}; vertical-align: top; }}
.items .num {{ text-align: right; white-space: nowrap; }}
.items .empty {{ color: {MUTED}; text-align: center; }}
.items tr {{ page-break-inside: avoid; }}
.totals td {{ border-bottom: none; padding: 1.2mm 2mm; }}
.totals .lbl {{ text-align: right; color: {MUTED}; }}
.totals tr.grand td {{ border-top: 1.2px solid {MIDNIGHT}; font-weight: 700; color: {MIDNIGHT}; font-size: 10pt; padding-top: 2mm; }}
.totals tr.grand .lbl {{ color: {MIDNIGHT}; }}
.totals tr.due td {{ font-weight: 700; color: #b03a2e; }}
.block {{ margin-top: 6mm; page-break-inside: avoid; }}
.muted {{ color: {MUTED}; }}
.closing {{ margin-top: 8mm; border-top: 1px solid {RULE}; padding-top: 3mm; font-size: 8pt; color: {MUTED};
  page-break-inside: avoid; }}
.closing .right {{ text-align: right; margin-top: 1.5mm; color: {INK}; }}
</style></head>
<body>
{letterhead}
<div class="running-footer"><div class="inner">
  <p class="powered">{footer_mark}<span class="by">POWERED BY</span>
    <span class="company">{POWERED_BY_COMPANY}</span><span class="dot">&bull;</span><span class="product">{POWERED_BY_PRODUCT}</span></p>
  <p class="meta"><span class="who">{footer_who}</span>&nbsp;&nbsp;&middot;&nbsp;&nbsp;<span class="page"></span></p>
</div></div>

<table class="head"><tr>
  <td>{_clinic_block(doc)}</td>
  <td class="doc"><p class="t">{_esc(title)}</p><table class="meta-t">{_meta_rows(doc)}</table></td>
</tr></table>

<div class="bill"><p class="tag">Billed to</p><p class="p-name">{_esc(doc.patient_name)}</p>{phone}</div>

{_items_table(doc)}
{_payments_table(doc)}
{notes}

<div class="closing">
  <p>This is a computer-generated {word} and does not need a signature.</p>
  <div class="right">{authorised}<p>Thank you for visiting {_esc(doc.clinic_name)}.</p></div>
</div>
</body></html>
"""


def _render(html_content: str) -> bytes:
    if HTML is None:
        raise RuntimeError("PDF generation requires WeasyPrint and its native libraries.")
    return HTML(string=html_content).write_pdf()


async def render_invoice_pdf(doc: InvoiceDoc) -> bytes:
    """Resolve the clinic logo, build the HTML and render it off the event loop."""
    from app.services.prescription_pdf import fetch_logo

    doc.clinic_logo_src = await resolve_clinic_logo(doc.clinic_logo, fetch_logo)
    return await asyncio.to_thread(_render, build_invoice_html(doc))
