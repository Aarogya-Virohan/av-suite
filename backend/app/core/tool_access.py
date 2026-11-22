"""BE-1: the three tool checkboxes on a clinic user (C1, CRM-6).

A tool checkbox is a fixed bundle of capability overrides. Checking a tool
writes the bundle scopes as explicit overrides; unchecking writes NONE for
the same keys (needed because the admin template grants everything).

Keys and scopes match scripts/clinic_setup TOOL_CAPABILITIES (EN-4), so a
clinic set up by the script and one edited in the Users screen agree.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import resolve_capability_scope
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.product import WorkspaceProduct
from app.models.user_permission import UserPermission
from app.repositories.user_permission import UserPermissionRepository
from app.schemas.user_permission import UserPermissionCreate
from app.screening.access import CLINICAL_CAPABILITIES, check_clinical_grant

_ALL = CapabilityScope.ALL
_OWN = CapabilityScope.OWN

# Order = order of the checkboxes in the UI.
TOOL_KEYS: tuple[str, ...] = (
    "psycho-social-screening",
    "exercise-library",
    "posture-tool",
)

TOOL_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "psycho-social-screening": "Psychosocial",
        "exercise-library": "Exercise Library",
        "posture-tool": "Posture",
    }
)

TOOL_CAPABILITIES: Mapping[str, Mapping[str, CapabilityScope]] = MappingProxyType(
    {
        "exercise-library": MappingProxyType(
            {
                "exercises.view": _ALL,
                "prescriptions.view": _ALL,
                "prescriptions.create": _ALL,
                "prescriptions.edit": _OWN,
            }
        ),
        "posture-tool": MappingProxyType(
            {"posture.view": _ALL, "posture.create": _ALL}
        ),
        "psycho-social-screening": MappingProxyType(
            {
                "screening.assign": _ALL,
                "screening.view": _OWN,
                "screening.refer": _OWN,
            }
        ),
    }
)

# Clinic products a tool needs (same as clinic_setup TOOL_PRODUCTS).
TOOL_PRODUCTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "exercise-library": ("exercise-library", "exercise-prescription"),
        "posture-tool": ("posture-tool",),
        "psycho-social-screening": ("psycho-social-screening",),
    }
)


def bundle_for(tool: str, role: UserRole | str) -> dict[str, CapabilityScope]:
    """Capability bundle of one tool for a role.

    Front desk never holds screening answers (S-D-036), so for front desk the
    Psychosocial checkbox means "can assign screenings" only.
    """

    bundle = dict(TOOL_CAPABILITIES[tool])
    if UserRole(role) == UserRole.FRONT_DESK:
        for key in CLINICAL_CAPABILITIES:
            bundle.pop(key, None)
    return bundle


def tools_state(
    role: UserRole | str, overrides: Mapping[str, CapabilityScope | str]
) -> dict[str, bool]:
    """A tool is on when every key of its bundle resolves to a scope other than none."""

    role = UserRole(role)
    return {
        tool: all(
            resolve_capability_scope(role, key, overrides) != CapabilityScope.NONE
            for key in bundle_for(tool, role)
        )
        for tool in TOOL_KEYS
    }


async def entitled_tools(db: AsyncSession, clinic_id: UUID) -> dict[str, bool]:
    enabled = set(
        (
            await db.scalars(
                select(WorkspaceProduct.product_id).where(
                    WorkspaceProduct.clinic_id == clinic_id,
                    WorkspaceProduct.status == EntitlementStatus.ENABLED,
                )
            )
        ).all()
    )
    return {tool: all(p in enabled for p in TOOL_PRODUCTS[tool]) for tool in TOOL_KEYS}


async def overrides_by_user(
    db: AsyncSession, clinic_id: UUID, user_ids: Iterable[UUID] | None = None
) -> dict[UUID, dict[str, CapabilityScope]]:
    stmt = select(UserPermission).where(UserPermission.clinic_id == clinic_id)
    if user_ids is not None:
        stmt = stmt.where(UserPermission.user_id.in_(list(user_ids)))
    out: dict[UUID, dict[str, CapabilityScope]] = {}
    for row in (await db.scalars(stmt)).all():
        out.setdefault(row.user_id, {})[row.capability_key] = CapabilityScope(row.scope)
    return out


def validate_tool_keys(tools: Iterable[str]) -> list[str]:
    tools = list(dict.fromkeys(tools))
    unknown = [t for t in tools if t not in TOOL_CAPABILITIES]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNKNOWN_TOOL",
                "message": f"Unknown tool(s): {', '.join(unknown)}. Allowed: {', '.join(TOOL_KEYS)}.",
            },
        )
    return tools


async def apply_tools(
    db: AsyncSession,
    *,
    clinic_id: UUID,
    actor_id: UUID,
    target_id: UUID,
    target_role: UserRole | str,
    enabled: Iterable[str],
) -> dict[str, bool]:
    """Set the user's tool checkboxes to exactly `enabled`. Caller commits.

    Raises 400 TOOL_NOT_IN_PLAN when a tool is switched on that the clinic is
    not entitled to, and passes on the Tool 03 clinical-grant 403s.
    """

    from app.services.audit import AuditLogService
    from app.repositories.audit import AuditLogRepository

    role = UserRole(target_role)
    wanted = set(validate_tool_keys(enabled))
    entitled = await entitled_tools(db, clinic_id)
    repo = UserPermissionRepository(db)
    existing_rows = await repo.list_for_user_in_clinic(clinic_id, target_id)
    existing = {r.capability_key: CapabilityScope(r.scope) for r in existing_rows}
    before = tools_state(role, existing)

    turning_on = [t for t in TOOL_KEYS if t in wanted and not before[t]]
    not_in_plan = [t for t in turning_on if not entitled[t]]
    if not_in_plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOOL_NOT_IN_PLAN",
                "message": "This clinic's plan does not include: "
                + ", ".join(TOOL_LABELS[t] for t in not_in_plan),
                "tools": not_in_plan,
            },
        )

    desired: dict[str, CapabilityScope] = {}
    for tool in TOOL_KEYS:
        bundle = bundle_for(tool, role)
        if tool in wanted:
            if before[tool]:
                continue  # already on: keep any wider/narrower custom scopes
            desired.update(bundle)
        elif before[tool]:
            desired.update({key: CapabilityScope.NONE for key in bundle})

    changes = {k: v for k, v in desired.items() if existing.get(k) != v}
    if changes:
        await check_clinical_grant(
            db,
            clinic_id=clinic_id,
            actor_id=actor_id,
            target_id=target_id,
            target_role=role,
            requested=[UserPermissionCreate(capability_key=k, scope=v) for k, v in changes.items()],
            existing=existing_rows,
        )
        for key, scope in changes.items():
            await repo.set_override(
                clinic_id=clinic_id,
                user_id=target_id,
                capability_key=key,
                scope=scope,
                granted_by=actor_id,
            )
            existing[key] = scope
        after = tools_state(role, existing)
        await AuditLogService(AuditLogRepository(db)).log_event(
            clinic_id=clinic_id,
            user_id=actor_id,
            action="set_tool_access",
            entity_type="user_permissions",
            entity_id=target_id,
            details={
                "target_user_id": str(target_id),
                "tools_before": before,
                "tools_after": after,
            },
        )
        return after
    return before
