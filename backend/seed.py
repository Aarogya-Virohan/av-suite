import asyncio
from datetime import datetime, timezone
import uuid
import sys

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.treatment import TreatmentSession
from app.models.exercise import Exercise

async def seed():
    async with AsyncSessionLocal() as session:
        # Create 3 Clinics
        clinics = []
        for i in range(1, 4):
            clinic = Clinic(
                id=uuid.uuid4(),
                name=f"Av Suite Clinic {i}"
            )
            session.add(clinic)
            clinics.append(clinic)
        
        await session.commit()
        
        # Create Users, Patients, Exercises, and Treatments for each clinic
        for idx, clinic in enumerate(clinics, start=1):
            # 1. Users (Admin, Therapist, Front Desk)
            admin = User(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                email=f"admin{idx}@clinic.com",
                password_hash=get_password_hash("password123"),
                first_name="Admin",
                last_name="User",
                role=UserRole.ADMIN,
                is_active=True,
            )
            therapist = User(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                email=f"therapist{idx}@clinic.com",
                password_hash=get_password_hash("password123"),
                first_name="Therapist",
                last_name="User",
                role=UserRole.THERAPIST,
                is_active=True,
            )
            front_desk = User(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                email=f"frontdesk{idx}@clinic.com",
                password_hash=get_password_hash("password123"),
                first_name="FrontDesk",
                last_name="User",
                role=UserRole.FRONT_DESK,
                is_active=True,
            )
            
            session.add_all([admin, therapist, front_desk])
            
            # 2. Patients (3 patients)
            # Patient 1 - Assigned to therapist (via treatment)
            # Patient 2 - Assigned to therapist (via treatment)
            # Patient 3 - Unassigned (to test "own" vs "all" access)
            patients = []
            patient_first_names = ["Alice", "Bob", "Charlie"]
            for j in range(1, 4):
                patient = Patient(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    first_name=patient_first_names[j-1],
                    last_name="Smith",
                    date_of_birth=datetime(1990, 1, 1).date(),
                    phone=f"123456789{j}"
                )
                session.add(patient)
                patients.append(patient)
            
            # 3. Exercises
            for k in range(1, 3):
                exercise = Exercise(
                    id=uuid.uuid4(),
                    title=f"Exercise {k} for {clinic.name}",
                    description="Standard exercise",
                    clinic_id=clinic.id
                )
                session.add(exercise)
                
            await session.flush()
            
            # 4. Link patients 1 and 2 to the therapist so they are "own"
            for patient in patients[:2]:
                treatment = TreatmentSession(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    patient_id=patient.id,
                    therapist_id=therapist.id,
                    treatment_date=datetime.now(timezone.utc),
                    treatment="Initial Assessment",
                    finalized=True
                )
                session.add(treatment)
                
        await session.commit()
        print("Data seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
