"""Posture reports tied to a CRM patient (POS-2 / BE-2, 23 Nov 2026).

The patient behind a posture report is a CRM patient of the signed-in clinic.
Name, age and sex come from that record, the case ID shown on the report is the
patient's CRM ID, and the finished report is saved in posture_sessions so it
can be opened and downloaded again. Before this the report took free text and
wrote a JSON file to the container disk, which Railway wipes on every deploy.
"""

from __future__ import annotations

import copy
import re
import uuid
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.posture_session import PostureSession
from app.services.clinic_code import derive_clinic_code
from app.services.patient_number import format_patient_id

PATIENT_NOT_FOUND = "Patient not found or not in caller's clinic"
REPORT_NOT_FOUND = "Report not found"

def clinic_code(code: str | None, clinic_name: str | None = None) -> str:
    """The clinic's own code (clinics.code, set in Settings; unique, 1 to 6
    letters or digits). Only when it is empty is the name rule used, which is
    what the code was first derived from (services/clinic_code.py)."""
    stored = (code or "").strip().upper()
    return stored or derive_clinic_code(clinic_name)


def format_case_id(display_number: int | None, code: str | None, clinic_name: str | None = None) -> str:
    """The Patient ID the CRM shows ("ASC2-000004"): clinic code, then the
    display number padded to 6 digits. Empty without a number."""
    if display_number is None or display_number < 0:
        return ""
    return format_patient_id(clinic_code(code, clinic_name), display_number)


def patient_age(patient: Patient, today: date) -> int | None:
    """Age from the date of birth when the CRM has one, else the stored age."""
    dob = patient.date_of_birth
    if dob is not None:
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return years if years >= 0 else None
    return patient.age


def gender_label(patient: Patient) -> str:
    value = getattr(patient.gender, "value", patient.gender)
    return str(value).capitalize() if value else ""


def patient_summary(patient: Patient, clinic: Any, today: date) -> dict[str, Any]:
    """What the picker shows. No phone, no clinical data."""
    return {
        "id": str(patient.id),
        "displayNumber": int(patient.display_number),
        "caseId": format_case_id(patient.display_number, clinic.code, clinic.name),
        "name": patient.full_name,
        "age": patient_age(patient, today),
        "gender": gender_label(patient),
    }


async def get_clinic_patient(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> Patient:
    """The patient, or 404 when it is not a live patient of this clinic (as AUD-05).

    Clinic-wide on purpose: a posture assessment is often the first thing done
    for a patient, before any appointment ties a therapist to them, so the
    "own patients" scope of the CRM list is not applied here.
    """
    query = select(Patient).where(
        Patient.id == patient_id,
        Patient.clinic_id == clinic_id,
        Patient.deleted_at.is_(None),
    )
    patient = (await db.execute(query)).scalars().first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PATIENT_NOT_FOUND)
    return patient


async def search_clinic_patients(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    term: str,
    limit: int = 20,
) -> list[Patient]:
    """Live patients of the clinic whose name or CRM ID matches the term."""
    query = select(Patient).where(Patient.clinic_id == clinic_id, Patient.deleted_at.is_(None))
    term = (term or "").strip()
    if term:
        # "SPC-000123", "ASC2-000123" (codes can hold digits), "#123" or "123" all find
        # CRM ID 123; anything else is a name.
        digits = re.fullmatch(
            r"\s*#?\s*(?:[A-Za-z0-9]{1,6}\s*[-#\s]\s*|[A-Za-z]{1,6})?(\d{1,18})\s*", term
        )
        matches = [Patient.full_name.ilike(f"%{term}%")]
        if digits:
            matches.append(Patient.display_number == int(digits.group(1)))
        query = query.where(or_(*matches))
    query = query.order_by(Patient.first_name, Patient.last_name, Patient.display_number).limit(limit)
    return list((await db.execute(query)).scalars().all())


def report_for_storage(report: dict) -> dict:
    """The report as saved: no photographs (founders 11 Oct 2026, 6a) and no branding.

    Branding is read again from the clinics row when a report is shown or
    printed, so a later logo or name change reaches old reports too.
    """
    saved = copy.deepcopy(report)
    saved.pop("branding", None)
    views = saved.get("views")
    if isinstance(views, dict):
        for view in views.values():
            if isinstance(view, dict):
                view.pop("photoUrl", None)
    return saved


async def save_report(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    user_id: uuid.UUID | None,
    report: dict,
) -> PostureSession:
    row = PostureSession(
        clinic_id=clinic_id,
        patient_id=patient_id,
        report_id=str(report["reportId"]),
        report_json=report_for_storage(report),
        analysis_version=str(report.get("analysisVersion") or "") or None,
        created_by_user_id=user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def get_saved_report(db: AsyncSession, clinic_id: uuid.UUID, report_id: str) -> PostureSession:
    row = (
        await db.execute(
            select(PostureSession).where(
                PostureSession.clinic_id == clinic_id,
                PostureSession.report_id == report_id,
                PostureSession.report_json.is_not(None),
            )
        )
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=REPORT_NOT_FOUND)
    return row


async def list_saved_reports(
    db: AsyncSession, clinic_id: uuid.UUID, patient_id: uuid.UUID, limit: int = 50
) -> list[PostureSession]:
    rows = await db.execute(
        select(PostureSession)
        .where(
            PostureSession.clinic_id == clinic_id,
            PostureSession.patient_id == patient_id,
            PostureSession.report_json.is_not(None),
        )
        .order_by(PostureSession.created_at.desc())
        .limit(limit)
    )
    return list(rows.scalars().all())


def report_listing(row: PostureSession) -> dict[str, Any]:
    return {
        "reportId": row.report_id,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "assessmentDate": ((row.report_json or {}).get("patient") or {}).get("assessmentDate"),
        "clinician": ((row.report_json or {}).get("patient") or {}).get("clinician") or "",
        "analysisVersion": row.analysis_version,
    }
