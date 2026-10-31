"""Invoice and receipt PDF (Decisions.md L-41): real PDF, real content."""

import io
import re
from decimal import Decimal

import pytest
from pypdf import PdfReader

from app.core.config import settings
from app.services.invoice_pdf import money, pdf_filename, percent_text

API = settings.API_V1_PREFIX


def _text(pdf: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf))
    return " ".join((page.extract_text() or "") for page in reader.pages)


def _has(text: str, needle: str) -> bool:
    """Tags are upper-cased and letter-spaced by CSS, and the PDF text keeps
    that (\"P A Y M E N T S\"), so compare without case and whitespace."""
    squash = lambda v: re.sub(r"\s+", "", v).lower()
    return squash(needle) in squash(text)


async def _setup(client, auth_headers):
    profile = await client.patch(
        f"{API}/settings/clinic",
        json={
            "address_line": "12 MG Road",
            "city": "Noida",
            "state": "Uttar Pradesh",
            "pincode": "201301",
            "phone": "9811000001",
            "registration_number": "REG-77",
            "gstin": "09ABCDE1234F1Z5",
            "authorised_person": "Dr Meera Rao",
        },
        headers=auth_headers,
    )
    assert profile.status_code == 200, profile.text
    patient = await client.post(
        f"{API}/patients",
        json={"first_name": "Kavya", "last_name": "Nair", "phone": "9898765011"},
        headers=auth_headers,
    )
    assert patient.status_code in (200, 201), patient.text
    patient_id = patient.json()["data"]["id"]
    invoice = await client.post(
        f"{API}/invoices",
        json={
            "patient_id": patient_id,
            "issue_date": "2026-10-20T20:30:00Z",
            "due_date": "2026-10-30T06:00:00Z",
            "items": [
                {"description": "Knee rehab session", "quantity": 2, "unit_price": "750.00"},
                {"description": "Dry needling", "quantity": 1, "unit_price": "500.00"},
            ],
            "discount_percent": "10",
            "tax_percent": "18",
            "notes": "Pay at front desk",
        },
        headers=auth_headers,
    )
    assert invoice.status_code == 201, invoice.text
    return patient_id, invoice.json()


@pytest.mark.asyncio
async def test_invoice_pdf_is_real_and_has_the_printed_content(client, auth_headers):
    _, inv = await _setup(client, auth_headers)
    res = await client.get(f"{API}/invoices/{inv['id']}/pdf/download", headers=auth_headers)
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/pdf"
    assert f'filename="Invoice-{inv["invoice_number"]}.pdf"' in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
    text = _text(res.content)
    for expected in (
        "Kavya Nair",
        "9898765011",
        "12 MG Road, Noida, Uttar Pradesh 201301",
        "GSTIN 09ABCDE1234F1Z5",
        "Reg. No. REG-77",
        "Knee rehab session",
        "Dry needling",
        "Discount (10%)",
        "Tax (18%)",
        "Rs. 2,000.00",  # subtotal
        "Rs. 2,124.00",  # total: 2000 - 200 + 324
        inv["invoice_number"],
        "21 Oct 2026",  # 20:30 UTC is the next day in India
        "Pay at front desk",
        "Due 30 Oct 2026",
        "Authorised by Dr Meera Rao",
        "does not need a signature",
    ):
        assert _has(text, expected), expected
    assert not _has(text, "Payments received")
    assert not _has(text, "Balance due")  # nothing paid yet, so no Paid / Balance rows


@pytest.mark.asyncio
async def test_receipt_pdf_lists_payments_and_balance(client, auth_headers):
    patient_id, inv = await _setup(client, auth_headers)
    paid = await client.post(
        f"{API}/payments",
        json={
            "invoice_id": inv["id"],
            "patient_id": patient_id,
            "amount": "1000.00",
            "payment_method": "upi",
            "payment_date": "2026-10-22T05:00:00Z",
            "transaction_reference": "UPI-REF-4411",
        },
        headers=auth_headers,
    )
    assert paid.status_code in (200, 201), paid.text
    res = await client.get(
        f"{API}/invoices/{inv['id']}/pdf/download", params={"kind": "receipt"}, headers=auth_headers
    )
    assert res.status_code == 200, res.text
    assert f'filename="Receipt-{inv["invoice_number"]}.pdf"' in res.headers["content-disposition"]
    text = _text(res.content)
    for expected in ("Payment Receipt", "Payments received", "UPI", "UPI-REF-4411", "22 Oct 2026",
                     "Rs. 1,000.00", "Balance due", "Rs. 1,124.00"):
        assert _has(text, expected), expected
    assert "Due " not in text  # no due date on a receipt


@pytest.mark.asyncio
async def test_pdf_bad_kind_and_other_clinic(client, auth_headers):
    _, inv = await _setup(client, auth_headers)
    bad = await client.get(
        f"{API}/invoices/{inv['id']}/pdf/download", params={"kind": "quote"}, headers=auth_headers
    )
    assert bad.status_code == 422
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": "Other Pdf Clinic", "email": "otherpdf@physiodemo.in",
              "password": "Password123!", "first_name": "Other", "last_name": "Admin"},
    )
    assert reg.status_code in (200, 201), reg.text
    other = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    res = await client.get(f"{API}/invoices/{inv['id']}/pdf/download", headers=other)
    assert res.status_code == 404
    unauth = await client.get(f"{API}/invoices/{inv['id']}/pdf/download")
    assert unauth.status_code in (401, 403)


@pytest.mark.asyncio
async def test_generate_link_points_at_the_real_route(client, auth_headers):
    _, inv = await _setup(client, auth_headers)
    res = await client.post(f"{API}/invoices/{inv['id']}/pdf", headers=auth_headers)
    assert res.status_code == 200, res.text
    assert res.json()["download_url"] == f"/api/v1/invoices/{inv['id']}/pdf/download"


def test_formatting_helpers():
    assert money("1234567.5") == "Rs. 12,34,567.50"
    assert money(Decimal("0")) == "Rs. 0.00"
    assert money("999") == "Rs. 999.00"
    assert percent_text("10.00") == "10%"
    assert percent_text("12.50") == "12.5%"
    assert percent_text(None) is None
    assert pdf_filename("receipt", "INV/2026 01") == "Receipt-INV-2026-01.pdf"
