from __future__ import annotations

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse


class AuthenticationError(Exception):
    """Raised when login credentials cannot be authenticated."""


class AuthService:
    """Authentication service for issuing clinic-scoped JWTs."""

    user_repository: UserRepository

    def __init__(self, user_repository: UserRepository) -> None:
        """Store repositories required for authentication."""

        self.user_repository = user_repository

    async def authenticate_user(self, request: LoginRequest) -> User:
        """Return the authenticated active user for the provided credentials."""

        user = await self.user_repository.get_by_email(request.email)
        if user is None or not user.is_active or not verify_password(request.password, user.password_hash):
            raise AuthenticationError("Incorrect email or password")

        return user

    def create_token_for_user(self, user: User) -> TokenResponse:
        """Create a JWT token response for an authenticated user."""

        access_token = create_access_token(
            user_id=user.id,
            clinic_id=user.clinic_id,
            role=user.role,
        )
        return TokenResponse(access_token=access_token)

    async def login(self, request: LoginRequest) -> TokenResponse:
        """Authenticate credentials and return a bearer token response."""

        user = await self.authenticate_user(request)
        return self.create_token_for_user(user)
