from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, List, Mapping

from app.enums.permission import CapabilityScope
from app.enums.user import UserRole


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    """Definition for one Rev3 capability key."""

    key: str
    allowed_scopes: frozenset[CapabilityScope]


CAPABILITY_REGISTRY: Mapping[str, CapabilityDefinition] = MappingProxyType(
    {
        "analytics.my_performance": CapabilityDefinition(
            key="analytics.my_performance",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                }
            ),
        ),
        "analytics.clinic_financials": CapabilityDefinition(
            key="analytics.clinic_financials",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "permissions.manage": CapabilityDefinition(
            key="permissions.manage",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "users.manage": CapabilityDefinition(
            key="users.manage",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "treatments.view": CapabilityDefinition(
            key="treatments.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "treatments.create": CapabilityDefinition(
            key="treatments.create",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "treatments.edit": CapabilityDefinition(
            key="treatments.edit",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "appointments.view": CapabilityDefinition(
            key="appointments.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "appointments.create": CapabilityDefinition(
            key="appointments.create",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "appointments.edit": CapabilityDefinition(
            key="appointments.edit",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Assessment capabilities
        "assessments.view": CapabilityDefinition(
            key="assessments.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "assessments.create": CapabilityDefinition(
            key="assessments.create",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "assessments.edit": CapabilityDefinition(
            key="assessments.edit",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Document capabilities
        "documents.view": CapabilityDefinition(
            key="documents.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "documents.upload": CapabilityDefinition(
            key="documents.upload",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Billing capabilities
        "billing.invoice.view": CapabilityDefinition(
            key="billing.invoice.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "billing.invoice.create": CapabilityDefinition(
            key="billing.invoice.create",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "billing.payment.record": CapabilityDefinition(
            key="billing.payment.record",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Package capabilities
        "packages.view": CapabilityDefinition(
            key="packages.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "packages.manage": CapabilityDefinition(
            key="packages.manage",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Lead capabilities
        "leads.view": CapabilityDefinition(
            key="leads.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "leads.manage": CapabilityDefinition(
            key="leads.manage",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Booking capabilities
        "booking.requests.manage": CapabilityDefinition(
            key="booking.requests.manage",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Prescription capabilities
        "prescriptions.create": CapabilityDefinition(
            key="prescriptions.create",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Posture capabilities
        "posture.view": CapabilityDefinition(
            key="posture.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "posture.create": CapabilityDefinition(
            key="posture.create",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.OWN,
                    CapabilityScope.ALL,
                }
            ),
        ),
        # Governance capabilities
        "therapists.view": CapabilityDefinition(
            key="therapists.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "settings.edit": CapabilityDefinition(
            key="settings.edit",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "recyclebin.restore": CapabilityDefinition(
            key="recyclebin.restore",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
        "audit.view": CapabilityDefinition(
            key="audit.view",
            allowed_scopes=frozenset(
                {
                    CapabilityScope.NONE,
                    CapabilityScope.ALL,
                }
            ),
        ),
    }
)


ROLE_TEMPLATES: Mapping[UserRole, Mapping[str, CapabilityScope]] = MappingProxyType(
    {
        UserRole.ADMIN: MappingProxyType(
            {
                "analytics.my_performance": CapabilityScope.OWN,
                "analytics.clinic_financials": CapabilityScope.ALL,
                "permissions.manage": CapabilityScope.ALL,
                "users.manage": CapabilityScope.ALL,
                "treatments.view": CapabilityScope.ALL,
                "treatments.create": CapabilityScope.ALL,
                "treatments.edit": CapabilityScope.ALL,
                "appointments.view": CapabilityScope.ALL,
                "appointments.create": CapabilityScope.ALL,
                "appointments.edit": CapabilityScope.ALL,
                "assessments.view": CapabilityScope.ALL,
                "assessments.create": CapabilityScope.ALL,
                "assessments.edit": CapabilityScope.ALL,
                "documents.view": CapabilityScope.ALL,
                "documents.upload": CapabilityScope.ALL,
                "billing.invoice.view": CapabilityScope.ALL,
                "billing.invoice.create": CapabilityScope.ALL,
                "billing.payment.record": CapabilityScope.ALL,
                "packages.view": CapabilityScope.ALL,
                "packages.manage": CapabilityScope.ALL,
                "leads.view": CapabilityScope.ALL,
                "leads.manage": CapabilityScope.ALL,
                "booking.requests.manage": CapabilityScope.ALL,
                "prescriptions.create": CapabilityScope.ALL,
                "posture.view": CapabilityScope.ALL,
                "posture.create": CapabilityScope.ALL,
                "therapists.view": CapabilityScope.ALL,
                "settings.edit": CapabilityScope.ALL,
                "recyclebin.restore": CapabilityScope.ALL,
                "audit.view": CapabilityScope.ALL,
            }
        ),
        UserRole.THERAPIST: MappingProxyType(
            {
                "analytics.my_performance": CapabilityScope.OWN,
                "treatments.view": CapabilityScope.OWN,
                "treatments.create": CapabilityScope.OWN,
                "treatments.edit": CapabilityScope.OWN,
                "appointments.view": CapabilityScope.OWN,
                "appointments.create": CapabilityScope.OWN,
                "appointments.edit": CapabilityScope.OWN,
                "assessments.view": CapabilityScope.OWN,
                "assessments.create": CapabilityScope.OWN,
                "assessments.edit": CapabilityScope.OWN,
                "documents.view": CapabilityScope.OWN,
                "documents.upload": CapabilityScope.OWN,
                "prescriptions.create": CapabilityScope.OWN,
                "posture.view": CapabilityScope.OWN,
                "posture.create": CapabilityScope.OWN,
            }
        ),
        UserRole.FRONT_DESK: MappingProxyType(
            {
                "appointments.view": CapabilityScope.ALL,
                "appointments.create": CapabilityScope.ALL,
                "documents.view": CapabilityScope.ALL,
                "documents.upload": CapabilityScope.ALL,
                "billing.invoice.view": CapabilityScope.ALL,
                "billing.invoice.create": CapabilityScope.ALL,
                "billing.payment.record": CapabilityScope.ALL,
                "packages.view": CapabilityScope.ALL,
                "leads.view": CapabilityScope.ALL,
                "leads.manage": CapabilityScope.ALL,
                "booking.requests.manage": CapabilityScope.ALL,
            }
        ),
        UserRole.PATIENT: MappingProxyType({}),
    }
)


def get_capability_definition(capability_key: str) -> CapabilityDefinition | None:
    """Return the registered capability definition, if known."""

    return CAPABILITY_REGISTRY.get(capability_key)


def get_role_template(role: UserRole) -> Mapping[str, CapabilityScope]:
    """Return the default capability template for a role."""

    return ROLE_TEMPLATES.get(role, MappingProxyType({}))


def validate_capability_scope(
    capability_key: str, scope: CapabilityScope | str
) -> CapabilityScope:
    """Validate that a scope is allowed for a known capability."""

    capability = get_capability_definition(capability_key)
    if capability is None:
        raise ValueError(f"Unknown capability: {capability_key}")

    normalized_scope = CapabilityScope(scope)
    if normalized_scope not in capability.allowed_scopes:
        raise ValueError(
            f"Scope '{normalized_scope.value}' is not allowed for '{capability_key}'"
        )

    return normalized_scope


def resolve_capability_scope(
    role: UserRole,
    capability_key: str,
    user_permissions: Mapping[str, CapabilityScope | str] | None = None,
) -> CapabilityScope:
    """Resolve effective scope using explicit override, then role template, then none."""

    if capability_key not in CAPABILITY_REGISTRY:
        return CapabilityScope.NONE

    if user_permissions is not None and capability_key in user_permissions:
        return validate_capability_scope(
            capability_key, user_permissions[capability_key]
        )

    return get_role_template(role).get(capability_key, CapabilityScope.NONE)


# Centralized Permission Map
# Maps a resource/feature area to the list of roles that are allowed to access it.
# Adding a new role (e.g., Manager) is as simple as adding it to the appropriate lists here.
PERMISSION_MAP: Dict[str, List[UserRole]] = {
    "patients": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "assessments": [UserRole.ADMIN, UserRole.THERAPIST],
    "billing": [UserRole.ADMIN, UserRole.FRONT_DESK],
    "analytics": [
        UserRole.ADMIN,
        UserRole.THERAPIST,
    ],  # RBAC Spec §4: Front Desk has NO analytics access
    "leads": [UserRole.ADMIN, UserRole.FRONT_DESK],
    "documents": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "appointments": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "exercises": [UserRole.ADMIN, UserRole.THERAPIST],
    "posture": [UserRole.ADMIN, UserRole.THERAPIST],
    "prescriptions": [UserRole.ADMIN, UserRole.THERAPIST],
    "settings": [UserRole.ADMIN],
    "packages": [UserRole.ADMIN],
    "clinic_admin": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "booking": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "appointment_requests": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
}
