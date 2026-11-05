import asyncio
import importlib.util
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.models.clinic import Clinic
from app.models.patient import Patient, PatientCounter
from app.schemas.common import PaginationParams
from app.schemas.patient import PatientCreate
from app.services.patient_service import create_patient, search_patients


@pytest.mark.asyncio
async def test_patient_display_number_api_search_and_no_reuse(client, auth_headers):
    base = f"{settings.API_V1_PREFIX}/patients"
    created = await client.post(
        base, json={"first_name": "Number", "last_name": "Patient"}, headers=auth_headers
    )
    assert created.status_code in (200, 201), created.text
    patient = created.json()["data"]
    assert isinstance(patient["display_number"], int)

    listed = await client.get(base, headers=auth_headers)
    assert listed.status_code == 200
    assert next(p for p in listed.json()["data"] if p["id"] == patient["id"])["display_number"] == patient["display_number"]
    detail = await client.get(f"{base}/{patient['id']}", headers=auth_headers)
    assert isinstance(detail.json()["data"]["display_number"], int)

    for term in (str(patient["display_number"]), f"{patient['display_number']:06d}"):
        found = await client.get(base, params={"search": term}, headers=auth_headers)
        assert found.status_code == 200
        assert any(p["id"] == patient["id"] for p in found.json()["data"])

    deleted = await client.delete(f"{base}/{patient['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    next_patient = await client.post(
        base, json={"first_name": "Next", "last_name": "Patient"}, headers=auth_headers
    )
    assert next_patient.json()["data"]["display_number"] > patient["display_number"]


@pytest.mark.asyncio
async def test_display_number_sequences_are_clinic_scoped(db_session):
    clinics = [
        Clinic(
            id=uuid.uuid4(), name=f"Counter Clinic {index}", branding_color="#008080",
            plan_tier="clinical_pro", is_partner_clinic=True,
        )
        for index in (1, 2)
    ]
    db_session.add_all(clinics)
    await db_session.commit()

    first = await create_patient(db_session, str(clinics[0].id), PatientCreate(first_name="A", last_name="One"))
    second = await create_patient(db_session, str(clinics[0].id), PatientCreate(first_name="A", last_name="Two"))
    other = await create_patient(db_session, str(clinics[1].id), PatientCreate(first_name="B", last_name="One"))
    assert (first.display_number, second.display_number, other.display_number) == (1, 2, 1)


@pytest.mark.asyncio
async def test_search_matches_123_and_zero_padded_000123(db_session):
    clinic = Clinic(name="Search Number Clinic")
    db_session.add(clinic)
    await db_session.commit()
    db_session.add(PatientCounter(clinic_id=clinic.id, last_number=122))
    await db_session.commit()

    patient = await create_patient(
        db_session, str(clinic.id), PatientCreate(first_name="Search", last_name="Target")
    )
    assert patient.display_number == 123
    for term in ("123", "000123"):
        found, _ = await search_patients(
            db_session, str(clinic.id), term, PaginationParams(page=1, page_size=20)
        )
        assert patient.id in {result.id for result in found}


@pytest.mark.asyncio
async def test_parallel_patient_creates_allocate_unique_numbers(sessionmaker, setup_db):
    # PostgreSQL is the production concurrency target. SQLite's write-lock behavior
    # does not model PostgreSQL's concurrent ON CONFLICT row locking.
    from app.core.config import settings
    from sqlalchemy.engine import make_url

    if make_url(settings.TEST_DATABASE_URL or settings.DATABASE_URL).get_backend_name() != "postgresql":
        pytest.skip("PostgreSQL required to exercise concurrent counter upserts")
    async with sessionmaker() as session:
        clinic = (await session.execute(select(Clinic).limit(1))).scalar_one()
        clinic_id = str(clinic.id)

    async def create(index):
        async with sessionmaker() as session:
            return await create_patient(
                session, clinic_id,
                PatientCreate(first_name="Concurrent", last_name=f"{index}"),
            )

    patients = await asyncio.gather(*(create(i) for i in range(12)))
    assert len({patient.display_number for patient in patients}) == 12


@pytest.mark.asyncio
async def test_migration_backfills_existing_patients_per_clinic(engine, setup_db):
    if make_url(settings.TEST_DATABASE_URL or settings.DATABASE_URL).get_backend_name() != "postgresql":
        pytest.skip("PostgreSQL required to exercise the migration")

    migration_path = Path(__file__).parents[1] / "alembic/versions/c7d9e1a4b602_patient_display_number.py"
    spec = importlib.util.spec_from_file_location("patient_display_number_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    schema = f"patient_number_migration_{uuid.uuid4().hex}"

    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        await connection.execute(text("CREATE TABLE clinics (id uuid PRIMARY KEY)"))
        await connection.execute(text("""
            CREATE TABLE patients (
                id uuid PRIMARY KEY,
                clinic_id uuid NOT NULL REFERENCES clinics(id),
                created_at timestamptz NOT NULL
            )
        """))
        await connection.execute(text("""
            INSERT INTO clinics (id) VALUES
                ('10000000-0000-0000-0000-000000000001'),
                ('10000000-0000-0000-0000-000000000002'),
                ('10000000-0000-0000-0000-000000000003')
        """))
        await connection.execute(text("""
            INSERT INTO patients (id, clinic_id, created_at) VALUES
                ('20000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '2024-01-01'),
                ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '2024-01-01'),
                ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '2024-01-02'),
                ('30000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000002', '2024-01-03')
        """))

        def run_migration(sync_connection):
            context = MigrationContext.configure(sync_connection)
            with Operations.context(context):
                migration.upgrade()

        await connection.run_sync(run_migration)
        rows = (await connection.execute(text("""
            SELECT id::text, display_number FROM patients ORDER BY clinic_id, display_number
        """))).all()
        assert [(row.id, row.display_number) for row in rows] == [
            ("20000000-0000-0000-0000-000000000001", 1),
            ("20000000-0000-0000-0000-000000000003", 2),
            ("20000000-0000-0000-0000-000000000002", 3),
            ("30000000-0000-0000-0000-000000000001", 1),
        ]
        counters = (await connection.execute(text(
            "SELECT clinic_id::text, last_number FROM patient_counters ORDER BY clinic_id"
        ))).all()
        assert [(row.clinic_id, row.last_number) for row in counters] == [
            ("10000000-0000-0000-0000-000000000001", 3),
            ("10000000-0000-0000-0000-000000000002", 1),
        ]
        nullable = await connection.scalar(text("""
            SELECT is_nullable FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = 'patients' AND column_name = 'display_number'
        """), {"schema": schema})
        assert nullable == "NO"
        await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
