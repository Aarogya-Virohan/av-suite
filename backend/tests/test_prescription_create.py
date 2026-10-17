"""Regression: creating a prescription through the API.

POST /prescriptions passed the authenticated user's id (already a UUID
object) to uuid.UUID(), which only accepts strings, so every new
prescription returned 500. No test covered the endpoint.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.product import WorkspaceProduct
from app.models.user import User


async def test_admin_can_create_prescription(client: AsyncClient, db_session: AsyncSession):
    clinic = Clinic(name=f"Rx Clinic {uuid.uuid4()}")
    user = User(
        id=uuid.uuid4(),
        clinic_id=None,
        email=f"rx-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash",
        role=UserRole.ADMIN,
        first_name="Rx",
        last_name="Admin",
        is_active=True,
    )
    db_session.add_all([clinic, user])
    await db_session.flush()
    user.clinic_id = clinic.id
    db_session.add(Membership(user_id=user.id, clinic_id=clinic.id, role=UserRole.ADMIN))
    db_session.add(
        WorkspaceProduct(clinic_id=clinic.id, product_id="exercise-prescription", status=EntitlementStatus.ENABLED)
    )
    patient = Patient(clinic_id=clinic.id, first_name="Rx", last_name="Patient")
    exercise = Exercise(clinic_id=clinic.id, title="Bridge", is_free=True)
    db_session.add_all([patient, exercise])
    await db_session.commit()

    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=UserRole.ADMIN.value)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{settings.API_V1_PREFIX}/prescriptions",
        headers=headers,
        json={
            "patient_id": str(patient.id),
            "items": [{"exercise_id": str(exercise.id), "sets": 3, "reps": 12}],
        },
    )
    assert response.status_code == 201, response.text
    rx_id = uuid.UUID(response.json()["data"]["id"])

    stored = await db_session.scalar(select(Prescription).where(Prescription.id == rx_id))
    assert stored is not None
    assert stored.clinic_id == clinic.id
    assert stored.physio_id == user.id
