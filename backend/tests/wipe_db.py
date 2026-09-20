import sys
import os
# Add backend directory to Python path so app.* modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Database and Bucket Wipe Script for AV Suite CRM
================================================
This script is a destructive utility used to cleanly tear down the testing environment.

What this file does:
1. Connects directly to the PostgreSQL database via asyncpg.
2. Queries the `patient_documents` table to find all active file URLs that were uploaded to Supabase.
3. Uses the Supabase storage client to delete those specific dummy files from the 'documents' bucket, preventing orphaned files.
4. Drops the 'public' schema using CASCADE, which deletes all tables, data, and custom ENUM types.
5. Recreates a pristine, empty 'public' schema.

Usage:
    cd backend
    python tests/wipe_db.py

Note: You must run `alembic upgrade head` after running this script to recreate the tables before seeding again.
"""

import asyncio
import asyncpg
from supabase import create_client, Client
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL.replace('+asyncpg', '')

async def wipe_db():
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    # We first retrieve all files to delete from the PatientDocument table
    print("Fetching files to wipe from the Supabase bucket...")
    try:
        # Fetch file_urls that exist in the documents table
        rows = await conn.fetch("SELECT file_url FROM patient_documents WHERE file_url IS NOT NULL")
        files_to_delete = [row['file_url'] for row in rows]
        
        if files_to_delete:
            supabase_url = settings.SUPABASE_URL
            supabase_key = settings.SUPABASE_SECRET_KEY
            supabase: Client = create_client(supabase_url, supabase_key)
            
            print(f"Deleting {len(files_to_delete)} files from Supabase 'documents' bucket...")
            try:
                res = supabase.storage.from_("documents").remove(files_to_delete)
                print("Bucket wiped successfully.")
            except Exception as e:
                print(f"Bucket wipe warning/error: {e}")
        else:
            print("No files found in DB to delete from bucket.")
    except Exception as e:
        print(f"Could not fetch patient documents: {e}")

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
