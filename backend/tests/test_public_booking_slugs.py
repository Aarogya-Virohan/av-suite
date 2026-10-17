from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.clinic import Clinic
from app.repositories.clinic import ClinicRepository


@pytest.mark.asyncio
async def test_clinic_slug_lookup_is_exact_and_public_booking_isolated(db_session, client):
    clinic_a = Clinic(name="Apollo Physiotherapy", slug="apollo-physiotherapy")
    clinic_b = Clinic(
        name="Apollo Physiotherapy & Rehab", slug="apollo-physiotherapy-rehab"
    )
    db_session.add_all([clinic_a, clinic_b])
    await db_session.flush()

    repository = ClinicRepository(db_session)
    assert (await repository.get_by_slug_or_id(clinic_a.slug)).id == clinic_a.id
    assert (await repository.get_by_slug_or_id(clinic_b.slug)).id == clinic_b.id
    assert await repository.get_by_slug_or_id("Apollo Physiotherapy") is None
    assert await repository.get_by_slug_or_id("physiotherapy") is None

    payload = {
        "name": "Booking Patient",
        "phone": f"+9198{uuid4().int % 10**8:08d}",
        "age": 34,
        "chief_complaint": "Back pain",
    }
    for slug, expected_clinic in (
        (clinic_a.slug, clinic_a),
        (clinic_b.slug, clinic_b),
    ):
        response = await client.post(
            f"{settings.API_V1_PREFIX}/booking/request",
            params={"clinic_slug": slug},
            json=payload,
        )
        assert response.status_code == 201, response.text
        assert response.json()["data"]["clinic_id"] == str(expected_clinic.id)


@pytest.mark.asyncio
async def test_slug_or_id_keeps_exact_uuid_lookup(db_session):
    clinic = Clinic(name="UUID Clinic")
    db_session.add(clinic)
    await db_session.flush()

    found = await ClinicRepository(db_session).get_by_slug_or_id(str(clinic.id))
    assert found is not None
    assert found.id == clinic.id


def test_new_clinics_get_unique_deterministic_shape_slugs():
    clinic_id_a, clinic_id_b = uuid4(), uuid4()
    first = Clinic(id=clinic_id_a, name="Apollo Physiotherapy")
    second = Clinic(id=clinic_id_b, name="Apollo Physiotherapy")

    assert first.slug.startswith("apollo-physiotherapy-")
    assert second.slug.startswith("apollo-physiotherapy-")
    assert first.slug != second.slug
    assert first.slug.endswith(clinic_id_a.hex[:12])
    assert second.slug.endswith(clinic_id_b.hex[:12])
