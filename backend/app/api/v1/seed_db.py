import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import uuid

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.lead import Lead
from app.enums.user import UserRole


async def seed():
    print("Tip: run `alembic upgrade head` first; it also seeds demo login data.")
    print("Connecting to database...")
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        print("Wiping existing data...")
        # TRUNCATE CASCADE will delete data from all tables that reference clinics, which is almost everything
        await conn.execute(text("TRUNCATE clinics CASCADE"))

    async with async_session() as session:
        print("Creating clinic...")
        clinic_id = uuid.uuid4()
        clinic = Clinic(
            id=clinic_id,
            name="Aarogya Virohan Demo Clinic",
            branding_color="#008080",
            plan_tier="clinical_pro",
            is_partner_clinic=True,
        )
        session.add(clinic)

        print("Creating users...")
        password_hash = get_password_hash("Password123!")

        # Admin
        admin = User(
            clinic_id=clinic_id,
            email="admin@avtest.com",
            password_hash=password_hash,
            role=UserRole.ADMIN,
            first_name="Admin",
            last_name="User",
            phone="9876543211",
            is_active=True,
        )

        # Front Desk
        frontdesk = User(
            clinic_id=clinic_id,
            email="frontdesk@avtest.com",
            password_hash=password_hash,
            role=UserRole.FRONT_DESK,
            first_name="Front",
            last_name="Desk",
            phone="9876543212",
            is_active=True,
        )

        # Therapist
        therapist_id = uuid.uuid4()
        therapist = User(
            id=therapist_id,
            clinic_id=clinic_id,
            email="therapist@avtest.com",
            password_hash=password_hash,
            role=UserRole.THERAPIST,
            first_name="Main",
            last_name="Therapist",
            phone="9876543213",
            is_active=True,
        )

        session.add_all([admin, frontdesk, therapist])
        await session.flush()

        print("Creating fake data (leads, patients, appointments)...")
        # Leads
        lead1 = Lead(
            clinic_id=clinic_id,
            name="John Prospect",
            phone="9000000001",
            source="Facebook",
            stage="new",
        )

        # Patients
        patient_id_1 = uuid.uuid4()
        patient1 = Patient(
            id=patient_id_1,
            clinic_id=clinic_id,
            first_name="Alice",
            last_name="Patient",
            phone="9000000002",
            age=30,
            gender="Female",
            chief_complaint="Lower back pain",
            status="active",
        )

        patient_id_2 = uuid.uuid4()
        patient2 = Patient(
            id=patient_id_2,
            clinic_id=clinic_id,
            first_name="Bob",
            last_name="Patient",
            phone="9000000003",
            age=45,
            gender="Male",
            chief_complaint="Shoulder injury",
            status="active",
        )

        session.add_all([lead1, patient1, patient2])
        await session.flush()

        # Appointments
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        appt1 = Appointment(
            clinic_id=clinic_id,
            patient_id=patient_id_1,
            therapist_id=therapist_id,
            scheduled_at=tomorrow.replace(hour=10, minute=0, second=0, microsecond=0),
            duration_minutes=45,
            status="scheduled",
            source="manual",
        )

        appt2 = Appointment(
            clinic_id=clinic_id,
            patient_id=patient_id_2,
            therapist_id=therapist_id,
            scheduled_at=tomorrow.replace(hour=14, minute=0, second=0, microsecond=0),
            duration_minutes=30,
            status="scheduled",
            source="manual",
        )

        session.add_all([appt1, appt2])

        await session.commit()
        print("✅ Database successfully wiped and seeded with fake data!")
        print("\n--- TEST ACCOUNTS ---")
        print("1. Admin:       admin@avtest.com")
        print("2. Front Desk:  frontdesk@avtest.com")
        print("3. Therapist:   therapist@avtest.com")
        print("Password for all: Password123!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
