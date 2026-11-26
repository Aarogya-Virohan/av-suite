"""
Posture PDF is four pages (Round 4 fix, 27 Nov 2026): side plane on page 1,
coronal and posterior planes together on page 2, signature and synthesis on
page 3, sources and the closing block on page 4. The bigger footer block
(report number + clinic name, address, website) must not push a plane onto a
page of its own, also with long clinic details and long source notes.
"""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image
from pypdf import PdfReader

from app.services.posture import pdf_service as ps
from app.services.posture import reference_ranges as rr
from app.services.posture import report_builder as rb
from app.services.posture.synthesizer import generate_synthesis
from app.services.report_letterhead import ClinicBrand, format_address

pytest.importorskip("weasyprint")


def _photo() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (600, 1200), (190, 200, 210)).save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _report() -> dict:
    M = rb.measurement
    side = [M("PT-L01", "Head Position (ear–shoulder angle)", 48.2, "°", "under_review"),
            M("PT-L05", "Knee Hyperextension", 4.1, "°", "none"),
            M("PT-L06", "Trunk Lean", 6.8, "°", "mild", "forward")]
    front = [M("PT-A01", "Head Tilt", 3.9, "°", "mild", "right"),
             M("PT-A04", "Pelvic Obliquity", 2.2, "°", "none"),
             M("PT-A05", "Left Knee Alignment", 9.6, "°", "moderate", "valgus"),
             M("PT-A06", "Right Knee Alignment", 5.4, "°", "mild", "valgus")]
    back = [M("PT-P01", "Shoulder Level Asymmetry", 11.0, "mm", "under_review"),
            M("PT-P02", "Trunk Shift", 7.5, "mm", "mild", "left")]
    photo = _photo()
    view = lambda ms: rb.build_side_view_result(ms, photo, 0.93, "camera")  # noqa: E731
    findings = {m["paramId"]: m["severity"] for m in side + front + back}
    patient = {"name": "Anil Kapoor", "age": 52, "gender": "Male", "heightCm": 171,
               "caseRef": "SPC-000119", "assessmentDate": "2026-11-26", "clinician": "Dr. Arjun Mehta (PT)"}
    report = rb.build_report_response(patient, view(side), view(front), view(back), generate_synthesis(findings))
    report["reportId"] = "PT-20261126-ABCD1234"
    report["reportNumber"] = "SPC-POS-000017"
    return report


def _pages(brand: ClinicBrand) -> list[str]:
    from weasyprint import HTML

    pdf = HTML(string=ps.build_report_html(_report(), {"brand": brand})).write_pdf()
    return [p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages]


LONG = ClinicBrand(
    name="Sukoon Physiotherapy & Sports Rehabilitation Centre, Sector 50",
    doctor_name="Dr. Meera Raghavan (PT), MPT Orthopaedics",
    phone="+91 98110 42375",
    email="appointments.care@sukoonphysio.in",
    address=format_address(
        "Plot 14, First Floor, Sector 50 Market, Near Metro Gate 2, Opposite Central Park",
        "Noida", "Uttar Pradesh", "201301",
    ),
    website="https://www.sukoonphysiotherapy-rehab.in/",
)


@pytest.mark.parametrize("brand", [ClinicBrand(name="Short Clinic"), LONG], ids=["short", "long"])
def test_posture_pdf_is_four_pages_with_front_and_back_together(brand):
    pages = _pages(brand)
    assert len(pages) == 4
    assert "Sagittal" in pages[0]
    assert "Coronal" in pages[1] and "Posterior" in pages[1]
    assert "DISCLAIMER" in pages[3]
    for i, text in enumerate(pages, start=1):
        assert f"Page {i} of 4" in text
        assert "SPC-POS-000017" in text  # report number above every footer


def test_long_source_notes_keep_four_pages(monkeypatch):
    longer = [{**s, "note": (s.get("note") or "Measured on the photograph.") * 2} for s in rr.SOURCES]
    monkeypatch.setattr(rr, "SOURCES", longer)
    pages = _pages(LONG)
    assert len(pages) == 4
    assert "Coronal" in pages[1] and "Posterior" in pages[1]


def test_paired_photo_height_is_capped_and_shrinks_with_the_footer():
    assert ps.paired_plane_photo_mm(ClinicBrand()) <= ps.PAIR_PHOTO_MAX_MM
    assert ps.paired_plane_photo_mm(LONG) < ps.paired_plane_photo_mm(ClinicBrand(name="x"))
