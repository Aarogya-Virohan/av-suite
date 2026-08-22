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
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN}),
        ),
        "analytics.clinic_financials": CapabilityDefinition(
            key="analytics.clinic_financials",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "patients.view": CapabilityDefinition(
            key="patients.view",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "patients.create": CapabilityDefinition(
            key="patients.create",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "patients.edit": CapabilityDefinition(
            key="patients.edit",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "patients.delete": CapabilityDefinition(
            key="patients.delete",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "permissions.manage": CapabilityDefinition(
            key="permissions.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "users.manage": CapabilityDefinition(
            key="users.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "treatments.view": CapabilityDefinition(
            key="treatments.view",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "treatments.create": CapabilityDefinition(
            key="treatments.create",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "treatments.edit": CapabilityDefinition(
            key="treatments.edit",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "appointments.view": CapabilityDefinition(
            key="appointments.view",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "appointments.create": CapabilityDefinition(
            key="appointments.create",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "appointments.edit": CapabilityDefinition(
            key="appointments.edit",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "leads.view": CapabilityDefinition(
            key="leads.view",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "leads.create": CapabilityDefinition(
            key="leads.create",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "leads.edit": CapabilityDefinition(
            key="leads.edit",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "leads.delete": CapabilityDefinition(
            key="leads.delete",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "billing.view": CapabilityDefinition(
            key="billing.view",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "billing.create": CapabilityDefinition(
            key="billing.create",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "billing.edit": CapabilityDefinition(
            key="billing.edit",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "billing.delete": CapabilityDefinition(
            key="billing.delete",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "documents.view": CapabilityDefinition(
            key="documents.view",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "documents.upload": CapabilityDefinition(
            key="documents.upload",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL}),
        ),
        "documents.delete": CapabilityDefinition(
            key="documents.delete",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "settings.manage": CapabilityDefinition(
            key="settings.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "booking.manage": CapabilityDefinition(
            key="booking.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "packages.manage": CapabilityDefinition(
            key="packages.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "exercises.manage": CapabilityDefinition(
            key="exercises.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "posture.manage": CapabilityDefinition(
            key="posture.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        ),
        "prescriptions.manage": CapabilityDefinition(
            key="prescriptions.manage",
            allowed_scopes=frozenset({CapabilityScope.NONE, CapabilityScope.ALL}),
        )

    }
)


ROLE_TEMPLATES: Mapping[UserRole, Mapping[str, CapabilityScope]] = MappingProxyType(
    {
        UserRole.ADMIN: MappingProxyType(
            {
                "patients.view": CapabilityScope.ALL,
                "patients.create": CapabilityScope.ALL,
                "patients.edit": CapabilityScope.ALL,
                "patients.delete": CapabilityScope.ALL,
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
                "leads.view": CapabilityScope.ALL,
                "leads.create": CapabilityScope.ALL,
                "leads.edit": CapabilityScope.ALL,
                "leads.delete": CapabilityScope.ALL,
                "billing.view": CapabilityScope.ALL,
                "billing.create": CapabilityScope.ALL,
                "billing.edit": CapabilityScope.ALL,
                "billing.delete": CapabilityScope.ALL,
                "documents.view": CapabilityScope.ALL,
                "documents.upload": CapabilityScope.ALL,
                "documents.delete": CapabilityScope.ALL,
                "settings.manage": CapabilityScope.ALL,
                "booking.manage": CapabilityScope.ALL,
                "packages.manage": CapabilityScope.ALL,
                "exercises.manage": CapabilityScope.ALL,
                "posture.manage": CapabilityScope.ALL,
                "prescriptions.manage": CapabilityScope.ALL,
            }
        ),
        UserRole.THERAPIST: MappingProxyType(
            {
                "patients.view": CapabilityScope.OWN,
                "patients.create": CapabilityScope.ALL,
                "patients.edit": CapabilityScope.OWN,
                "analytics.my_performance": CapabilityScope.OWN,
                "treatments.view": CapabilityScope.OWN,
                "treatments.create": CapabilityScope.OWN,
                "treatments.edit": CapabilityScope.OWN,
                "appointments.view": CapabilityScope.OWN,
                "appointments.create": CapabilityScope.OWN,
                "appointments.edit": CapabilityScope.OWN,
                "documents.view": CapabilityScope.OWN,
                "documents.upload": CapabilityScope.OWN,
                "exercises.manage": CapabilityScope.ALL,
                "posture.manage": CapabilityScope.ALL,
                "prescriptions.manage": CapabilityScope.ALL,
            }
        ),
        UserRole.FRONT_DESK: MappingProxyType(
            {
                "patients.view": CapabilityScope.ALL,
                "patients.create": CapabilityScope.ALL,
                "patients.edit": CapabilityScope.ALL,
                "appointments.view": CapabilityScope.ALL,
                "appointments.create": CapabilityScope.ALL,
                "leads.view": CapabilityScope.ALL,
                "leads.create": CapabilityScope.ALL,
                "leads.edit": CapabilityScope.ALL,
                "billing.view": CapabilityScope.ALL,
                "billing.create": CapabilityScope.ALL,
                "booking.manage": CapabilityScope.ALL,
            }
        ),
        UserRole.PATIENT: MappingProxyType({})

    }
)


def get_capability_definition(capability_key: str) -> CapabilityDefinition | None:
    """Return the registered capability definition, if known."""

    return CAPABILITY_REGISTRY.get(capability_key)


def get_role_template(role: UserRole) -> Mapping[str, CapabilityScope]:
    """Return the default capability template for a role."""

    return ROLE_TEMPLATES.get(role, MappingProxyType({}))


def validate_capability_scope(capability_key: str, scope: CapabilityScope | str) -> CapabilityScope:
    """Validate that a scope is allowed for a known capability."""

    capability = get_capability_definition(capability_key)
    if capability is None:
        raise ValueError(f"Unknown capability: {capability_key}")

    normalized_scope = CapabilityScope(scope)
    if normalized_scope not in capability.allowed_scopes:
        raise ValueError(f"Scope '{normalized_scope.value}' is not allowed for '{capability_key}'")

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
        return validate_capability_scope(capability_key, user_permissions[capability_key])

    return get_role_template(role).get(capability_key, CapabilityScope.NONE)

# Centralized Permission Map
# Maps a resource/feature area to the list of roles that are allowed to access it.
# Adding a new role (e.g., Manager) is as simple as adding it to the appropriate lists here.
PERMISSION_MAP: Dict[str, List[UserRole]] = {
    "patients": [UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK],
    "assessments": [UserRole.ADMIN, UserRole.THERAPIST],
    "billing": [UserRole.ADMIN, UserRole.FRONT_DESK],
    "analytics": [UserRole.ADMIN, UserRole.THERAPIST],  # RBAC Spec §4: Front Desk has NO analytics access
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
