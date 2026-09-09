import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/av_suite")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalars().first()
        print(f"User: {user.email}, Role: {user.role}")

asyncio.run(main())
