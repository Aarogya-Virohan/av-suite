from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import uuid
import asyncpg
import pytest
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url
from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
S2_REVISION = "s2plat20261120"
S2_PARENT = "1912c0f3f42f"


def _connection_strings(source: str):
    url = make_url(source)
    if url.get_backend_name() != "postgresql" or (url.host or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("S2 migration validation requires disposable local PostgreSQL")
    return url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)


def _alembic(database_url: str, command: str, target: str | None = None):
    env = os.environ.copy()
    env.update(DEBUG="false", DATABASE_URL=database_url)
    env.pop("TEST_DATABASE_URL", None)
    args = [sys.executable, "-m", "alembic", command]
    if target is not None:
        args.append(target)
    result = subprocess.run(args, cwd=BACKEND_DIR, env=env, check=True, capture_output=True, text=True)
    return result.stdout + result.stderr


@pytest.mark.asyncio
async def test_s2_migration_round_trip_and_schema(test_database_url_safety_check):
    script = ScriptDirectory.from_config(
        AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    )
    assert script.get_revision(S2_REVISION).down_revision == S2_PARENT

    source = settings.TEST_DATABASE_URL or settings.DATABASE_URL
    test_database_url_safety_check(source)
    admin_dsn = _connection_strings(source)
    name = f"av_s2_migration_{uuid.uuid4().hex[:16]}"
    admin = await asyncpg.connect(admin_dsn)
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()
    database_url = make_url(source).set(database=name).render_as_string(hide_password=False)
    try:
        _alembic(database_url, "upgrade", S2_REVISION)
        conn = await asyncpg.connect(database_url.replace("+asyncpg", ""))
        try:
            tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('platform_operators', 'platform_audit_logs', 'platform_auth_rate_limits')")
            assert {row["tablename"] for row in tables} == {"platform_operators", "platform_audit_logs", "platform_auth_rate_limits"}
            columns = {row["column_name"] for row in await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='platform_operators'")}
            assert "last_totp_step" in columns
            limiter_indexes = {row["indexname"] for row in await conn.fetch("SELECT indexname FROM pg_indexes WHERE tablename='platform_auth_rate_limits'")}
            assert "ix_platform_auth_rate_limits_updated_at" in limiter_indexes
            role_check = await conn.fetchval("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='platform_operators'::regclass AND contype='c'")
            assert "owner" in role_check and "support" in role_check
            indexes = {row["indexname"] for row in await conn.fetch("SELECT indexname FROM pg_indexes WHERE tablename='platform_audit_logs'")}
            assert {"ix_platform_audit_logs_created_at", "ix_platform_audit_logs_organization_id", "ix_platform_audit_logs_operator_id"} <= indexes
            fks = {(row["table_name"], row["column_name"], row["foreign_table_name"]) for row in await conn.fetch("""SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name
                   FROM information_schema.table_constraints tc
                   JOIN information_schema.key_column_usage kcu
                     ON tc.constraint_catalog=kcu.constraint_catalog AND tc.constraint_schema=kcu.constraint_schema
                    AND tc.constraint_name=kcu.constraint_name AND tc.table_name=kcu.table_name
                   JOIN information_schema.constraint_column_usage ccu
                     ON tc.constraint_catalog=ccu.constraint_catalog AND tc.constraint_schema=ccu.constraint_schema
                    AND tc.constraint_name=ccu.constraint_name
                   WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_name='platform_audit_logs'""")}
            assert ("platform_audit_logs", "operator_id", "platform_operators") in fks
            assert ("platform_audit_logs", "organization_id", "organizations") in fks
            assert ("platform_audit_logs", "clinic_id", "clinics") in fks
        finally:
            await conn.close()
        _alembic(database_url, "downgrade", S2_PARENT)
        conn = await asyncpg.connect(database_url.replace("+asyncpg", ""))
        try:
            remaining = await conn.fetchval("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename IN ('platform_operators', 'platform_audit_logs', 'platform_auth_rate_limits')")
            assert remaining == 0
        finally:
            await conn.close()
        _alembic(database_url, "upgrade", S2_REVISION)
        assert S2_REVISION in _alembic(database_url, "current")
        _alembic(database_url, "upgrade", "head")
        assert "crm10code20261124" in _alembic(database_url, "current")
        assert _alembic(database_url, "heads").count("(head)") == 1
    finally:
        admin = await asyncpg.connect(admin_dsn)
        try:
            await admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=$1 AND pid<>pg_backend_pid()", name)
            await admin.execute(f'DROP DATABASE IF EXISTS "{name}"')
        finally:
            await admin.close()
