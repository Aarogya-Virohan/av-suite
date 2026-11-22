from __future__ import annotations

from collections.abc import AsyncGenerator
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address from Cloudflare or reverse proxy headers.
    Checks:
    1. CF-Connecting-IP (injected by Cloudflare edge)
    2. X-Forwarded-For (first IP in proxy chain)
    3. request.client.host (direct connection fallback)
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


from sqlalchemy import select

from app.core.database import get_db
from app.core.products import product_for_capability
from app.core.rbac import resolve_capability_scope
from app.core.security import decode_token
from app.enums.permission import CapabilityScope
from app.enums.organization import ClinicStatus, OrganizationStatus
from app.exceptions import ProductNotEntitledError, WorkspaceSuspendedError
from app.models.clinic import Clinic
from app.enums.user import UserRole
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission
from app.services.product_entitlements import active_entitlement_clause

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_async_session(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for route dependencies."""
    yield session


SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]

RoleDependency = Callable[..., Awaitable[User]]


@dataclass(slots=True)
class AuthenticatedContext:
    """Authenticated request identity resolved from the access token."""

    user: User
    clinic: Clinic
    membership: Membership

    @property
    def membership_role(self) -> UserRole:
        """Return the role assigned in the active workspace membership."""
        return self.membership.role


@dataclass(slots=True)
class PermissionContext:
    """Request-level permission context caching capability overrides."""

    user: User
    clinic: Clinic
    membership: Membership
    overrides: dict[str, CapabilityScope] | None = None
    enabled_product_ids: set[str] | None = None

    def effective_scope(self, capability_key: str) -> CapabilityScope:
        """Resolve the effective scope for a capability using cached overrides."""
        return resolve_capability_scope(
            role=self.membership.role,
            capability_key=capability_key,
            user_permissions=self.overrides or {},
        )

    def is_product_entitled(self, product_id: str) -> bool:
        """Return whether the active workspace has an enabled product entitlement."""
        return product_id in (self.enabled_product_ids or set())


def _require_user_roles(
    current_user: User, effective_role: UserRole, roles: tuple[UserRole, ...]
) -> User:
    """Ensure the authenticated user has one of the allowed roles."""

    if effective_role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    return current_user


async def get_authenticated_context(
    token: TokenDep, session: SessionDep
) -> AuthenticatedContext:
    """Resolve the authenticated user and active workspace membership from an access token."""

    try:
        claims = decode_token(token)
        user_id = UUID(str(claims["sub"]))
        clinic_id = UUID(str(claims["clinic_id"]))
    except (PyJWTError, ValueError, KeyError, TypeError) as exc:
        # AUD-02 / L-47: expired, bad-signature or garbage tokens are 401,
        # never 500, so the frontends can send the user back to login.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials clinic mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is None",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clinic = await session.get(Clinic, clinic_id)
    if clinic is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clinic is None",
            headers={"WWW-Authenticate": "Bearer"},
        )

    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.clinic_id == clinic.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this clinic/workspace",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if clinic.status != ClinicStatus.ACTIVE:
        raise WorkspaceSuspendedError("clinic")
    organization = await session.get(Organization, clinic.organization_id)
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise WorkspaceSuspendedError("organization")

    return AuthenticatedContext(user=user, clinic=clinic, membership=membership)


AuthenticatedContextDep = Annotated[
    AuthenticatedContext, Depends(get_authenticated_context)
]


async def get_permission_context(
    auth_context: AuthenticatedContextDep,
    session: SessionDep,
) -> PermissionContext:
    """Load explicit capability overrides once per request."""

    from sqlalchemy import select

    stmt = select(UserPermission).where(
        UserPermission.user_id == auth_context.user.id,
        UserPermission.clinic_id == auth_context.clinic.id,
    )
    result = await session.execute(stmt)
    overrides = {p.capability_key: p.scope for p in result.scalars()}

    product_stmt = select(WorkspaceProduct).where(
        WorkspaceProduct.clinic_id == auth_context.clinic.id,
        active_entitlement_clause(datetime.now(timezone.utc)),
    )
    product_result = await session.execute(product_stmt)
    enabled_product_ids = {
        entitlement.product_id for entitlement in product_result.scalars()
    }

    return PermissionContext(
        user=auth_context.user,
        clinic=auth_context.clinic,
        membership=auth_context.membership,
        overrides=overrides,
        enabled_product_ids=enabled_product_ids,
    )


PermissionContextDep = Annotated[PermissionContext, Depends(get_permission_context)]


def require_capability(capability_key: str) -> Callable[..., CapabilityScope]:
    """Dependency that enforces a capability check using the request context."""

    def dependency(perm_ctx: PermissionContextDep) -> CapabilityScope:
        product_id = product_for_capability(capability_key)
        if product_id is not None and not perm_ctx.is_product_entitled(product_id):
            raise ProductNotEntitledError(capability_key, product_id)

        scope = perm_ctx.effective_scope(capability_key)
        if scope == CapabilityScope.NONE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required capability: {capability_key}",
            )
        return scope

    return dependency


async def get_current_user(
    auth_context: AuthenticatedContextDep,
) -> User:
    """Return the authenticated user resolved from the access token."""

    return auth_context.user


async def get_current_clinic(
    auth_context: AuthenticatedContextDep,
) -> Clinic:
    """Return the authenticated clinic for the current user."""

    return auth_context.clinic


def require_roles(*roles: UserRole) -> RoleDependency:
    """Return a dependency that requires any of the specified roles."""

    async def dependency(auth_context: AuthenticatedContextDep) -> User:
        """Validate the active workspace membership role for the authenticated user."""

        effective_role = auth_context.membership_role
        if effective_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return auth_context.user

    return dependency


async def require_admin(
    auth_context: AuthenticatedContextDep,
) -> User:
    """Require the authenticated user to have the admin role."""

    return _require_user_roles(
        auth_context.user, auth_context.membership_role, (UserRole.ADMIN,)
    )


async def require_therapist(
    auth_context: AuthenticatedContextDep,
) -> User:
    """Require the authenticated user to have the therapist role."""

    return _require_user_roles(
        auth_context.user, auth_context.membership_role, (UserRole.THERAPIST,)
    )


async def require_front_desk(
    auth_context: AuthenticatedContextDep,
) -> User:
    """Require the authenticated user to have the front desk role."""

    return _require_user_roles(
        auth_context.user, auth_context.membership_role, (UserRole.FRONT_DESK,)
    )


async def get_platform_operator(token: TokenDep, session: SessionDep, request: Request):
    """Authenticate only AV platform tokens; clinic identities never cross this boundary."""
    import jwt
    from app.core.config import settings
    from app.exceptions import BaseAppException
    from app.models.platform import PlatformOperator

    try:
        claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], audience="av-platform", options={"require": ["sub", "aud", "typ", "ver", "exp"]})
        if claims.get("typ") != "platform":
            raise jwt.InvalidTokenError("Wrong token type")
        operator_id = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
        raise BaseAppException("Unauthorized", "UNAUTHORIZED", 401) from exc

    operator = await session.get(PlatformOperator, operator_id)
    if operator is None or not operator.is_active or claims.get("ver") != operator.token_version:
        raise BaseAppException("Unauthorized", "UNAUTHORIZED", 401)
    request.state.platform_operator_token_version = claims["ver"]
    return operator
