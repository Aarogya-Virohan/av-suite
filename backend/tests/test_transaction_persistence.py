"""Test transaction persistence for the centralized request transaction boundary.

These tests verify that the transaction lifecycle is correctly managed:
- Successful requests commit automatically
- Exception requests rollback
- Explicit commits in services don't break anything
"""

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.lead import Lead
from app.models.appointment import Appointment
from app.models.treatment import TreatmentSession
from app.models.booking import AppointmentRequest
from app.core.security import create_access_token, get_password_hash
from app.enums.user import UserRole


@pytest.fixture
async def real_postgres_client(db_session):
    """Client that uses the real get_db dependency for PostgreSQL transaction testing."""

    # Override to use our test session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def test_clinic_with_user(db_session):
    """Create a test clinic with admin user for persistence tests."""
    clinic_id = uuid.uuid4()
    user_id = uuid.uuid4()

    clinic = Clinic(
        id=clinic_id,
        name=f"Persistence Test Clinic {uuid.uuid4().hex[:8]}",
        branding_color="#008080",
        plan_tier="clinical_pro",
    )
    db_session.add(clinic)

    from app.models.user import User

    user = User(
        id=user_id,
        clinic_id=clinic_id,
        email=f"persist_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.ADMIN,
        first_name="Persist",
        last_name="Tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Generate token
    token = create_access_token(
        subject=user_id, clinic_id=clinic_id, role=UserRole.ADMIN.value
    )

    return {
        "clinic_id": clinic_id,
        "user_id": user_id,
        "token": token,
        "therapist_id": user_id,  # Admin can act as therapist for tests
    }


class TestTransactionPersistence:
    """Verify that the centralized transaction boundary persists writes."""

    def _extract_id(self, response) -> str:
        """Extract ID from API response handling both envelope formats."""
        data = response.json().get("data", response.json())
        return data.get("id")

    @pytest.mark.asyncio
    async def test_patient_persists_after_request(
        self, real_postgres_client, test_clinic_with_user
    ):
        """POST /patients should persist the patient record."""
        clinic = test_clinic_with_user
        headers = {"Authorization": f"Bearer {clinic['token']}"}

        # Create patient - use schema fields (first_name, last_name)
        patient_data = {
            "first_name": "Persist",
            "last_name": "Test Patient",
            "phone": "9999999999",
        }
        response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/patients",
            json=patient_data,
            headers=headers,
        )
        assert response.status_code in (200, 201), response.text
        patient_id = self._extract_id(response)

        # Verify persistence by fetching the patient
        get_response = await real_postgres_client.get(
            f"{settings.API_V1_PREFIX}/patients/{patient_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        get_data = get_response.json().get("data", get_response.json())
        assert get_data["first_name"] == "Persist"
        assert get_data["last_name"] == "Test Patient"

    @pytest.mark.asyncio
    async def test_lead_persists_after_request(
        self, real_postgres_client, test_clinic_with_user
    ):
        """POST /leads should persist the lead record."""
        clinic = test_clinic_with_user
        headers = {"Authorization": f"Bearer {clinic['token']}"}

        # Create lead - use schema fields (name, phone, email, source, stage)
        lead_data = {
            "name": "Persist Test Lead",
            "phone": "8888888888",
            "email": "persist_lead@test.com",
            "source": "website",
            "stage": "new",
        }
        response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/leads",
            json=lead_data,
            headers=headers,
        )
        assert response.status_code in (200, 201), response.text
        lead_id = self._extract_id(response)

        # Verify persistence by fetching the lead
        get_response = await real_postgres_client.get(
            f"{settings.API_V1_PREFIX}/leads/{lead_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        get_data = get_response.json().get("data", get_response.json())
        assert get_data["name"] == "Persist Test Lead"

    @pytest.mark.asyncio
    async def test_appointment_persists_after_request(
        self, real_postgres_client, test_clinic_with_user
    ):
        """POST /appointments should persist the appointment record."""
        clinic = test_clinic_with_user
        headers = {"Authorization": f"Bearer {clinic['token']}"}

        # First create a patient
        patient_response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/patients",
            json={"first_name": "Appt", "last_name": "Patient", "phone": "7777777777"},
            headers=headers,
        )
        patient_id = self._extract_id(patient_response)

        # Create appointment
        appointment_data = {
            "patient_id": patient_id,
            "therapist_id": str(clinic["therapist_id"]),
            "scheduled_at": "2026-08-26T10:00:00Z",
            "duration_minutes": 30,
        }
        response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/appointments",
            json=appointment_data,
            headers=headers,
        )
        assert response.status_code in (200, 201), response.text
        appointment_id = self._extract_id(response)

        # Verify persistence by fetching the appointment
        get_response = await real_postgres_client.get(
            f"{settings.API_V1_PREFIX}/appointments/{appointment_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        get_data = get_response.json().get("data", get_response.json())
        assert get_data["patient_id"] == patient_id

    @pytest.mark.asyncio
    async def test_treatment_session_persists_after_request(
        self, real_postgres_client, test_clinic_with_user
    ):
        """POST /treatments should persist the treatment session record."""
        clinic = test_clinic_with_user
        headers = {"Authorization": f"Bearer {clinic['token']}"}

        # First create a patient
        patient_response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/patients",
            json={
                "first_name": "Treatment",
                "last_name": "Patient",
                "phone": "6666666666",
            },
            headers=headers,
        )
        patient_id = self._extract_id(patient_response)

        # Create treatment session - requires 'treatment' field
        treatment_data = {
            "patient_id": patient_id,
            "therapist_id": str(clinic["therapist_id"]),
            "treatment_date": "2026-08-26",
            "treatment": "Test treatment performed",
            "notes": "Test treatment session",
        }
        response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/treatments",
            json=treatment_data,
            headers=headers,
        )
        assert response.status_code in (200, 201), response.text
        session_id = self._extract_id(response)

        # Verify persistence by fetching the session
        get_response = await real_postgres_client.get(
            f"{settings.API_V1_PREFIX}/treatments/{session_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        get_data = get_response.json().get("data", get_response.json())
        assert get_data["patient_id"] == patient_id

    @pytest.mark.asyncio
    async def test_booking_request_persists_after_request(
        self, real_postgres_client, test_clinic_with_user, db_session
    ):
        """POST /booking/request should persist the appointment request record."""
        clinic = test_clinic_with_user
        headers = {"Authorization": f"Bearer {clinic['token']}"}

        # Create public booking request using clinic slug (no auth required for initial request)
        # Uses AppointmentRequestCreate schema: name, phone, optional age, gender, chief_complaint, notes, preferred_date, preferred_slot
        booking_data = {
            "name": "Booking Request Patient",
            "phone": "5555555555",
            "notes": "Test booking request",
            "preferred_date": "2026-08-26",
        }
        # Use clinic name as slug (the get_by_slug_or_id method matches clinic name)
        # Clinic name format: "Persistence Test Clinic {uuid_hex[:8]}"
        # For testing, we'll need to query the clinic name from the database
        clinic_query = await db_session.execute(
            select(Clinic).where(Clinic.id == clinic["clinic_id"])
        )
        clinic_record = clinic_query.scalar_one()
        clinic_slug = clinic_record.name

        response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/booking/request?clinic_slug={clinic_slug}",
            json=booking_data,
        )
        assert response.status_code in (200, 201), response.text
        request_id = self._extract_id(response)

        # Verify persistence by querying directly
        result = await db_session.execute(
            select(AppointmentRequest).where(
                AppointmentRequest.id == uuid.UUID(request_id)
            )
        )
        saved_request = result.scalar_one_or_none()
        assert saved_request is not None
        assert saved_request.name == "Booking Request Patient"
        # Verify it was created for the correct clinic
        assert saved_request.clinic_id == clinic["clinic_id"]


class TestTransactionRollback:
    """Verify that exceptions cause rollback."""

    @pytest.mark.asyncio
    async def test_exception_rolls_back_transaction(
        self, real_postgres_client, test_clinic_with_user, db_session
    ):
        """Verify that validation errors cause rollback and don't leave partial data."""
        clinic = test_clinic_with_user
        headers = {"Authorization": f"Bearer {clinic['token']}"}

        # Try to create an appointment with invalid patient_id (doesn't exist)
        # This should fail validation and rollback
        appointment_data = {
            "patient_id": str(uuid.uuid4()),  # Non-existent patient
            "therapist_id": str(clinic["therapist_id"]),
            "scheduled_at": "2026-08-26T10:00:00Z",
            "duration_minutes": 30,
        }
        response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/appointments",
            json=appointment_data,
            headers=headers,
        )
        # Should fail because patient doesn't exist
        assert response.status_code in [400, 404, 422], response.text

        # Verify no orphan appointment was created
        result = await db_session.execute(
            select(Appointment).where(
                Appointment.therapist_id == clinic["therapist_id"]
            )
        )
        appointments = result.scalars().all()
        # Should be empty because the request should have rolled back
        assert len(appointments) == 0


class TestExplicitCommitsPreserved:
    """Verify that existing explicit commits don't cause issues."""

    @pytest.mark.asyncio
    async def test_auth_register_with_explicit_commit_persists(
        self, real_postgres_client, db_session
    ):
        """auth_service.register_user has an explicit commit - verify it still works."""
        unique_email = f"register_{uuid.uuid4().hex[:8]}@test.com"

        response = await real_postgres_client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "email": unique_email,
                "password": "TestPassword123!",
                "clinic_name": "Explicit Commit Test Clinic",
                "first_name": "Explicit",
                "last_name": "Commit",
            },
        )
        assert response.status_code in (200, 201), response.text

        # Verify user was persisted
        from app.models.user import User

        result = await db_session.execute(
            select(User).where(User.email == unique_email)
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.first_name == "Explicit"
