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
