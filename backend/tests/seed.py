import sys
import os
import asyncio
from datetime import datetime, timezone, date
import uuid

# Add backend directory to Python path so app.* modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.enums.user import UserRole
from app.enums.shared import Gender
from app.enums.lead import LeadStage, LeadSource
from app.models.clinic import Clinic, ClinicPlanTier
from app.models.user import User
from app.models.patient import Patient
from app.models.treatment import TreatmentSession
from app.models.exercise import Exercise
from app.models.lead import Lead

ALL_DATA_TABLES = [
    "audit_logs",
    "patient_documents",
    "payments",
    "invoice_items",
    "invoices",
    "patient_packages",
    "packages",
    "soap_assessments",
    "treatment_sessions",
    "appointment_requests",
    "appointments",
    "leads",
    "posture_measurements",
    "posture_sessions",
    "prescription_items",
    "prescriptions",
    "exercises",
    "patients",
    "user_permissions",
    "users",
    "clinics",
]


async def wipe_database(session):
    """Wipes all business and CRM data while keeping schema and migrations intact."""
    tables_list = ", ".join(f'"{table}"' for table in ALL_DATA_TABLES)
    print("Wiping all existing database records...")
    await session.execute(text(f"TRUNCATE TABLE {tables_list} CASCADE;"))
    await session.commit()
    print("Database wiped successfully.")


async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Wipe whole database
        await wipe_database(session)

        print("Seeding fresh data (2 Clinics, Admins, Therapists, Leads, Exercises, Treatments)...")

        # 2. Create 2 Clinics
        clinics = []
        for i in range(1, 3):
            clinic = Clinic(
                id=uuid.uuid4(),
                name=f"AV Suite Clinic {i}",
                branding_logo_url=f"https://logo.example.com/clinic{i}.png",
                branding_color="#0d9488" if i == 1 else "#2563eb",
                plan_tier=ClinicPlanTier.clinical_pro,
                is_partner_clinic=True,
                is_documents_enabled=True,
            )
            session.add(clinic)
            clinics.append(clinic)

        await session.commit()

        # 3. For each clinic, add Users (Admin, Therapists), Leads, Exercises, Treatments
        for idx, clinic in enumerate(clinics, start=1):
            # Admin User
            admin = User(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                email=f"admin{idx}@clinic.com",
                password_hash=get_password_hash("password123"),
                first_name=f"Admin{idx}",
                last_name="User",
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)

            # Therapists
            therapists = []
            for t_num in range(1, 3):
                therapist = User(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    email=f"therapist{idx}_{t_num}@clinic.com",
                    password_hash=get_password_hash("password123"),
                    first_name=f"Therapist{t_num}",
                    last_name=f"Clinic{idx}",
                    role=UserRole.THERAPIST,
                    is_active=True,
                )
                session.add(therapist)
                therapists.append(therapist)

            # Front Desk
            front_desk = User(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                email=f"frontdesk{idx}@clinic.com",
                password_hash=get_password_hash("password123"),
                first_name=f"FrontDesk{idx}",
                last_name="User",
                role=UserRole.FRONT_DESK,
                is_active=True,
            )
            session.add(front_desk)

            await session.flush()

            # Leads
            leads_data = [
                ("Aarav Sharma", f"987654321{idx}", f"aarav{idx}@example.com", LeadSource.WEBSITE, LeadStage.NEW, "Inquired about shoulder rehabilitation."),
                ("Diya Patel", f"987654322{idx}", f"diya{idx}@example.com", LeadSource.WALK_IN, LeadStage.CONTACTED, "Walk-in consultation for posture correction."),
                ("Rohan Mehta", f"987654323{idx}", f"rohan{idx}@example.com", LeadSource.REFERRAL, LeadStage.QUALIFIED, "Referred by Dr. Verma for knee rehab."),
            ]
            for name, phone, email, source, stage, notes in leads_data:
                lead = Lead(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    name=name,
                    phone=phone,
                    email=email,
                    source=source,
                    stage=stage,
                    assigned_to=therapists[0].id,
                    notes=notes,
                )
                session.add(lead)

            # Exercises
            exercises_data = [
                ("Shoulder External Rotation", "Rotate shoulder outward with resistance band", "Shoulder", "https://example.com/video/shoulder-rot.mp4"),
                ("Cervical Retraction (Chin Tucks)", "Gently pull head straight back keeping eyes level", "Neck", "https://example.com/video/chin-tuck.mp4"),
                ("Wall Angels", "Slide arms along wall maintaining back and elbow contact", "Upper Back", "https://example.com/video/wall-angels.mp4"),
                ("Hamstring Stretch", "Hold seated forward reach for 30 seconds", "Legs", "https://example.com/video/hamstring.mp4"),
            ]
            for title, description, body_part, video_url in exercises_data:
                exercise = Exercise(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    title=title,
                    description=description,
                    body_part=body_part,
                    is_free=True,
                    video_url=video_url,
                )
                session.add(exercise)

            await session.flush()

            # Base patient required to link treatment sessions
            patient = Patient(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                first_name=f"Patient{idx}",
                last_name="Sample",
                date_of_birth=date(1992, 5, 15),
                phone=f"912345678{idx}",
                age=34,
                gender=Gender.MALE if idx == 1 else Gender.FEMALE,
                chief_complaint="Persistent lower back pain after desk work",
                referral_source="Online Search",
                status="active",
            )
            session.add(patient)
            await session.flush()

            # Treatments
            treatments_data = [
                ("Initial Assessment & Lumbar Mobilization", "Perform gentle lumbar extensions twice daily. Avoid prolonged sitting.", 6, "Patient demonstrated 30% limited lumbar flexion with mild tenderness."),
                ("Follow-up Core Activation & Posture Correction", "Continue chin tucks and pelvic tilts 3x daily.", 3, "Significant improvement in lumbar mobility and reduced pain score."),
            ]
            for treat_name, advice, pain, notes in treatments_data:
                treatment = TreatmentSession(
                    id=uuid.uuid4(),
                    clinic_id=clinic.id,
                    patient_id=patient.id,
                    appointment_id=None,
                    therapist_id=therapists[0].id,
                    treatment_date=datetime.now(timezone.utc),
                    pain_score=pain,
                    treatment=treat_name,
                    home_advice=advice,
                    notes=notes,
                    finalized=True,
                )
                session.add(treatment)

        await session.commit()
        print("Database successfully wiped and freshly seeded!")
        print("\n=== Available Logins (Password for all: password123) ===")
        print("Clinic 1 (AV Suite Clinic 1):")
        print("  - Admin:      admin1@clinic.com")
        print("  - Therapist:  therapist1_1@clinic.com")
        print("  - Therapist:  therapist1_2@clinic.com")
        print("  - Front Desk: frontdesk1@clinic.com")
        print("Clinic 2 (AV Suite Clinic 2):")
        print("  - Admin:      admin2@clinic.com")
        print("  - Therapist:  therapist2_1@clinic.com")
        print("  - Therapist:  therapist2_2@clinic.com")
        print("  - Front Desk: frontdesk2@clinic.com")


if __name__ == "__main__":
    asyncio.run(seed())
