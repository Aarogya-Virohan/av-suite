from __future__ import annotations

from enum import StrEnum


class DocumentCategory(StrEnum):
    """Categories for patient documents and medical attachments."""

    MEDICAL_REPORT = "medical_report"
    PRESCRIPTION = "prescription"
    LAB_RESULT = "lab_result"
    CONSENT_FORM = "consent_form"
    X_RAY_SCAN = "x_ray_scan"
    ID_PROOF = "id_proof"
    OTHER = "other"
