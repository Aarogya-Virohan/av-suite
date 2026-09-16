from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.enums.permission import CapabilityScope
from app.enums.user import UserRole


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    """Definition for one Rev3 capability key."""

    key: str
    allowed_scopes: frozenset[CapabilityScope]


# Shorthands for the three scope sets used below.
_NA = frozenset({CapabilityScope.NONE, CapabilityScope.ALL})
_NOA = frozenset({CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL})


# ---------------------------------------------------------------------------
# CANONICAL CAPABILITY REGISTRY
#
# Naming rule: every key is exactly "module.action". No three-segment keys,
# no legacy aggregate-management keys. Granularity is per action within a module, which
# is the founder decision of 13 Aug 2026.
#
# OWN is only offered where the resource has a real per-user owner that the
# query layer can filter on. If a key offers OWN here, the corresponding
# service query MUST implement the OWN filter, otherwise the permission grid
# lies to the admin.
#
# The two public booking endpoints - GET /booking/branding/{clinic_slug} and
# POST /booking/request - are intentionally unauthenticated and carry NO
# capability. The booking.* keys below are for the staff-facing side only
# (viewing, approving, editing and deleting incoming requests).
# ---------------------------------------------------------------------------
CAPABILITY_REGISTRY: Mapping[str, CapabilityDefinition] = MappingProxyType(
    {
        # --- patients -----------------------------------------------------
        "patients.view": CapabilityDefinition("patients.view", _NOA),
        "patients.create": CapabilityDefinition("patients.create", _NA),
        "patients.edit": CapabilityDefinition("patients.edit", _NOA),
        "patients.delete": CapabilityDefinition("patients.delete", _NA),
        # --- leads --------------------------------------------------------
        "leads.view": CapabilityDefinition("leads.view", _NA),
        "leads.create": CapabilityDefinition("leads.create", _NA),
        "leads.edit": CapabilityDefinition("leads.edit", _NA),
        "leads.delete": CapabilityDefinition("leads.delete", _NA),
        "leads.convert": CapabilityDefinition("leads.convert", _NOA),
        # --- appointments -------------------------------------------------
        "appointments.view": CapabilityDefinition("appointments.view", _NOA),
        "appointments.create": CapabilityDefinition("appointments.create", _NOA),
        "appointments.edit": CapabilityDefinition("appointments.edit", _NOA),
        "appointments.delete": CapabilityDefinition("appointments.delete", _NOA),
        # --- treatments (SOAP sessions) -----------------------------------
        "treatments.view": CapabilityDefinition("treatments.view", _NOA),
        "treatments.create": CapabilityDefinition("treatments.create", _NOA),
        "treatments.edit": CapabilityDefinition("treatments.edit", _NOA),
        "treatments.delete": CapabilityDefinition("treatments.delete", _NOA),
        # --- assessments --------------------------------------------------
        "assessments.view": CapabilityDefinition("assessments.view", _NOA),
        "assessments.create": CapabilityDefinition("assessments.create", _NA),
        "assessments.edit": CapabilityDefinition("assessments.edit", _NOA),
        "assessments.delete": CapabilityDefinition("assessments.delete", _NOA),
        # --- prescriptions ------------------------------------------------
        "prescriptions.view": CapabilityDefinition("prescriptions.view", _NOA),
        "prescriptions.create": CapabilityDefinition("prescriptions.create", _NA),
        "prescriptions.edit": CapabilityDefinition("prescriptions.edit", _NOA),
        "prescriptions.delete": CapabilityDefinition("prescriptions.delete", _NOA),
        # --- exercises (clinic-wide library, ownership has no meaning) -----
        "exercises.view": CapabilityDefinition("exercises.view", _NA),
        "exercises.create": CapabilityDefinition("exercises.create", _NA),
        "exercises.edit": CapabilityDefinition("exercises.edit", _NA),
        "exercises.delete": CapabilityDefinition("exercises.delete", _NA),
        # --- documents ----------------------------------------------------
        "documents.view": CapabilityDefinition("documents.view", _NOA),
        "documents.upload": CapabilityDefinition("documents.upload", _NA),
        "documents.edit": CapabilityDefinition("documents.edit", _NOA),
        "documents.delete": CapabilityDefinition("documents.delete", _NOA),
        # --- invoices -----------------------------------------------------
        "invoices.view": CapabilityDefinition("invoices.view", _NOA),
        "invoices.create": CapabilityDefinition("invoices.create", _NA),
        "invoices.edit": CapabilityDefinition("invoices.edit", _NA),
        "invoices.delete": CapabilityDefinition("invoices.delete", _NA),
        # --- payments -----------------------------------------------------
        "payments.view": CapabilityDefinition("payments.view", _NA),
        "payments.record": CapabilityDefinition("payments.record", _NA),
        "payments.delete": CapabilityDefinition("payments.delete", _NA),
        # --- packages (packages.assign covers patient-package create+edit) -
        "packages.view": CapabilityDefinition("packages.view", _NA),
        "packages.create": CapabilityDefinition("packages.create", _NA),
        "packages.edit": CapabilityDefinition("packages.edit", _NA),
        "packages.delete": CapabilityDefinition("packages.delete", _NA),
        "packages.assign": CapabilityDefinition("packages.assign", _NA),
        # --- booking (staff-facing only, see note above) ------------------
        "booking.view": CapabilityDefinition("booking.view", _NA),
        "booking.approve": CapabilityDefinition("booking.approve", _NA),
        "booking.edit": CapabilityDefinition("booking.edit", _NA),
        "booking.delete": CapabilityDefinition("booking.delete", _NA),
        # --- analytics ----------------------------------------------------
        # my_performance allows ALL so an admin can see clinic-wide figures
        # on the same page a therapist sees only their own.
        "analytics.my_performance": CapabilityDefinition(
            "analytics.my_performance", _NOA
        ),
        "analytics.clinic_financials": CapabilityDefinition(
            "analytics.clinic_financials", _NA
        ),
        # --- settings -----------------------------------------------------
        "settings.view": CapabilityDefinition("settings.view", _NA),
        "settings.edit": CapabilityDefinition("settings.edit", _NA),
        # --- users --------------------------------------------------------
        # users.view is granted to front desk so the therapist dropdown works
        # when booking an appointment. Salary and registration number MUST NOT
        # be returned by users.view - gate those behind users.edit.
        "users.view": CapabilityDefinition("users.view", _NA),
        "users.create": CapabilityDefinition("users.create", _NA),
        "users.edit": CapabilityDefinition("users.edit", _NA),
        "users.delete": CapabilityDefinition("users.delete", _NA),
        # --- permissions --------------------------------------------------
        "permissions.view": CapabilityDefinition("permissions.view", _NA),
        "permissions.edit": CapabilityDefinition("permissions.edit", _NA),
        # --- audit --------------------------------------------------------
        "audit.view": CapabilityDefinition("audit.view", _NA),
        # --- recycle bin --------------------------------------------------
        "recyclebin.view": CapabilityDefinition("recyclebin.view", _NA),
        "recyclebin.restore": CapabilityDefinition("recyclebin.restore", _NA),
        # --- posture ------------------------------------------------------
        "posture.view": CapabilityDefinition("posture.view", _NOA),
        "posture.create": CapabilityDefinition("posture.create", _NA),
    }
)


_ALL = CapabilityScope.ALL
_OWN = CapabilityScope.OWN
_NONE = CapabilityScope.NONE


def _admin_template() -> Mapping[str, CapabilityScope]:
    """Admin gets the widest scope every capability allows."""

    return MappingProxyType(
        {
            key: (_ALL if _ALL in definition.allowed_scopes else _OWN)
            for key, definition in CAPABILITY_REGISTRY.items()
        }
    )


# ---------------------------------------------------------------------------
# ROLE TEMPLATES
#
# These are DEFAULTS ONLY. An admin can override any capability per user in
# the user_permissions table, and that override wins (see
# resolve_capability_scope below).
#
# Source: the approved RBAC matrix issued to the frontend in Aug 2026.
# Any key not listed for a role resolves to NONE.
#
# Adding a new role (for example Manager) means adding one entry here. No
# other file should need to change.
# ---------------------------------------------------------------------------
ROLE_TEMPLATES: Mapping[UserRole, Mapping[str, CapabilityScope]] = MappingProxyType(
    {
        UserRole.ADMIN: _admin_template(),
        UserRole.THERAPIST: MappingProxyType(
            {
                "patients.view": _OWN,
                "patients.create": _ALL,
                "patients.edit": _OWN,
                "patients.delete": _NONE,
                "leads.view": _NONE,
                "leads.create": _NONE,
                "leads.edit": _NONE,
                "leads.delete": _NONE,
                "leads.convert": _NONE,
                "appointments.view": _OWN,
                "appointments.create": _OWN,
                "appointments.edit": _OWN,
                "appointments.delete": _OWN,
                "treatments.view": _OWN,
                "treatments.create": _OWN,
                "treatments.edit": _OWN,
                "treatments.delete": _OWN,
                "assessments.view": _OWN,
                "assessments.create": _ALL,
                "assessments.edit": _OWN,
                "assessments.delete": _NONE,
                "prescriptions.view": _OWN,
                "prescriptions.create": _ALL,
                "prescriptions.edit": _OWN,
                "prescriptions.delete": _NONE,
                "exercises.view": _ALL,
                "exercises.create": _NONE,
                "exercises.edit": _NONE,
                "exercises.delete": _NONE,
                "documents.view": _OWN,
                "documents.upload": _ALL,
                "documents.edit": _OWN,
                "documents.delete": _NONE,
                "invoices.view": _NONE,
                "invoices.create": _NONE,
                "invoices.edit": _NONE,
                "invoices.delete": _NONE,
                "payments.view": _NONE,
                "payments.record": _NONE,
                "payments.delete": _NONE,
                "packages.view": _NONE,
                "packages.create": _NONE,
                "packages.edit": _NONE,
                "packages.delete": _NONE,
                "packages.assign": _NONE,
                "booking.view": _NONE,
                "booking.approve": _NONE,
                "booking.edit": _NONE,
                "booking.delete": _NONE,
                "analytics.my_performance": _OWN,
                "analytics.clinic_financials": _NONE,
                "settings.view": _NONE,
                "settings.edit": _NONE,
                "users.view": _NONE,
                "users.create": _NONE,
                "users.edit": _NONE,
                "users.delete": _NONE,
                "permissions.view": _NONE,
                "permissions.edit": _NONE,
                "audit.view": _NONE,
                "recyclebin.view": _NONE,
                "recyclebin.restore": _NONE,
                "posture.view": _OWN,
                "posture.create": _ALL,
            }
        ),
        UserRole.FRONT_DESK: MappingProxyType(
            {
                "patients.view": _ALL,
                "patients.create": _ALL,
                "patients.edit": _ALL,
                "patients.delete": _NONE,
                "leads.view": _ALL,
                "leads.create": _ALL,
                "leads.edit": _ALL,
                "leads.delete": _NONE,
                "leads.convert": _ALL,
                "appointments.view": _ALL,
                "appointments.create": _ALL,
                "appointments.edit": _NONE,
                "appointments.delete": _ALL,
                "treatments.view": _NONE,
                "treatments.create": _NONE,
                "treatments.edit": _NONE,
                "treatments.delete": _NONE,
                "assessments.view": _NONE,
                "assessments.create": _NONE,
                "assessments.edit": _NONE,
                "assessments.delete": _NONE,
                "prescriptions.view": _NONE,
                "prescriptions.create": _NONE,
                "prescriptions.edit": _NONE,
                "prescriptions.delete": _NONE,
                "exercises.view": _ALL,
                "exercises.create": _NONE,
                "exercises.edit": _NONE,
                "exercises.delete": _NONE,
                "documents.view": _ALL,
                "documents.upload": _ALL,
                "documents.edit": _ALL,
                "documents.delete": _NONE,
                "invoices.view": _ALL,
                "invoices.create": _ALL,
                "invoices.edit": _NONE,
                "invoices.delete": _NONE,
                "payments.view": _ALL,
                "payments.record": _ALL,
                "payments.delete": _NONE,
                "packages.view": _ALL,
                "packages.create": _NONE,
                "packages.edit": _NONE,
                "packages.delete": _NONE,
                "packages.assign": _ALL,
                "booking.view": _ALL,
                "booking.approve": _ALL,
                "booking.edit": _ALL,
                "booking.delete": _NONE,
                "analytics.my_performance": _NONE,
                "analytics.clinic_financials": _NONE,
                "settings.view": _NONE,
                "settings.edit": _NONE,
                "users.view": _ALL,
                "users.create": _NONE,
                "users.edit": _NONE,
                "users.delete": _NONE,
                "permissions.view": _NONE,
                "permissions.edit": _NONE,
                "audit.view": _NONE,
                "recyclebin.view": _NONE,
                "recyclebin.restore": _NONE,
                "posture.view": _NONE,
                "posture.create": _NONE,
            }
        ),
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


def validate_role_templates() -> None:
    """Fail fast if any role template contains an unknown key or illegal scope.

    Called at application startup so a template typo cannot reach production
    as a silently missing permission.
    """

    for role, template in ROLE_TEMPLATES.items():
        for capability_key, scope in template.items():
            if capability_key not in CAPABILITY_REGISTRY:
                raise ValueError(
                    f"ROLE_TEMPLATES[{role.value}] references unknown "
                    f"capability '{capability_key}'"
                )
            validate_capability_scope(capability_key, scope)
