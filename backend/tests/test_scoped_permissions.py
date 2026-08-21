import pytest

from app.core.rbac import (
    CapabilityScope,
    get_capability_definition,
    get_role_template,
    resolve_capability_scope,
    validate_capability_scope,
)
from app.enums.user import UserRole


def test_known_capability_lookup() -> None:
    capability = get_capability_definition("analytics.my_performance")

    assert capability is not None
    assert capability.key == "analytics.my_performance"
    assert capability.allowed_scopes == {CapabilityScope.NONE, CapabilityScope.OWN}


def test_unknown_capability_resolves_to_denied() -> None:
    scope = resolve_capability_scope(UserRole.ADMIN, "analytics.unregistered")

    assert scope == CapabilityScope.NONE


def test_role_template_lookup() -> None:
    template = get_role_template(UserRole.ADMIN)

    assert template["permissions.manage"] == CapabilityScope.ALL
    assert template["users.manage"] == CapabilityScope.ALL


def test_default_role_permission_resolution() -> None:
    admin_scope = resolve_capability_scope(UserRole.ADMIN, "analytics.clinic_financials")
    therapist_scope = resolve_capability_scope(UserRole.THERAPIST, "analytics.my_performance")
    front_desk_scope = resolve_capability_scope(UserRole.FRONT_DESK, "analytics.my_performance")

    assert admin_scope == CapabilityScope.ALL
    assert therapist_scope == CapabilityScope.OWN
    assert front_desk_scope == CapabilityScope.NONE


def test_explicit_none_override_denies_role_template_grant() -> None:
    scope = resolve_capability_scope(
        UserRole.ADMIN,
        "permissions.manage",
        user_permissions={"permissions.manage": CapabilityScope.NONE},
    )

    assert scope == CapabilityScope.NONE


def test_allowed_scope_validation() -> None:
    scope = validate_capability_scope("permissions.manage", "all")

    assert scope == CapabilityScope.ALL


def test_disallowed_scope_validation() -> None:
    with pytest.raises(ValueError):
        validate_capability_scope("permissions.manage", CapabilityScope.OWN)
