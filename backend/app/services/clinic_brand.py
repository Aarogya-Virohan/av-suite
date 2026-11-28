"""
The clinic as the clinical report letterhead shows it (Round 4, BR-h, BR-i).

One place builds the ClinicBrand for the Rx, posture and psychosocial PDFs
from the clinics row, so the three reports always agree. The header doctor
name is clinics.display_doctor_name; when a clinic has not set one it falls
back to the clinic owner admin's name (the earliest admin membership of the
clinic), as Shivank sir decided on 26 Nov 2026.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.user import UserRole
from app.models.membership import Membership
from app.models.user import User
from app.services.report_letterhead import ClinicBrand, format_address, letterhead_logo


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


async def owner_admin_name(db: AsyncSession, clinic_id: Any) -> str:
    """Full name of the clinic's earliest active admin, or "" when there is none."""
    row = (
        await db.execute(
            select(User.first_name, User.last_name)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.clinic_id == clinic_id,
                Membership.role == UserRole.ADMIN,
                User.is_active.is_(True),
            )
            .order_by(Membership.created_at.asc(), Membership.id.asc())
            .limit(1)
        )
    ).first()
    if row is None:
        return ""
    return " ".join(p for p in (_text(row[0]), _text(row[1])) if p)


async def display_doctor_name(db: AsyncSession, clinic: Any) -> str:
    name = _text(getattr(clinic, "display_doctor_name", None))
    if name or clinic is None:
        return name
    return await owner_admin_name(db, clinic.id)


async def clinic_brand(db: AsyncSession, clinic: Any, fetch=None) -> ClinicBrand:
    """ClinicBrand for a clinics row; an empty brand when there is no clinic."""
    if clinic is None:
        return ClinicBrand()
    mode = getattr(clinic, "logo_bg_mode", None) or "as_is"
    logo = await letterhead_logo(
        getattr(clinic, "branding_logo_url", None),
        mode,
        getattr(clinic, "branding_logo_render", None),
        fetch,
    )
    return ClinicBrand(
        name=_text(clinic.name),
        logo_src=logo,
        logo_bg_mode=mode,
        doctor_name=await display_doctor_name(db, clinic),
        phone=_text(clinic.phone),
        email=_text(clinic.email),
        address=format_address(clinic.address_line, clinic.city, clinic.state, clinic.pincode),
        website=_text(getattr(clinic, "website", None)),
    )
