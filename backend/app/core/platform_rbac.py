from fastapi import Depends
from app.core.dependencies import get_platform_operator
from app.exceptions import BaseAppException
from app.models.platform import PlatformOperator

PLATFORM_PERMISSION_REGISTRY = frozenset({
    "platform.organizations.read", "platform.organizations.manage",
    "platform.entitlements.manage", "platform.operators.manage",
    "platform.audit.read", "platform.usage.read",
})
ROLE_PERMISSIONS = {
    "owner": PLATFORM_PERMISSION_REGISTRY,
    "support": frozenset(p for p in PLATFORM_PERMISSION_REGISTRY if p.endswith(".read")),
}


def require_platform_permission(permission: str):
    if permission not in PLATFORM_PERMISSION_REGISTRY:
        raise ValueError(f"Unknown platform permission: {permission}")

    async def dependency(operator: PlatformOperator = Depends(get_platform_operator)) -> PlatformOperator:
        if permission not in ROLE_PERMISSIONS.get(operator.role, frozenset()):
            raise BaseAppException("Forbidden", "FORBIDDEN", 403)
        return operator

    return dependency
