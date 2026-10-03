import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.enums.user import UserRole

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalars().first()
        if user:
            print(f"user.role type: {type(user.role)}")
            print(f"user.role: {repr(user.role)}")
            print(f"UserRole.ADMIN: {repr(UserRole.ADMIN)}")
            print(f"user.role == UserRole.ADMIN: {user.role == UserRole.ADMIN}")

if __name__ == "__main__":
    asyncio.run(main())
