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

Round 4 (26 Nov 2026, BR-m): plain black and white, no band, no watermark,
no tint; one receipt per payment (D-043). Amounts use "Rs."
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

from app.services.brand import font_faces
from app.services.report_letterhead import (
    LOGO_BG_AS_IS,
    format_address,
    letterhead_logo,
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
    receipt_number: str | None = None  # D-043, RCP-<FY>-<6 digits>


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
    # "ADP-000003"; empty = line left out. Label on the PDF is "Patient ID".
    patient_id: str | None = None
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
    website: str | None = None
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
    # The payment a receipt is for; None = the latest completed payment.
    payment: ReceiptPayment | None = None


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
# Amount in words, Indian system (lakh, crore)
# --------------------------------------------------------------------------
_ONES = (
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
)
_TENS = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety")


def _below_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _below_thousand(n: int) -> str:
    hundred, rest = divmod(n, 100)
    parts = []
    if hundred:
        parts.append(f"{_ONES[hundred]} Hundred")
    if rest:
        parts.append(_below_hundred(rest))
    return " ".join(parts)


def _indian_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    if crore:
        parts.append(f"{_indian_words(crore)} Crore")
    if lakh:
        parts.append(f"{_below_hundred(lakh)} Lakh")
    if thousand:
        parts.append(f"{_below_hundred(thousand)} Thousand")
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def amount_in_words(value: Decimal | str | int | float | None) -> str:
    """'Rupees Two Thousand Five Hundred and Fifty Paise Only' (Indian grouping)."""
    amount = abs(_dec(value).quantize(Decimal("0.01")))
    rupees = int(amount)
    paise = int((amount - rupees) * 100)
    text = f"Rupees {_indian_words(rupees)}"
    if paise:
        text += f" and {_below_hundred(paise)} Paise"
    return text + " Only"


# --------------------------------------------------------------------------
# Template, Round 4 (BR-m): plain black and white, no band, no watermark,
# no tint. Only what the document needs.
# --------------------------------------------------------------------------
GREY = "#555555"   # small print on white: 7.5:1
LINE = "#bbbbbb"


def _clinic_header(doc: InvoiceDoc) -> str:
    logo = (
        f'<td class="logo"><img src="{doc.clinic_logo_src}" alt="" '
        f'style="width: {_logo_mm(doc.clinic_logo_src)[0]}mm; height: {_logo_mm(doc.clinic_logo_src)[1]}mm" /></td>'
        if doc.clinic_logo_src
        else ""
    )
    lines = []
    address = format_address(doc.address_line, doc.city, doc.state, doc.pincode)
    if address:
        lines.append(_esc(address))
    contact = " &middot; ".join(_esc(v) for v in (_filled(doc.phone), _filled(doc.email)) if v)
    if contact:
        lines.append(contact)
    ids = " &middot; ".join(
        f"{label} {_esc(v)}" for label, v in (("GSTIN", _filled(doc.gstin)), ("Reg. No.", _filled(doc.registration_number))) if v
    )
    if ids:
        lines.append(ids)
    body = "".join(f"<p>{line}</p>" for line in lines)
    return (
        f'<table class="clinic"><tr>{logo}<td><p class="cname">{_esc(doc.clinic_name)}</p>{body}</td></tr></table>'
    )


def _logo_mm(src: str) -> tuple[float, float]:
    from app.services.report_letterhead import _fit_box

    return _fit_box(src, 30.0, 16.0)


def _kv(rows: list[tuple[str, str]]) -> str:
    return "".join(
        f'<tr><td class="k">{k}</td><td class="v">{v}</td></tr>' for k, v in rows if v
    )


def _items_table(doc: InvoiceDoc) -> str:
    if doc.items:
        body = "".join(
            f"<tr><td>{_esc(it.description)}</td><td class='num'>{_esc(it.quantity)}</td>"
            f"<td class='num'>{money(it.unit_price)}</td><td class='num'>{money(it.total_price)}</td></tr>"
            for it in doc.items
        )
    else:
        body = '<tr><td colspan="4" class="empty">No line items recorded on this invoice.</td></tr>'
    return f"""
<table class="items">
  <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Rate</th><th class="num">Amount</th></tr></thead>
  <tbody>{body}</tbody>
</table>"""


def _totals(doc: InvoiceDoc) -> str:
    rows = [("Subtotal", money(doc.subtotal), "")]
    if _dec(doc.discount_amount) > 0:
        pct = percent_text(doc.discount_percent)
        rows.append((f"Discount{f' ({pct})' if pct else ''}", f"- {money(doc.discount_amount)}", ""))
    if _dec(doc.tax_amount) > 0:
        pct = percent_text(doc.tax_percent)
        rows.append((f"Tax{f' ({pct})' if pct else ''}", money(doc.tax_amount), ""))
    rows.append(("Total", money(doc.total_amount), "grand"))
    rows.append(("Paid", money(doc.paid_amount), ""))
    balance = max(Decimal("0"), _dec(doc.total_amount) - _dec(doc.paid_amount))
    rows.append(("Balance", money(balance), "bal"))
    body = "".join(
        f'<tr class="{cls}"><td class="k">{_esc(k)}</td><td class="num">{_esc(v)}</td></tr>' for k, v, cls in rows
    )
    return f'<table class="totals">{body}</table>'


def receipt_payment(doc: InvoiceDoc) -> ReceiptPayment | None:
    """The payment this receipt is for (D-043: one receipt per payment)."""
    if doc.payment is not None:
        return doc.payment
    done = [p for p in doc.payments if (p.status or "completed") == "completed"]
    # Same date: the one recorded later (higher receipt number) wins.
    return (
        max(done, key=lambda p: (p.paid_on or datetime.min.replace(tzinfo=IST), p.receipt_number or ""))
        if done
        else None
    )


def document_number(doc: InvoiceDoc) -> str:
    if doc.kind == "receipt":
        pay = receipt_payment(doc)
        return (pay.receipt_number if pay and pay.receipt_number else "") or doc.invoice_number
    return doc.invoice_number


def _invoice_body(doc: InvoiceDoc) -> str:
    bill = _kv(
        [
            ("Name", f"<b>{_esc(doc.patient_name)}</b>"),
            ("Patient ID", _esc(doc.patient_id) if _filled(doc.patient_id) else ""),
            ("Phone", _esc(doc.patient_phone) if _filled(doc.patient_phone) else ""),
        ]
    )
    meta = _kv(
        [
            ("Invoice No.", f"<b>{_esc(doc.invoice_number)}</b>"),
            ("Date", _esc(display_date(doc.issue_date))),
            ("Due date", _esc(display_date(doc.due_date))),
        ]
    )
    notes = f'<p class="notes"><b>Notes</b> {_esc(doc.notes)}</p>' if _filled(doc.notes) else ""
    return f"""
<p class="title">INVOICE</p>
<table class="two"><tr>
  <td><p class="cap">Bill to</p><table class="kv">{bill}</table></td>
  <td class="right"><table class="kv r">{meta}</table></td>
</tr></table>
{_items_table(doc)}
<table class="after"><tr>
  <td class="words"><p class="cap">Amount in words</p><p>{_esc(amount_in_words(doc.total_amount))}</p>{notes}</td>
  <td class="tot">{_totals(doc)}</td>
</tr></table>"""


def _receipt_body(doc: InvoiceDoc) -> str:
    pay = receipt_payment(doc)
    if pay is None:
        return '<p class="title">RECEIPT</p><p>No payment has been recorded against this invoice.</p>'
    mode = METHOD_LABEL.get(str(pay.method), str(pay.method))
    if pay.status and pay.status != "completed":
        mode = f"{mode} ({pay.status})"
    balance = max(Decimal("0"), _dec(doc.total_amount) - _dec(doc.paid_amount))
    rows = _kv(
        [
            ("Receipt No.", f"<b>{_esc(document_number(doc))}</b>"),
            ("Date", _esc(display_date(pay.paid_on))),
            ("Received from", f"<b>{_esc(doc.patient_name)}</b>"),
            ("Patient ID", _esc(doc.patient_id) if _filled(doc.patient_id) else ""),
            ("Against invoice", _esc(doc.invoice_number)),
            ("Amount received", f"<b>{money(pay.amount)}</b>"),
            ("Amount in words", _esc(amount_in_words(pay.amount))),
            ("Payment mode", _esc(mode)),
            ("Transaction ref.", _esc(pay.reference) if _filled(pay.reference) else ""),
            ("Invoice total", money(doc.total_amount)),
            ("Balance due", f"<b>{money(balance)}</b>"),
        ]
    )
    return f"""
<p class="title">RECEIPT</p>
<table class="kv receipt">{rows}</table>"""


def _signatory(doc: InvoiceDoc) -> str:
    """Round 4 (27 Nov 2026): a signature line with the clinic's authorised
    person, text only (no signature image). The line stays even when no name
    is set, so the paper can still be signed."""
    name = _filled(doc.authorised_person)
    who = f'<p class="sname">{_esc(name)}</p>' if name else ""
    clinic = f'<p class="sfor">For {_esc(doc.clinic_name)}</p>' if _filled(doc.clinic_name) else ""
    return f'<div class="sign">{clinic}<div class="sline"></div>{who}<p class="slabel">Authorised signatory</p></div>'


def build_invoice_html(doc: InvoiceDoc) -> str:
    title = "Receipt" if doc.kind == "receipt" else "Invoice"
    body = _receipt_body(doc) if doc.kind == "receipt" else _invoice_body(doc)
    number = document_number(doc)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<title>{_esc(title)} {_esc(number)}</title>
<style>
{font_faces()}
@page {{
  size: A4;
  margin: 16mm 16mm 18mm 16mm;
  background-color: #ffffff;
  @bottom-left {{ content: "{_esc(number)}"; font-family: 'Inter', sans-serif; font-size: 7pt; color: {GREY}; }}
  @bottom-center {{ content: "Powered by Aarogya Virohan · AV Suite"; font-family: 'Inter', sans-serif;
    font-size: 7pt; color: {GREY}; }}
  @bottom-right {{ content: "Page " counter(page) " of " counter(pages);
    font-family: 'Inter', sans-serif; font-size: 7pt; color: {GREY}; }}
}}
body {{ font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #000;
  margin: 0; line-height: 1.45; font-size: 9.5pt; }}
p {{ margin: 0; }}
.clinic {{ border-collapse: collapse; width: 100%; padding-bottom: 4mm; border-bottom: 0.4mm solid #000; }}
.clinic td {{ vertical-align: middle; padding: 0 0 4mm 0; font-size: 8.5pt; color: #222; }}
.clinic td.logo {{ width: 1%; padding-right: 4mm; }}
.clinic .cname {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 700; font-size: 13pt; color: #000;
  margin-bottom: 0.8mm; }}
.title {{ font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-weight: 800; font-size: 16pt;
  letter-spacing: 2px; margin: 6mm 0 4mm 0; }}
.cap {{ font-size: 7.5pt; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; color: {GREY};
  margin-bottom: 1mm; }}
.two {{ width: 100%; border-collapse: collapse; margin-bottom: 5mm; }}
.two td {{ vertical-align: top; padding: 0; width: 50%; }}
.two td.right {{ text-align: right; }}
.kv {{ border-collapse: collapse; }}
.kv.r {{ margin-left: auto; }}
.kv td {{ padding: 0.6mm 0; vertical-align: top; }}
.kv .k {{ color: {GREY}; padding-right: 5mm; white-space: nowrap; }}
.kv.r .v {{ text-align: right; }}
.kv.receipt {{ width: 100%; margin-top: 2mm; }}
.kv.receipt td {{ padding: 2mm 0; border-bottom: 0.2mm solid {LINE}; }}
.kv.receipt .k {{ width: 45mm; }}
.items {{ width: 100%; border-collapse: collapse; }}
.items th {{ text-align: left; font-size: 8pt; font-weight: 700; border-top: 0.4mm solid #000;
  border-bottom: 0.4mm solid #000; padding: 1.8mm 2mm; }}
.items td {{ padding: 2mm; border-bottom: 0.2mm solid {LINE}; vertical-align: top; }}
.items .num {{ text-align: right; white-space: nowrap; }}
.items .empty {{ color: {GREY}; text-align: center; }}
.items tr {{ page-break-inside: avoid; }}
.after {{ width: 100%; border-collapse: collapse; margin-top: 4mm; page-break-inside: avoid; }}
.after td {{ vertical-align: top; padding: 0; }}
.after td.words {{ width: 55%; padding-right: 8mm; }}
.notes {{ margin-top: 4mm !important; font-size: 8.5pt; }}
.totals {{ width: 100%; border-collapse: collapse; }}
.totals td {{ padding: 1.2mm 2mm; }}
.totals .k {{ color: #222; }}
.totals .num {{ text-align: right; white-space: nowrap; }}
.totals tr.grand td {{ border-top: 0.4mm solid #000; border-bottom: 0.4mm solid #000; font-weight: 700; font-size: 10.5pt; }}
.totals tr.bal td {{ font-weight: 700; }}
.sign {{ width: 62mm; margin: 16mm 0 0 auto; text-align: center; page-break-inside: avoid; font-size: 8.5pt; }}
.sign .sfor {{ color: #222; margin-bottom: 12mm; }}
.sign .sline {{ border-top: 0.3mm solid #000; }}
.sign .sname {{ font-weight: 700; margin-top: 1.2mm; }}
.sign .slabel {{ color: {GREY}; font-size: 7.5pt; margin-top: 0.6mm; }}
</style></head>
<body>
{_clinic_header(doc)}
{body}
{_signatory(doc)}
</body></html>
"""


def _render(html_content: str) -> bytes:
    if HTML is None:
        raise RuntimeError("PDF generation requires WeasyPrint and its native libraries.")
    return HTML(string=html_content).write_pdf()


async def render_invoice_pdf(doc: InvoiceDoc) -> bytes:
    """Resolve the clinic logo, build the HTML and render it off the event loop."""
    from app.services.prescription_pdf import fetch_logo

    # Invoices show the logo exactly as uploaded (BR-m), whatever the
    # letterhead background mode.
    doc.clinic_logo_src = await letterhead_logo(doc.clinic_logo, LOGO_BG_AS_IS, None, fetch_logo)
    return await asyncio.to_thread(_render, build_invoice_html(doc))
