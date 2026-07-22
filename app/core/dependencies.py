from __future__ import annotations

from collections.abc import AsyncGenerator
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.clinic import Clinic
from app.enums.user import UserRole, normalize_user_role
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for route dependencies."""

    async for session in get_db():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]

RoleDependency = Callable[..., Awaitable[User]]


@dataclass(slots=True)
class AuthenticatedContext:
    """Authenticated request identity resolved from the access token."""

    user: User
    clinic: Clinic


def _require_user_roles(current_user: User, roles: tuple[UserRole, ...]) -> User:
    """Ensure the authenticated user has one of the allowed roles."""

    if current_user.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    return current_user


async def get_authenticated_context(token: TokenDep, session: SessionDep) -> AuthenticatedContext:
    """Resolve the authenticated user and clinic from an access token."""


    try:
        claims = decode_access_token(token)
        user_id = UUID(claims["user_id"])
        clinic_id = UUID(claims["clinic_id"])
        role = normalize_user_role(claims["role"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.clinic_id != clinic_id or user.role != role or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clinic = await session.get(Clinic, clinic_id)
    if clinic is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedContext(user=user, clinic=clinic)


AuthenticatedContextDep = Annotated[AuthenticatedContext, Depends(get_authenticated_context)]


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

    async def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        """Validate role membership for the authenticated user."""

        return _require_user_roles(current_user, roles)

    return dependency


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require the authenticated user to have the admin role."""

    return _require_user_roles(current_user, (UserRole.ADMIN,))


async def require_therapist(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require the authenticated user to have the therapist role."""

    return _require_user_roles(current_user, (UserRole.THERAPIST,))


async def require_front_desk(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require the authenticated user to have the front desk role."""

    return _require_user_roles(current_user, (UserRole.FRONT_DESK,))
