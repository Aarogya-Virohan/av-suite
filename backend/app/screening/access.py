"""Who may hold the clinical screening capabilities (S-D-036, closes S-L-008).

The pilot consent text promises patients that administrative staff cannot see
their answers or scores. `screening.view` and `screening.refer` show answers,
so granting either (any scope other than none) follows these rules:

- therapist: always allowed.
- front desk: never.
- admin: allowed when another user grants it (a second admin vouches that
  this person treats patients, and the grant is audited), or when the admin
  is the only active staff member of the clinic (a solo owner who treats
  patients). An admin can never grant it to themselves in a clinic with
  other staff.

Only changes are checked. Revoking (scope none) is always allowed, and an
override that already exists unchanged is not re-checked, so saving other
permissions for a user does not fail.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.permission import CapabilityScope
from app.enums.user import UserRole
from app.models.membership import Membership
from app.models.user import User

CLINICAL_CAPABILITIES: frozenset[str] = frozenset({"screening.view", "screening.refer"})
STAFF_ROLES = (UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK)


def _deny(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": code, "message": message})


async def active_staff_count(db: AsyncSession, clinic_id: uuid.UUID) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(Membership)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.clinic_id == clinic_id,
                Membership.role.in_(STAFF_ROLES),
                User.is_active.is_(True),
            )
        )
    ) or 0


def clinical_grants(requested: Iterable, existing: Iterable) -> list[str]:
    """Capability keys this request newly grants (or widens) for clinical data."""
    before = {e.capability_key: CapabilityScope(e.scope) for e in existing}
    out = []
    for p in requested:
        if p.capability_key not in CLINICAL_CAPABILITIES:
            continue
        scope = CapabilityScope(p.scope)
        if scope == CapabilityScope.NONE or before.get(p.capability_key) == scope:
            continue
        out.append(p.capability_key)
    return sorted(out)


async def check_clinical_grant(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    target_id: uuid.UUID,
    target_role: UserRole | str | None,
    requested: Iterable,
    existing: Iterable,
) -> None:
    """Raise 403 when the request would give clinical screening access to the wrong person."""
    keys = clinical_grants(list(requested), list(existing))
    if not keys:
        return
    role = UserRole(target_role) if target_role is not None else None
    if role == UserRole.THERAPIST:
        return
    if role == UserRole.ADMIN:
        if actor_id != target_id:
            return
        if await active_staff_count(db, clinic_id) == 1:
            return
        raise _deny(
            "SCREENING_SELF_GRANT",
            "You cannot give yourself access to screening results. Another admin can, "
            "if you treat patients.",
        )
    raise _deny(
        "SCREENING_CLINICAL_ROLE",
        "Screening results can only be shown to treating providers, not to front desk staff.",
    )
