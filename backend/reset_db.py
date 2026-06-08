import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.models.base import Base

async def reset_db():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # Drop all tables including alembic_version
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        print("Database wiped clean!")
        print("Database reset and tables recreated!")

if __name__ == "__main__":
    asyncio.run(reset_db())
