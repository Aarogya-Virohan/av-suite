"""
The signed-in clinic on the posture report, 17 November 2026.

The report used to carry a placeholder clinic ("AV Clinic") whatever clinic
the clinician had signed in to. The clinic now comes from the clinics row of
the request's clinic (the same row /auth/me returns), never from the report
body the client posts: the PDF route rebuilds it on every export, so a
posted report cannot put another clinic's name or a remote logo on paper.

The PDF uses the shared report letterhead (app/services/report_letterhead.py,
D-036): name, logo, address and contacts. Registration number and GSTIN stay
off, as on the exercise prescription; they belong on invoices. The web report
gets the same values as plain text in report["branding"].
"""

from __future__ import annotations

from typing import Any

from app.services.prescription_pdf import fetch_logo
from app.services.report_letterhead import (
    ClinicBrand,
    clinic_details,
    format_address,
    letterhead_logo,
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


async def clinic_letterhead(clinic: Any, doctor_name: str = "") -> dict:
    """
    {"name", "logoSrc", "details", "brand"} for build_report_html, from a
    Clinic row. `brand` is the Round 4 letterhead (ClinicBrand); `doctor_name`
    is the clinic's display doctor name with its fallback already applied
    (app/services/clinic_brand.py). An empty dict when there is no clinic.
    """
    if clinic is None or not _text(getattr(clinic, "name", None)):
        return {}
    mode = getattr(clinic, "logo_bg_mode", None) or "as_is"
    logo = await letterhead_logo(
        getattr(clinic, "branding_logo_url", None),
        mode,
        getattr(clinic, "branding_logo_render", None),
        fetch_logo,
    )
    details = clinic_details(
        address_line=getattr(clinic, "address_line", None),
        city=getattr(clinic, "city", None),
        state=getattr(clinic, "state", None),
        pincode=getattr(clinic, "pincode", None),
        phone=getattr(clinic, "phone", None),
        email=getattr(clinic, "email", None),
    )
    brand = ClinicBrand(
        name=_text(clinic.name),
        logo_src=logo,
        logo_bg_mode=mode,
        doctor_name=_text(doctor_name) or _text(getattr(clinic, "display_doctor_name", None)),
        phone=_text(getattr(clinic, "phone", None)),
        email=_text(getattr(clinic, "email", None)),
        address=format_address(
            getattr(clinic, "address_line", None),
            getattr(clinic, "city", None),
            getattr(clinic, "state", None),
            getattr(clinic, "pincode", None),
        ),
        website=_text(getattr(clinic, "website", None)),
    )
    return {"name": _text(clinic.name), "logoSrc": logo, "details": details, "brand": brand}


def web_branding(clinic: Any, logo_src: str = "") -> dict:
    """
    report["branding"] for the web report (ReportHeader.tsx): the same clinic
    as the PDF, as plain text. No head doctor: the clinics row has none
    (decision 13 Nov, authorised_person is not a doctor).
    """
    if clinic is None or not _text(getattr(clinic, "name", None)):
        return {}
    branding = {
        "clinicName": _text(clinic.name),
        "logo": logo_src,
        "addressLine": format_address(
            getattr(clinic, "address_line", None),
            getattr(clinic, "city", None),
            getattr(clinic, "state", None),
            getattr(clinic, "pincode", None),
        ),
        "phone": _text(getattr(clinic, "phone", None)),
        "email": _text(getattr(clinic, "email", None)),
    }
    return {k: v for k, v in branding.items() if v}
