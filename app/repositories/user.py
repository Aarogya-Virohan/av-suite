from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):  # pyright: ignore[reportInvalidTypeArguments] - SQLAlchemy Mapped primary keys satisfy the repository contract at runtime.
    """Repository for clinic-scoped users."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a user repository bound to the active session."""

        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email address."""

        result = await self.session.scalars(select(User).where(User.email == email))
        return result.one_or_none()
