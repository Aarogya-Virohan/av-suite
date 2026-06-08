import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def create_dummy_patient():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # Get the clinic ID
        result = await conn.execute(text("SELECT id FROM clinics LIMIT 1"))
        clinic_row = result.fetchone()
        if not clinic_row:
            print("No clinic found!")
            return
        clinic_id = clinic_row[0]
        
        # Insert patient
        patient_id = "00000000-0000-0000-0000-000000000000"
        
        # Check if exists
        res = await conn.execute(text("SELECT id FROM patients WHERE id = :id"), {"id": patient_id})
        if res.fetchone():
            print("Patient already exists")
            return
            
        await conn.execute(
            text("""
                INSERT INTO patients (id, clinic_id, first_name, last_name, phone, date_of_birth)
                VALUES (:id, :clinic_id, 'Dummy', 'Patient', '1234567890', '1990-01-01')
            """),
            {"id": patient_id, "clinic_id": clinic_id}
        )
        print("Dummy patient created!")

if __name__ == "__main__":
    asyncio.run(create_dummy_patient())
