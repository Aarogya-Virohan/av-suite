from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import uuid

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.models import Clinic, OrganizationMembership

BACKEND_DIR = Path(__file__).resolve().parents[1]
S1_REVISION = "s1fnd20261120"
S1_PARENT = "6ab832834814"


def _s1_index_columns_from_metadata() -> dict[str, tuple[str, ...]]:
    tables = (Clinic.__table__, OrganizationMembership.__table__)
    return {
        index.name: tuple(column.name for column in index.columns)
        for table in tables
        for index in table.indexes
        if index.name
        in {
            "ix_clinics_organization_id",
            "ix_organization_memberships_organization_id",
        }
    }


def _safe_local_admin_dsn(test_database_url: str) -> tuple[str, str]:
    url = make_url(test_database_url)
    if url.get_backend_name() != "postgresql" or (url.host or "").lower() not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise RuntimeError("S1 migration tests require disposable local PostgreSQL.")
    admin_url = url.set(drivername="postgresql", database="postgres")
    return admin_url.render_as_string(hide_password=False), url.render_as_string(
        hide_password=False
    )


def _run_alembic(database_url: str, command: str, target: str) -> str:
    environment = os.environ.copy()
    environment.update(DEBUG="false", DATABASE_URL=database_url)
    environment.pop("TEST_DATABASE_URL", None)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", command, target],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr


async def _create_test_database(admin_dsn: str) -> tuple[str, str]:
    db_name = f"av_s1_migration_{uuid.uuid4().hex[:16]}"
    admin = await asyncpg.connect(admin_dsn)
    try:
        await admin.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await admin.close()
    base = make_url(settings.TEST_DATABASE_URL or settings.DATABASE_URL)
    target = base.set(database=db_name)
    return db_name, target.render_as_string(hide_password=False)


async def _drop_test_database(admin_dsn: str, db_name: str) -> None:
    admin = await asyncpg.connect(admin_dsn)
    try:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            db_name,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    finally:
        await admin.close()


@pytest.mark.asyncio
async def test_s1_empty_database_upgrade_downgrade_upgrade_and_single_head(
    test_database_url_safety_check,
) -> None:
    source_url = settings.TEST_DATABASE_URL or settings.DATABASE_URL
    test_database_url_safety_check(source_url)
    admin_dsn, _ = _safe_local_admin_dsn(source_url)
    db_name, database_url = await _create_test_database(admin_dsn)
    try:
        _run_alembic(database_url, "upgrade", "head")
        _run_alembic(database_url, "downgrade", "6ab832834814")
        _run_alembic(database_url, "upgrade", "head")
        environment = os.environ.copy()
        environment.update(DEBUG="false", DATABASE_URL=database_url)
        heads = subprocess.run(
            [sys.executable, "-m", "alembic", "heads"],
            cwd=BACKEND_DIR,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert heads.count("(head)") == 1
        assert S1_REVISION in heads
    finally:
        await _drop_test_database(admin_dsn, db_name)


@pytest.mark.asyncio
async def test_s1_backfill_on_alembic_schema_preserves_rows_and_creates_owners(
    test_database_url_safety_check,
) -> None:
    source_url = settings.TEST_DATABASE_URL or settings.DATABASE_URL
    test_database_url_safety_check(source_url)
    admin_dsn, _ = _safe_local_admin_dsn(source_url)
    db_name, database_url = await _create_test_database(admin_dsn)
    try:
        _run_alembic(database_url, "upgrade", S1_PARENT)
        connection = await asyncpg.connect(database_url.replace("+asyncpg", ""))
        try:
            clinic_solo = uuid.uuid4()
            clinic_regular = uuid.uuid4()
            clinic_legacy_type = uuid.uuid4()
            patient_id = uuid.uuid4()
            user_id = uuid.uuid4()
            therapist_id = uuid.uuid4()
            await connection.execute(
                "ALTER TYPE clinic_type ADD VALUE 'legacy_s1_test_type'"
            )
            await connection.execute(
                """INSERT INTO clinics (id, name, slug, type) VALUES
                   ($1, 'Legacy solo clinic', 's1-legacy-solo', 'solo'::clinic_type),
                   ($2, 'Legacy clinic', 's1-legacy-clinic', 'clinic'::clinic_type),
                   ($3, 'Unknown legacy type', 's1-legacy-unknown',
                    'legacy_s1_test_type'::clinic_type)""",
                clinic_solo,
                clinic_regular,
                clinic_legacy_type,
            )
            await connection.execute(
                """INSERT INTO users
                   (id, clinic_id, email, password_hash, role, first_name, last_name)
                   VALUES ($1, $2, $3, 'unused', 'admin', 'Legacy', 'Admin')""",
                user_id,
                clinic_solo,
                f"s1-migration-{user_id}@example.com",
            )
            for clinic_id in (clinic_solo, clinic_regular, clinic_legacy_type):
                await connection.execute(
                    """INSERT INTO memberships (id, user_id, clinic_id, role)
                       VALUES ($1, $2, $3, 'admin'::user_role)""",
                    uuid.uuid4(),
                    user_id,
                    clinic_id,
                )
            await connection.execute(
                """INSERT INTO patients
                   (id, clinic_id, display_number, first_name, last_name, phone)
                   VALUES ($1, $2, 73, 'Ada', 'Legacy', '5550101')""",
                patient_id,
                clinic_solo,
            )
            await connection.execute(
                """INSERT INTO users
                   (id, clinic_id, email, password_hash, role, first_name, last_name)
                   VALUES ($1, $2, $3, 'unused', 'therapist', 'Legacy', 'Therapist')""",
                therapist_id,
                clinic_regular,
                f"s1-therapist-{therapist_id}@example.com",
            )
            await connection.execute(
                """INSERT INTO memberships (id, user_id, clinic_id, role)
                   VALUES ($1, $2, $3, 'therapist'::user_role)""",
                uuid.uuid4(),
                therapist_id,
                clinic_regular,
            )
            before = {
                table: await connection.fetchval(f"SELECT count(*) FROM {table}")
                for table in ("clinics", "memberships", "patients")
            }
            clinic_rows_before = await connection.fetch(
                "SELECT id, name, slug, type::text AS type FROM clinics ORDER BY id"
            )
            membership_rows_before = await connection.fetch(
                """SELECT id, user_id, clinic_id, role::text AS role
                   FROM memberships ORDER BY id"""
            )
            patient_before = await connection.fetchrow(
                """SELECT id, clinic_id, display_number, first_name, last_name, phone
                   FROM patients WHERE id = $1""",
                patient_id,
            )
        finally:
            await connection.close()

        _run_alembic(database_url, "upgrade", "head")
        connection = await asyncpg.connect(database_url.replace("+asyncpg", ""))
        try:
            organizations = await connection.fetch(
                "SELECT type, count(*) AS count FROM organizations GROUP BY type"
            )
            assert {row["type"]: row["count"] for row in organizations} == {
                "individual": 1,
                "clinic": 2,
            }
            assert await connection.fetchval(
                "SELECT count(*) FROM organization_memberships WHERE role = 'org_owner'"
            ) == 3
            assert await connection.fetchval(
                "SELECT count(*) FROM clinics WHERE organization_id IS NULL"
            ) == 0
            metadata_indexes = _s1_index_columns_from_metadata()
            assert metadata_indexes == {
                "ix_clinics_organization_id": ("organization_id",),
                "ix_organization_memberships_organization_id": ("organization_id",),
            }
            database_indexes = await connection.fetch(
                """SELECT indexname, indexdef FROM pg_indexes
                   WHERE schemaname = 'public'
                     AND tablename IN ('clinics', 'organization_memberships')"""
            )
            database_index_defs = {
                row["indexname"]: " ".join(row["indexdef"].lower().split())
                for row in database_indexes
            }
            for name, columns in metadata_indexes.items():
                assert name in database_index_defs
                assert database_index_defs[name].endswith(
                    f"({', '.join(columns)})"
                )
            after = {
                table: await connection.fetchval(f"SELECT count(*) FROM {table}")
                for table in ("clinics", "memberships", "patients")
            }
            assert after == before
            assert await connection.fetch(
                "SELECT id, name, slug, type::text AS type FROM clinics ORDER BY id"
            ) == clinic_rows_before
            assert await connection.fetch(
                """SELECT id, user_id, clinic_id, role::text AS role
                   FROM memberships ORDER BY id"""
            ) == membership_rows_before
            assert await connection.fetchrow(
                """SELECT id, clinic_id, display_number, first_name, last_name, phone
                   FROM patients WHERE id = $1""",
                patient_id,
            ) == patient_before
        finally:
            await connection.close()

        _run_alembic(database_url, "downgrade", "6ab832834814")
        connection = await asyncpg.connect(database_url.replace("+asyncpg", ""))
        try:
            assert await connection.fetchval("SELECT count(*) FROM clinics") == before[
                "clinics"
            ]
            assert await connection.fetchval("SELECT count(*) FROM memberships") == before[
                "memberships"
            ]
            assert await connection.fetchval("SELECT count(*) FROM patients") == before[
                "patients"
            ]
            assert await connection.fetchrow(
                """SELECT id, clinic_id, display_number, first_name, last_name, phone
                   FROM patients WHERE id = $1""",
                patient_id,
            ) == patient_before
            assert await connection.fetch(
                """SELECT id, user_id, clinic_id, role::text AS role
                   FROM memberships ORDER BY id"""
            ) == membership_rows_before
        finally:
            await connection.close()

        _run_alembic(database_url, "upgrade", "head")
        connection = await asyncpg.connect(database_url.replace("+asyncpg", ""))
        try:
            after_reupgrade = {
                table: await connection.fetchval(f"SELECT count(*) FROM {table}")
                for table in ("clinics", "memberships", "patients")
            }
            assert after_reupgrade == before
            assert await connection.fetchval(
                "SELECT count(*) FROM organizations"
            ) == before["clinics"]
            assert await connection.fetchval(
                "SELECT count(*) FROM organization_memberships WHERE role = 'org_owner'"
            ) == 3
            assert await connection.fetch(
                "SELECT id, name, slug, type::text AS type FROM clinics ORDER BY id"
            ) == clinic_rows_before
            assert await connection.fetch(
                """SELECT id, user_id, clinic_id, role::text AS role
                   FROM memberships ORDER BY id"""
            ) == membership_rows_before
            assert await connection.fetchrow(
                """SELECT id, clinic_id, display_number, first_name, last_name, phone
                   FROM patients WHERE id = $1""",
                patient_id,
            ) == patient_before
            assert await connection.fetchval(
                "SELECT count(*) FROM clinics WHERE organization_id IS NULL"
            ) == 0
        finally:
            await connection.close()
    finally:
        await _drop_test_database(admin_dsn, db_name)
