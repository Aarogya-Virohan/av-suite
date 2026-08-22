import sys
import os
# Add backend directory to Python path so app.* modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

"""
Seed Script for AV Suite CRM
============================
This script is used to populate the local or remote database with robust dummy data.
It should primarily be used for testing and local development.

What this file does:
1. Connects to the database using SQLAlchemy async session.
2. Uses the Supabase client to upload a dummy PDF document to the 'documents' storage bucket.
3. Seeds the following entities with complete data (filling all required and optional columns):
   - Clinics (with 'clinical_pro' tier and documents enabled)
   - Users (Admins, Therapists, Front Desk roles)
   - Leads (Includes stage, source, and assignment tracking)
   - Patients (Includes age, gender, exact 10-digit phone, and chief complaints)
   - Exercises (Includes body_part and video URL placeholders)
   - Treatment Sessions (Includes pain_score and home_advice)
   - Patient Documents (Links the uploaded Supabase bucket file URLs to the patient's record)

Usage:
    cd backend
    python tests/seed.py
"""

import asyncio
from datetime import datetime, timezone, date
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.enums.user import UserRole
from app.enums.shared import Gender
from app.enums.document import DocumentCategory
from app.enums.lead import LeadStage, LeadSource
from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.treatment import TreatmentSession
from app.models.exercise import Exercise
from app.models.lead import Lead
from app.models.document import PatientDocument
from app.core.config import settings

from supabase import create_client, Client

async def seed():
    # Setup Supabase client for bucket operations
    supabase_url = settings.SUPABASE_URL
    supabase_key = settings.SUPABASE_SECRET_KEY
    supabase: Client = create_client(supabase_url, supabase_key)

    async with AsyncSessionLocal() as session:
        # Create 3 Clinics
        clinics = []
        for i in range(1, 4):
            clinic = Clinic(
                id=uuid.uuid4(),
                name=f"Av Suite Clinic {i}",
                branding_logo_url=f"https://logo.example.com/clinic{i}.png",
                branding_color="#000000",
                plan_tier="clinical_pro",
                is_partner_clinic=True,
                is_documents_enabled=True
            )
            session.add(clinic)
            clinics.append(clinic)
        
        await session.commit()
        
        # Add Users, Patients, Leads, Exercises, Treatments for each clinic
        for idx, clinic in enumerate(clinics, start=1):
            users_to_add = []
            
            # Admins
            for a in range(1, 3):
                users_to_add.append(User(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    email=f"admin{idx}_{a}@clinic.com",
                    password_hash=get_password_hash("password123"),
                    first_name=f"Admin{a}",
                    last_name="User",
                    role=UserRole.ADMIN,
                    is_active=True,
                ))

            # Therapists
            for t in range(1, 4):
                users_to_add.append(User(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    email=f"therapist{idx}_{t}@clinic.com",
                    password_hash=get_password_hash("password123"),
                    first_name=f"Therapist{t}",
                    last_name="User",
                    role=UserRole.THERAPIST,
                    is_active=True,
                ))

            # Front Desk
            for f in range(1, 3):
                users_to_add.append(User(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    email=f"frontdesk{idx}_{f}@clinic.com",
                    password_hash=get_password_hash("password123"),
                    first_name=f"FrontDesk{f}",
                    last_name="User",
                    role=UserRole.FRONT_DESK,
                    is_active=True,
                ))
            
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
            users_to_add.extend([admin, therapist, front_desk])
            
            session.add_all(users_to_add)
            
            # Leads
            leads = []
            lead_names = ["John Doe", "Jane Roe", "Alice Foo"]
            for j in range(1, 4):
                lead = Lead(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    name=lead_names[j-1],
                    phone=f"987654321{j}",
                    email=f"lead{j}@clinic{idx}.com",
                    source=LeadSource.WEBSITE,
                    stage=LeadStage.NEW,
                    assigned_to=front_desk.id,
                    notes=f"Interested in initial assessment."
                )
                session.add(lead)
                leads.append(lead)

            # Patients
            patients = []
            patient_first_names = ["Alice", "Bob", "Charlie"]
            for j in range(1, 4):
                patient = Patient(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    user_id=None,
                    first_name=patient_first_names[j-1],
                    last_name="Smith",
                    date_of_birth=date(1990, 1, 1),
                    phone=f"123456789{j}",
                    age=36,
                    gender=Gender.MALE if j % 2 == 0 else Gender.FEMALE,
                    chief_complaint="Lower back pain" if j == 1 else "Neck stiffness",
                    referral_source="Google Search",
                    status="active"
                )
                session.add(patient)
                patients.append(patient)
            
            # Exercises
            for k in range(1, 3):
                exercise = Exercise(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    title=f"Exercise {k} for {clinic.name}",
                    description="Standard exercise for rehabilitation.",
                    body_part="Shoulder" if k == 1 else "Knee",
                    is_free=True,
                    video_url="https://example.com/video.mp4"
                )
                session.add(exercise)
                
            await session.flush()
            
            # Treatments & Documents
            for p_idx, patient in enumerate(patients[:2]):
                treatment = TreatmentSession(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    patient_id=patient.id,
                    appointment_id=None,
                    therapist_id=therapist.id,
                    treatment_date=datetime.now(timezone.utc),
                    pain_score=7,
                    treatment="Initial Assessment",
                    home_advice="Rest and apply ice.",
                    notes="Patient showed restricted range of motion.",
                    finalized=True
                )
                session.add(treatment)
                
                # Upload Dummy Document to Supabase
                file_path = f"{clinic.id}/{patient.id}/dummy_record_{p_idx}.pdf"
                dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Dummy) >>\nendobj\n"
                
                try:
                    res = supabase.storage.from_("documents").upload(
                        file=dummy_pdf_content,
                        path=file_path,
                        file_options={"content-type": "application/pdf", "upsert": "true"}
                    )
                except Exception as e:
                    print(f"Bucket upload failed: {e}")
                
                # Create Patient Document in DB
                doc = PatientDocument(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    patient_id=patient.id,
                    uploaded_by=therapist.id,
                    treatment_id=treatment.id,
                    file_url=file_path,
                    file_type="application/pdf",
                    file_size=len(dummy_pdf_content),
                    label=f"Medical Record {p_idx+1}",
                    category=DocumentCategory.MEDICAL_REPORT,
                    notes="Auto-generated during seed."
                )
                session.add(doc)

        await session.commit()
        print("Data and bucket seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
