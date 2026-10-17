from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


CANONICAL_PRODUCTS: tuple[dict[str, object], ...] = (
    {
        "id": "crm",
        "slug": "crm",
        "name": "CRM",
        "description": "Patient management, scheduling and clinic operations.",
        "category": "Patient Management",
        "allowed_clinic_types": ["clinic"],
    },
    {
        "id": "exercise-library",
        "slug": "exercise-library",
        "name": "Exercise Library",
        "description": "Clinical exercise resources and structured exercise programs.",
        "category": "Clinical",
        "allowed_clinic_types": ["clinic", "solo", "personal"],
    },
    {
        "id": "exercise-prescription",
        "slug": "exercise-prescription",
        "name": "Exercise Prescription",
        "description": "Build and manage personalized exercise programs.",
        "category": "Clinical",
        "allowed_clinic_types": ["clinic", "solo", "personal"],
    },
    {
        "id": "posture-tool",
        "slug": "posture-tool",
        "name": "Posture Tool",
        "description": "Posture assessment and movement analysis.",
        "category": "Clinical",
        "allowed_clinic_types": ["clinic", "solo", "personal"],
    },
    {
        "id": "clinical-decision-support",
        "slug": "clinical-decision-support",
        "name": "Clinical Decision Support",
        "description": "Structured clinical insights for better decision-making.",
        "category": "Clinical",
        "allowed_clinic_types": ["clinic", "solo", "personal"],
    },
    {
        "id": "psycho-social-screening",
        "slug": "psycho-social-screening",
        "name": "Psycho-social Screening",
        "description": "Screening and tracking for psycho-social factors.",
        "category": "Clinical",
        "allowed_clinic_types": ["clinic", "solo", "personal"],
    },
)


CRM_CAPABILITY_PREFIXES: tuple[str, ...] = (
    "leads.",
    "appointments.",
    "treatments.",
    "assessments.",
    "documents.",
    "invoices.",
    "payments.",
    "packages.",
    "booking.",
    "recyclebin.",
    "analytics.",
)

PRODUCT_CAPABILITY_PREFIXES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "exercise-library": ("exercises.",),
        "posture-tool": ("posture.",),
        "exercise-prescription": ("prescriptions.",),
    }
)


def _capabilities_for_prefix(prefix: str) -> tuple[str, ...]:
    from app.core.rbac import CAPABILITY_REGISTRY

    return tuple(key for key in CAPABILITY_REGISTRY if key.startswith(prefix))


CAPABILITY_PRODUCT_MAP: Mapping[str, str] = MappingProxyType(
    {
        # Platform-core capabilities such as patients, users, permissions,
        # audit, and settings remain governed by RBAC without a product gate.
        **{
            capability_key: "crm"
            for prefix in CRM_CAPABILITY_PREFIXES
            for capability_key in _capabilities_for_prefix(prefix)
        },
        **{
            capability_key: product_id
            for product_id, prefixes in PRODUCT_CAPABILITY_PREFIXES.items()
            for prefix in prefixes
            for capability_key in _capabilities_for_prefix(prefix)
        },
    }
)


def product_for_capability(capability_key: str) -> str | None:
    return CAPABILITY_PRODUCT_MAP.get(capability_key)
