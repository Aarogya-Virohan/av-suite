import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models.base import Base

async def setup():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        print("Recreating tables from Base...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables recreated successfully!")

if __name__ == "__main__":
    asyncio.run(setup())
