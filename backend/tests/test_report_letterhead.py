"""
Shared report letterhead and footer rules (D-036).

Clinic details come from the clinic profile, one item per line, in a fixed
order; an empty field is dropped and the lines below move up. The footer
shows "Powered by Aarogya Virohan . AV Suite" and the page count only, never
patient data. Uploaded logos lose their empty margins before sizing.
"""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from app.services.invoice_pdf import InvoiceDoc, build_invoice_html
from app.services.prescription_pdf import RxDoc, build_prescription_html
from app.services.report_letterhead import (
    _trim_background,
    clinic_detail_lines,
    clinic_details,
    footer_css,
    footer_html,
    format_address,
    format_website,
    letterhead_html,
    letterhead_page_top_mm,
    logo_from_data_uri,
)

FULL = {
    "address_line": "G-207, Beta 2 Rd, Block F, Beta II",
    "city": "Greater Noida",
    "state": "Uttar Pradesh",
    "pincode": "201310",
    "phone": "+91 99911 12222",
    "email": "clinic@example.com",
    "website": "https://www.example.com/",
}


# ---------------------------------------------------------------- details


def test_detail_lines_full_in_fixed_order():
    assert clinic_detail_lines(**FULL, registration_number="R-1", gstin="09ABCDE1234F1Z5") == [
        "G-207, Beta 2 Rd, Block F, Beta II, Greater Noida, Uttar Pradesh 201310",
        "+91 99911 12222",
        "clinic@example.com",
        "www.example.com",
        "Reg. No. R-1",
        "GSTIN 09ABCDE1234F1Z5",
    ]


@pytest.mark.parametrize("missing", ["phone", "email", "website"])
def test_missing_contact_moves_the_rest_up(missing):
    full = clinic_detail_lines(**FULL)
    lines = clinic_detail_lines(**{**FULL, missing: None})
    assert len(full) == 4 and len(lines) == 3
    assert "" not in lines
    assert lines == [v for v in full if v in lines]  # same order, gap closed
    assert all("&middot;" not in v and "·" not in v for v in lines)


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_values_count_as_missing(blank):
    assert clinic_detail_lines(phone=blank, email=blank, website=blank) == []


def test_nothing_filled_gives_no_lines():
    assert clinic_detail_lines() == []


def test_detail_lines_are_escaped():
    lines = clinic_detail_lines(address_line="<b>Lane</b> & Co", email="a<b>@x.com")
    assert lines == ["&lt;b&gt;Lane&lt;/b&gt; &amp; Co", "a&lt;b&gt;@x.com"]


def test_address_parts_not_repeated():
    assert (
        format_address("12 MG Road, Greater Noida, Uttar Pradesh", "Greater Noida", "Uttar Pradesh", "201310")
        == "12 MG Road, Greater Noida, Uttar Pradesh, 201310"
    )
    assert format_address(None, "Noida", None, None) == "Noida"
    assert format_address(None, None, "UP", "201310") == "UP 201310"
    assert format_address(None, None, None, None) == ""


def test_invalid_pincode_is_dropped():
    assert format_address("Lane 1", "Noida", None, "2013") == "Lane 1, Noida"


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("https://spineact.com/", "spineact.com"),
        ("HTTP://www.x.in", "www.x.in"),
        ("x.in/page/", "x.in/page"),
        ("  ", ""),
        (None, ""),
    ],
)
def test_website_shown_without_scheme(raw, shown):
    assert format_website(raw) == shown


# ---------------------------------------------------------------- letterhead


def _head(out: str) -> str:
    return out[out.index('<div class="letterhead">') : out.index('<div class="running-footer">')]


def test_details_are_labelled_pairs_in_fixed_order():
    assert [label for label, _ in clinic_details(**FULL, gstin="G", registration_number="R")] == [
        "Address", "Phone", "Email", "Website", "Reg. No.", "GSTIN",
    ]


def test_av_mark_is_kept_apart_from_the_clinic_contacts():
    """Founders 14 Nov: AV mark on the far right, a standing rule between it
    and the clinic's contacts, so the contacts never read as AV's."""
    out = letterhead_html("Invoice", "Clinic", "", clinic_details(**FULL))
    assert (
        out.index('class="lh-clinic"')
        < out.index('class="lh-contact-cell"')
        < out.index('class="lh-divider"')
        < out.index('class="lh-mark"')
    )
    assert "av-round" in out[out.index('class="lh-mark"') :]
    assert "Powered by" not in out and "POWERED BY" not in out


def test_no_divider_without_contacts():
    out = letterhead_html("Invoice", "Clinic", "", [])
    assert 'class="lh-divider"' not in out
    assert 'class="lh-mark"' in out


def test_contact_rows_in_order_with_icons():
    out = letterhead_html("Invoice", "Clinic", "", clinic_details(**FULL))
    block = out[out.index('class="lh-contact"') :]
    assert block.count("<tr>") == 4
    order = [block.index(v) for v in ("Greater Noida", "+91 99911 12222", "clinic@example.com", "www.example.com")]
    assert order == sorted(order)
    assert block.count("data:image/svg+xml;base64,") == 4


def test_missing_detail_has_no_row():
    out = letterhead_html("Invoice", "Clinic", "", clinic_details(**{**FULL, "phone": None}))
    block = out[out.index('class="lh-contact"') :]
    assert block.count("<tr>") == 3
    assert 'alt="Phone"' not in block


def test_ids_rows_carry_their_label():
    out = letterhead_html("Invoice", "C", "", clinic_details(gstin="G1", registration_number="R1"))
    assert '<span class="ck">GSTIN</span>G1' in out
    assert '<span class="ck">REG. NO.</span>R1' in out


def test_no_details_no_contact_block():
    out = letterhead_html("Invoice", "Clinic", "", [])
    assert "lh-contact" not in out
    assert 'class="lh-rule"' in out


def test_without_clinic_name_aarogya_virohan_letterhead():
    out = letterhead_html("Invoice", "", "", clinic_details(**FULL))
    assert 'class="av-only"' in out and "Aarogya Virohan" in out
    assert "lh-contact" not in out and 'class="lh-clinic"' not in out


def test_page_top_margin_fits_the_header():
    none = letterhead_page_top_mm([])
    four = letterhead_page_top_mm(clinic_details(**FULL))  # 2-line address + 3 = 5 lines
    six = letterhead_page_top_mm(clinic_details(**FULL, gstin="G", registration_number="R"))
    assert none == 29.0
    assert letterhead_page_top_mm(clinic_details(phone="1")) == none  # short block fits beside the logo
    assert none < four < six
    # Address wrap is capped, so a very long address cannot push the body off the page.
    assert letterhead_page_top_mm(clinic_details(address_line="x" * 2000)) == letterhead_page_top_mm(
        clinic_details(address_line="x" * 140)
    )


def test_page_top_margin_used_by_reports():
    rx = build_prescription_html(_rx(**FULL))
    inv = build_invoice_html(_inv(**FULL))
    top = letterhead_page_top_mm(clinic_details(**FULL))
    assert f"margin: {top}mm 0 20mm 0" in rx
    assert f"margin: {top}mm 0 20mm 0" in inv
    assert "margin: 29.0mm 0 20mm 0" in build_invoice_html(_inv(clinic_name=""))


def test_long_clinic_name_gets_smaller_font():
    short = letterhead_html("Invoice", "Clinic")
    long_ = letterhead_html("Invoice", "SpineAct Physiotherapy Clinic, Noida")  # 36 chars
    xlong = letterhead_html("Invoice", "SpineAct Physiotherapy Clinic (Spine &amp; Neuro Clinic)")
    assert 'class="clinic-name"' in short
    assert 'class="clinic-name long"' in long_
    assert 'class="clinic-name xlong"' in xlong


# ---------------------------------------------------------------- footer


def test_footer_is_the_old_centred_powered_by_line_and_page_count():
    out = footer_html()
    assert "POWERED BY" in out and "AAROGYA VIROHAN" in out and "AV SUITE" in out
    assert '<p class="powered">' in out and '<p class="meta"><span class="page"></span></p>' in out
    assert "text-align: center" in footer_css()


def _rx(**kw) -> RxDoc:
    base = {
        "rx_id": "7b825459-0000-0000-0000-000000000000",
        "clinic_name": "Clinic",
        "physio_name": "Asha Rao",
        "patient_name": "Unique Patientname",
        "patient_phone": "9876543210",
        "patient_dob": None,
        "prescribed_on": None,
        "physio_notes": None,
    }
    base.update(kw)
    return RxDoc(**base)


def _inv(**kw) -> InvoiceDoc:
    base = {
        "kind": "invoice",
        "invoice_number": "INV-0042",
        "status": "issued",
        "issue_date": None,
        "due_date": None,
        "clinic_name": "Clinic",
        "patient_name": "Unique Patientname",
    }
    base.update(kw)
    return InvoiceDoc(**base)


def _footer(out: str) -> str:
    start = out.index('<div class="running-footer">')
    return out[start : out.index("</div></div>", start)]


def test_rx_footer_has_the_rx_number_but_no_patient_name():
    # D-038: the document number (not the patient) identifies page 2 onwards.
    out = build_prescription_html(_rx())
    foot = _footer(out)
    assert "Unique Patientname" not in foot and "9876543210" not in foot
    assert '<span class="ref">Rx RX-7B825459</span>' in foot
    assert "Unique Patientname" in out  # still in the patient box


@pytest.mark.parametrize("kind,label", [("invoice", "Invoice"), ("receipt", "Receipt")])
def test_invoice_footer_has_the_number_but_no_patient_name(kind, label):
    out = build_invoice_html(_inv(kind=kind))
    foot = _footer(out)
    assert "Unique Patientname" not in foot
    assert f'<span class="ref">{label} INV-0042</span>' in foot
    assert "Unique Patientname" in out


def test_footer_reference_is_escaped_and_optional():
    assert '<span class="ref">' not in footer_html()
    assert '<span class="ref">' not in footer_html("   ")
    out = footer_html("Invoice <b>1</b>")
    assert "<b>1</b>" not in out and "Invoice &lt;b&gt;1&lt;/b&gt;" in out
    assert out.index('class="ref"') < out.index('class="page"')


def test_rx_letterhead_shows_clinic_contacts_but_no_tax_ids():
    out = build_prescription_html(_rx(**FULL))
    head = _head(out)
    assert "+91 99911 12222" in head and "clinic@example.com" in head
    assert "www.example.com" in head and "Greater Noida" in head
    assert "GSTIN" not in head and "Reg. No." not in head


def test_invoice_letterhead_shows_tax_ids_when_filled():
    out = build_invoice_html(_inv(**FULL, gstin="09ABCDE1234F1Z5", registration_number="R-1"))
    head = _head(out)
    assert '<span class="ck">GSTIN</span>09ABCDE1234F1Z5' in head
    assert '<span class="ck">REG. NO.</span>R-1' in head
    # The clinic block moved to the letterhead; the body starts with Billed to.
    assert "Billed to" in out


def test_invoice_thanks_line_without_clinic_name():
    out = build_invoice_html(_inv(clinic_name=""))
    assert "Thank you for visiting ." not in out
    assert "Thank you." in out


# ---------------------------------------------------------------- logo trim


def _png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _size(uri: str) -> tuple[int, int]:
    with Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))) as img:
        return img.size


def test_white_margins_are_trimmed():
    img = Image.new("RGB", (1000, 1000), "white")
    img.paste(Image.new("RGB", (400, 100), (30, 140, 60)), (300, 450))
    w, h = _size(logo_from_data_uri(_png(img)))
    assert 3.3 < w / h < 4.4  # close to the 4:1 mark, not the 1:1 canvas


def test_transparent_margins_are_trimmed():
    img = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", (300, 100), (30, 140, 60, 255)), (250, 350))
    w, h = _size(logo_from_data_uri(_png(img)))
    assert 2.6 < w / h < 3.4


def test_logo_with_different_corners_is_not_cropped():
    img = Image.new("RGB", (300, 300), "white")
    img.paste(Image.new("RGB", (20, 20), (200, 0, 0)), (0, 0))  # artwork in a corner
    out = _trim_background(img.convert("RGBA"))
    assert out.size == (300, 300)


def test_blank_logo_is_left_alone():
    img = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
    assert _trim_background(img).size == (200, 200)


def test_white_canvas_becomes_transparent_but_inner_white_is_kept():
    img = Image.new("RGB", (600, 600), "white")
    ring = Image.new("RGB", (200, 200), (30, 140, 60))
    ring.paste(Image.new("RGB", (80, 80), "white"), (60, 60))  # white inside the artwork
    img.paste(ring, (200, 200))
    out = _trim_background(img.convert("RGBA"))
    assert out.getpixel((0, 0))[3] == 0  # outer white cleared
    cx, cy = out.size[0] // 2, out.size[1] // 2
    assert out.getpixel((cx, cy)) == (255, 255, 255, 255)  # enclosed white kept


def test_dark_canvas_is_not_made_transparent():
    img = Image.new("RGB", (300, 300), (10, 20, 60))
    img.paste(Image.new("RGB", (100, 50), (240, 240, 240)), (100, 120))
    out = _trim_background(img.convert("RGBA"))
    assert all(out.getpixel(p)[3] == 255 for p in ((0, 0), (out.size[0] - 1, out.size[1] - 1)))
