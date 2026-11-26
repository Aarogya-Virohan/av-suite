"""
Shared report letterhead rules (Round 4, decided 26 Nov 2026; footer 27 Nov).

Clinical reports (Rx, posture, psychosocial): teal band top with the clinic
logo left, display doctor + phone + email, AV round logo right; on white
above the bottom band the report number (left) and the clinic block (name,
address, website, centred); bottom band with the white AV mark + "Powered by"
left and "Page x of y" right. Never patient data in the band or footer.
Invoice and receipt: plain black and white, number left and page right.
Uploaded logos in "background removed" mode lose their empty margins.
"""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from app.services.invoice_pdf import InvoiceDoc, build_invoice_html
from app.services.prescription_pdf import RxDoc, build_prescription_html, clinic_brand
from app.services.report_letterhead import (
    ClinicBrand,
    PatientBox,
    _trim_background,
    clinic_block_lines,
    clinic_details,
    clinical_band_html,
    clinical_footer_html,
    clinical_page_margins_mm,
    format_address,
    format_website,
    patient_box_html,
    render_logo_for_mode,
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


def _transparent(uri: str) -> str:
    return render_logo_for_mode(uri, "transparent")


# ---------------------------------------------------------------- address / website
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




def test_clinic_details_keep_tax_ids_labelled():
    rows = clinic_details(**FULL, registration_number="R-1", gstin="09ABCDE1234F1Z5")
    labels = [label for label, _ in rows]
    assert labels[-2:] == ["GSTIN", "Reg. No."] or set(labels) >= {"GSTIN", "Reg. No."}


# ---------------------------------------------------------------- clinical band + footer


def _brand(**kw) -> ClinicBrand:
    base = dict(
        name="Grove <Physio>",
        doctor_name="Dr. Asha Rao",
        phone="+91 99911 12222",
        email="clinic@example.com",
        address=format_address(FULL["address_line"], FULL["city"], FULL["state"], FULL["pincode"]),
        website="www.example.com",
    )
    base.update(kw)
    return ClinicBrand(**base)


def test_band_has_doctor_and_contacts_left_and_av_right():
    band = clinical_band_html(_brand())
    assert "Dr. Asha Rao" in band and "+91 99911 12222" in band and "clinic@example.com" in band
    assert band.index('class="cl-who') < band.index('class="cl-av"')
    # The address and website are in the footer block, never in the band.
    assert "Greater Noida" not in band and "example.com/" not in band
    assert "Powered by" not in band
    assert 'class="cl-logo"' not in band  # no logo stored


def test_band_logo_left_and_white_tile_only_in_white_mode():
    logo = _png(Image.new("RGBA", (400, 200), (200, 30, 30, 255)))
    band = clinical_band_html(_brand(logo_src=logo))
    assert band.index('class="cl-logo"') < band.index('class="cl-who') < band.index('class="cl-av"')
    assert 'class="tile"' not in band
    white = clinical_band_html(_brand(logo_src=logo, logo_bg_mode="white"))
    assert '<span class="tile">' in white


def test_band_text_is_escaped():
    band = clinical_band_html(_brand(doctor_name="Dr <b>X</b>"))
    assert "<b>X</b>" not in band and "Dr &lt;b&gt;X&lt;/b&gt;" in band


def test_footer_has_number_clinic_block_and_powered_by_but_no_patient():
    foot = clinical_footer_html(_brand(), "GRP-RX-000014")
    assert 'Report No. <b>GRP-RX-000014</b>' in foot
    assert foot.index("Report No.") < foot.index("Grove &lt;Physio&gt;") < foot.index("Powered by")
    assert "Greater Noida" in foot and "www.example.com" in foot
    assert "Aarogya Virohan" in foot and "AV Suite" in foot


def test_footer_number_is_escaped_and_optional():
    assert "Report No." not in clinical_footer_html(_brand(), "   ")
    out = clinical_footer_html(_brand(), "A <b>1</b>")
    assert "<b>1</b>" not in out.replace("<b>A &lt;b&gt;1&lt;/b&gt;</b>", "")


@pytest.mark.parametrize("missing", ["address", "website"])
def test_clinic_block_drops_empty_lines(missing):
    full = clinic_block_lines(_brand())
    short = clinic_block_lines(_brand(**{missing: ""}))
    assert len(short) == len(full) - 1


def test_bottom_margin_grows_with_the_clinic_block():
    _, three = clinical_page_margins_mm(_brand())
    _, one = clinical_page_margins_mm(_brand(address="", website=""))
    assert three > one


def test_patient_box_same_labels_and_dash_for_empty():
    box = patient_box_html(PatientBox(name="Priya <b>S</b>", patient_id="GRP-000003", report_no="GRP-RX-000001"))
    labels = ["Patient name", "Patient ID", "Age / Sex", "Date", "Treating therapist", "Report No."]
    positions = [box.index(label) for label in labels]
    assert positions == sorted(positions)
    assert "Priya &lt;b&gt;S&lt;/b&gt;" in box
    assert box.count("&ndash;") == 3  # age / sex, date, therapist


def _rx_footer(out: str) -> str:
    start = out.index('<div class="cl-footer">')
    return out[start : out.index("</tr></table></div></div>", start)]


def test_rx_footer_has_the_rx_number_but_no_patient_name():
    out = build_prescription_html(_rx(document_number="CLN-RX-000042"))
    foot = _rx_footer(out)
    assert "Unique Patientname" not in foot and "9876543210" not in foot
    assert "CLN-RX-000042" in foot
    assert "Unique Patientname" in out  # still in the patient box


def test_rx_without_stored_number_falls_back_to_old_reference():
    out = build_prescription_html(_rx())
    assert "RX-7B825459" in _rx_footer(out)


def test_rx_letterhead_shows_clinic_contacts_but_no_tax_ids():
    doc = _rx(**FULL, display_doctor_name="Dr. Asha Rao")
    out = build_prescription_html(doc)
    assert clinical_band_html(clinic_brand(doc)) in out
    assert "+91 99911 12222" in out and "clinic@example.com" in out
    assert "www.example.com" in out and "Greater Noida" in out
    assert "GSTIN" not in out and "Reg. No." not in out


# ---------------------------------------------------------------- invoice / receipt (plain B/W)


@pytest.mark.parametrize("kind,label", [("invoice", "Invoice"), ("receipt", "Receipt")])
def test_invoice_footer_has_the_number_but_no_patient_name(kind, label):
    from app.services.invoice_pdf import ReceiptPayment

    out = build_invoice_html(_inv(kind=kind, payments=[ReceiptPayment(None, "cash", None, "10", "completed")]))
    page = out[out.index("@page") : out.index("body {")]
    assert '@bottom-left { content: "INV-0042"' in page
    assert "counter(page)" in page and "Unique Patientname" not in page
    assert "Unique Patientname" in out


def test_receipt_footer_uses_the_receipt_number_of_its_payment():
    from app.services.invoice_pdf import ReceiptPayment

    pay = ReceiptPayment(None, "cash", None, "100.00", "completed", "RCP-2627-000007")
    out = build_invoice_html(_inv(kind="receipt", payments=[pay]))
    page = out[out.index("@page") : out.index("body {")]
    assert '@bottom-left { content: "RCP-2627-000007"' in page
    assert "Against invoice" in out and "INV-0042" in out


def test_invoice_is_black_and_white_without_band_or_watermark():
    out = build_invoice_html(_inv(**FULL, gstin="09ABCDE1234F1Z5", registration_number="R-1"))
    assert "cl-band" not in out and "watermark" not in out.lower()
    assert "GSTIN 09ABCDE1234F1Z5" in out and "Reg. No. R-1" in out


def test_invoice_signatory_line_with_authorised_person_text_only():
    out = build_invoice_html(_inv(authorised_person="Rohit <Verma>"))
    sign = out[out.index('<div class="sign">') :]
    assert "Authorised signatory" in sign and "Rohit &lt;Verma&gt;" in sign
    assert "<img" not in sign
    # The line stays without a name, so the paper can still be signed.
    bare = build_invoice_html(_inv())
    assert 'class="sline"' in bare and 'class="sname"' not in bare


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
    w, h = _size(_transparent(_png(img)))
    assert 3.3 < w / h < 4.4  # close to the 4:1 mark, not the 1:1 canvas


def test_transparent_margins_are_trimmed():
    img = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
    img.paste(Image.new("RGBA", (300, 100), (30, 140, 60, 255)), (250, 350))
    w, h = _size(_transparent(_png(img)))
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
