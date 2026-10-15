import pytest
from uuid import UUID
from sqlalchemy import select

from app.core.config import settings
from app.models.patient import Patient


async def _create_patient(client, auth_headers, first_name="Filter", last_name="Regression"):
    response = await client.post(
        f"{settings.API_V1_PREFIX}/patients",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "phone": "9876543210",
        },
        headers=auth_headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_active_patient_list_fetch_search_and_update_still_work(client, auth_headers):
    patient_id = await _create_patient(client, auth_headers, "Active", "FilterPatient")

    listed = await client.get(f"{settings.API_V1_PREFIX}/patients", headers=auth_headers)
    assert listed.status_code == 200
    assert any(row["id"] == patient_id for row in listed.json()["data"])

    fetched = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert fetched.status_code == 200

    searched = await client.get(
        f"{settings.API_V1_PREFIX}/patients",
        params={"search": "Active FilterPatient"},
        headers=auth_headers,
    )
    assert searched.status_code == 200
    assert any(row["id"] == patient_id for row in searched.json()["data"])

    updated = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}",
        json={"first_name": "ActiveUpdated"},
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["first_name"] == "ActiveUpdated"


@pytest.mark.asyncio
async def test_deleted_patient_is_excluded_from_normal_patient_apis(
    client, auth_headers, db_session
):
    patient_id = await _create_patient(client, auth_headers, "Deleted", "FilterPatient")
    deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert deleted.status_code == 200, deleted.text

    listed = await client.get(f"{settings.API_V1_PREFIX}/patients", headers=auth_headers)
    assert listed.status_code == 200
    assert all(row["id"] != patient_id for row in listed.json()["data"])

    fetched = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert fetched.status_code == 404

    searched = await client.get(
        f"{settings.API_V1_PREFIX}/patients",
        params={"search": "Deleted FilterPatient"},
        headers=auth_headers,
    )
    assert searched.status_code == 200
    assert all(row["id"] != patient_id for row in searched.json()["data"])

    updated = await client.patch(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}",
        json={"first_name": "ShouldNotUpdate"},
        headers=auth_headers,
    )
    assert updated.status_code == 404

    patient = await db_session.scalar(select(Patient).where(Patient.id == UUID(patient_id)))
    assert patient is not None
    assert patient.deleted_at is not None
    assert patient.first_name == "Deleted"


@pytest.mark.asyncio
async def test_deleted_patient_can_still_be_restored(client, auth_headers, db_session):
    patient_id = await _create_patient(client, auth_headers, "Restore", "FilterPatient")
    deleted = await client.delete(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert deleted.status_code == 200

    normal_list = await client.get(
        f"{settings.API_V1_PREFIX}/patients", headers=auth_headers
    )
    assert all(row["id"] != patient_id for row in normal_list.json()["data"])

    restored = await client.post(
        f"{settings.API_V1_PREFIX}/recycle-bin/patient/{patient_id}/restore",
        headers=auth_headers,
    )
    assert restored.status_code == 200, restored.text

    patient = await db_session.scalar(select(Patient).where(Patient.id == UUID(patient_id)))
    assert patient is not None
    assert patient.deleted_at is None

    visible = await client.get(
        f"{settings.API_V1_PREFIX}/patients/{patient_id}", headers=auth_headers
    )
    assert visible.status_code == 200
