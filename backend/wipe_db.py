import asyncio
import asyncpg
import os
from urllib.parse import urlparse

DATABASE_URL = "postgresql://postgres.vlupywockwfvcduaiwrn:AZ%5EEYQa%24khCa1MCKvUvf@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

async def wipe_db():
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    print("Dropping public schema...")
    await conn.execute('DROP SCHEMA public CASCADE;')
    print("Recreating public schema...")
    await conn.execute('CREATE SCHEMA public;')
    await conn.execute('GRANT ALL ON SCHEMA public TO postgres;')
    await conn.execute('GRANT ALL ON SCHEMA public TO public;')
    print("Database wiped successfully.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(wipe_db())
