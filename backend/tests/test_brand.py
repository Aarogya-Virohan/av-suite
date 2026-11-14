"""
Shared brand module (app/services/brand.py, 14 Nov 2026).

The palette and brand assets moved out of posture/pdf_service.py so the
report letterhead, prescription and invoice PDFs do not import the posture
module. These tests keep both halves of that true: the old names still work
from pdf_service, and the shared PDF modules load without it.
"""

import subprocess
import sys
from pathlib import Path

from app.services import brand
from app.services.posture import pdf_service

BACKEND = Path(__file__).resolve().parents[1]

PALETTE = (
    "MIDNIGHT", "MIDNIGHT_2", "DEEP_TEAL", "GROVE", "LIME", "BRAND", "BRAND_DARK",
    "INK", "MUTED", "ON_DARK", "PAGE", "PAPER", "RULE", "ZEBRA",
    "POWERED_BY_COMPANY", "POWERED_BY_PRODUCT",
)


def test_pdf_service_reexports_the_same_objects():
    for name in PALETTE:
        assert getattr(pdf_service, name) is getattr(brand, name), name
    assert pdf_service._brand_data_uri is brand.brand_data_uri
    assert pdf_service._font_faces is brand.font_faces


def test_brand_assets_resolve():
    assert brand.BRAND_DIR.is_dir()
    assert brand.brand_data_uri("av_logo_round.png").startswith("data:image/png;base64,")
    assert brand.brand_data_uri("does-not-exist.png") == ""
    assert "@font-face" in brand.font_faces()


def test_shared_pdf_modules_do_not_import_the_posture_package():
    code = (
        "import sys\n"
        "import app.services.report_letterhead, app.services.invoice_pdf, app.services.prescription_pdf\n"
        "loaded = [m for m in sys.modules if m.startswith('app.services.posture')]\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_watermark_is_the_round_mark_faded(monkeypatch):
    import base64, io
    from PIL import Image

    uri = brand.watermark_data_uri()
    assert uri.startswith("data:image/png;base64,")
    image = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    source = Image.open(brand.BRAND_DIR / brand.WATERMARK_FILE)
    assert image.size == source.size
    assert image.getchannel("A").getextrema()[1] == round(255 * brand.WATERMARK_OPACITY)
    # The white disc behind the artwork is dropped, not faded into a pale patch.
    rgba = source.convert("RGBA")
    white = [xy for xy in ((x, y) for x in range(0, rgba.width, 7) for y in range(0, rgba.height, 7))
             if rgba.getpixel(xy)[3] == 255 and min(rgba.getpixel(xy)[:3]) >= 250]
    assert white and all(image.getpixel(xy)[3] == 0 for xy in white)

    brand.watermark_data_uri.cache_clear()
    monkeypatch.setattr(brand, "WATERMARK_FILE", "")
    try:
        assert brand.watermark_data_uri() == ""
    finally:
        monkeypatch.undo()
        brand.watermark_data_uri.cache_clear()


def test_prescription_uses_the_watermark_switch(monkeypatch):
    from app.services import prescription_pdf
    from app.services.prescription_pdf import RxDoc, build_prescription_html

    doc = RxDoc(rx_id="7b825459-0000-0000-0000-000000000000", clinic_name="", physio_name="",
                patient_name="P", patient_phone=None, patient_dob=None, prescribed_on=None,
                physio_notes=None)
    assert brand.watermark_data_uri() in build_prescription_html(doc)
    monkeypatch.setattr(prescription_pdf, "watermark_data_uri", lambda: "")
    assert "background-image" not in build_prescription_html(doc)
