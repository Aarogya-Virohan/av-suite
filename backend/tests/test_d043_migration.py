"""
Migration brnum20261127 (Round 4 branding + D-043 numbers) on a database that
already holds the kind of rows prod has: invoices numbered INV-0001, old
prescriptions, saved and unsaved posture sessions, payments. Upgrade,
downgrade, upgrade again.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import settings
from tests.test_s2_migration import _alembic, _connection_strings

REVISION = "brnum20261127"
PARENT = "crm10code20261124"


async def _insert(conn, table: str, values: dict) -> None:
    """Insert one row, filling every other NOT NULL column without a default
    with a plain value of its type (the schema here is crm10code20261124)."""
    cols = await conn.fetch(
        """SELECT column_name, data_type, udt_name FROM information_schema.columns
           WHERE table_name = $1 AND is_nullable = 'NO' AND column_default IS NULL""",
        table,
    )
    row = dict(values)
    for c in cols:
        name = c["column_name"]
        if name in row:
            continue
        dt = c["data_type"]
        if dt == "uuid":
            row[name] = uuid.uuid4()
        elif dt in ("integer", "bigint", "smallint"):
            row[name] = 1
        elif dt == "numeric":
            row[name] = 0
        elif dt == "boolean":
            row[name] = False
        elif dt.startswith("timestamp"):
            row[name] = datetime.now(timezone.utc)
        elif dt == "date":
            row[name] = datetime.now(timezone.utc).date()
        elif dt in ("json", "jsonb"):
            row[name] = "{}"
        elif dt == "USER-DEFINED":
            row[name] = await conn.fetchval(
                "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = $1 ORDER BY enumsortorder LIMIT 1",
                c["udt_name"],
            )
        else:
            row[name] = f"x{uuid.uuid4().hex[:6]}"
    names = list(row)
    casts = []
    for n in names:
        udt = next((c["udt_name"] for c in cols if c["column_name"] == n), None)
        casts.append(f"${len(casts) + 1}::{udt}" if udt and udt.startswith("json") else f"${len(casts) + 1}")
    await conn.execute(
        f'INSERT INTO {table} ({", ".join(names)}) VALUES ({", ".join(casts)})', *row.values()
    )


@pytest.mark.asyncio
async def test_numbers_backfilled_in_order_and_round_trip(test_database_url_safety_check):
    source = settings.TEST_DATABASE_URL or settings.DATABASE_URL
    test_database_url_safety_check(source)
    admin_dsn = _connection_strings(source)
    name = f"av_d043_migration_{uuid.uuid4().hex[:16]}"
    admin = await asyncpg.connect(admin_dsn)
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()
    database_url = make_url(source).set(database=name).render_as_string(hide_password=False)
    dsn = database_url.replace("+asyncpg", "")
    try:
        _alembic(database_url, "upgrade", PARENT)
        conn = await asyncpg.connect(dsn)
        t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
        org = uuid.uuid4()
        clinics = {"SPC": uuid.uuid4(), "ASC2": uuid.uuid4()}
        try:
            await _insert(conn, "organizations", {"id": org, "type": "clinic"})
            for i, (code, cid) in enumerate(clinics.items()):
                await _insert(conn, "clinics", {"id": cid, "name": f"Clinic {code}", "code": code,
                                                "slug": f"c-{code.lower()}-{uuid.uuid4().hex[:6]}",
                                                "organization_id": org, "client_type": "clinic", "type": "clinic",
                                                "created_at": t0, "updated_at": t0})
            user = uuid.uuid4()
            await _insert(conn, "users", {"id": user, "email": f"u{uuid.uuid4().hex[:6]}@x.in",
                                          "clinic_id": clinics["SPC"]})
            patients = {}
            for code, cid in clinics.items():
                patients[code] = uuid.uuid4()
                await _insert(conn, "patients", {"id": patients[code], "clinic_id": cid, "first_name": "P",
                                                 "last_name": code, "display_number": 1})
            # Prescriptions inserted out of time order: numbering follows created_at.
            rx = {}
            for minutes in (30, 10, 20):
                rid = uuid.uuid4()
                rx[minutes] = rid
                await _insert(conn, "prescriptions", {"id": rid, "clinic_id": clinics["SPC"],
                                                      "patient_id": patients["SPC"], "physio_id": user,
                                                      "created_at": t0 + timedelta(minutes=minutes),
                                                      "updated_at": t0})
            await _insert(conn, "prescriptions", {"id": uuid.uuid4(), "clinic_id": clinics["ASC2"],
                                                  "patient_id": patients["ASC2"], "physio_id": user,
                                                  "created_at": t0, "updated_at": t0})
            saved, unsaved = uuid.uuid4(), uuid.uuid4()
            await _insert(conn, "posture_sessions", {"id": saved, "clinic_id": clinics["SPC"],
                                                     "patient_id": patients["SPC"], "report_id": "PT-20261001-AAAA",
                                                     "report_json": '{"reportId": "PT-20261001-AAAA"}',
                                                     "created_at": t0, "updated_at": t0})
            await _insert(conn, "posture_sessions", {"id": unsaved, "clinic_id": clinics["SPC"],
                                                     "patient_id": patients["SPC"], "created_at": t0, "updated_at": t0})
            inv = uuid.uuid4()
            await _insert(conn, "invoices", {"id": inv, "clinic_id": clinics["SPC"], "patient_id": patients["SPC"],
                                             "invoice_number": "INV-0001", "issue_date": t0,
                                             "subtotal": 500, "total_amount": 500, "paid_amount": 500,
                                             "status": "paid"})
            await _insert(conn, "invoice_counters", {"clinic_id": clinics["SPC"], "last_number": 1})
            pay = uuid.uuid4()
            await _insert(conn, "payments", {"id": pay, "clinic_id": clinics["SPC"], "invoice_id": inv,
                                             "patient_id": patients["SPC"], "amount": 500,
                                             "payment_method": "cash", "payment_date": t0})
        finally:
            await conn.close()

        _alembic(database_url, "upgrade", REVISION)
        conn = await asyncpg.connect(dsn)
        try:
            numbers = {r["id"]: r["number"] for r in await conn.fetch("SELECT id, number FROM prescriptions")}
            assert [numbers[rx[m]] for m in (10, 20, 30)] == ["SPC-RX-000001", "SPC-RX-000002", "SPC-RX-000003"]
            assert "ASC2-RX-000001" in numbers.values()
            posture = {r["id"]: r["number"] for r in await conn.fetch("SELECT id, number FROM posture_sessions")}
            assert posture == {saved: "SPC-POS-000001", unsaved: None}
            counters = {(r["clinic_id"], r["doc_type"], r["period"]): r["last_number"]
                        for r in await conn.fetch("SELECT * FROM document_counters")}
            assert counters == {(clinics["SPC"], "RX", ""): 3, (clinics["ASC2"], "RX", ""): 1,
                                (clinics["SPC"], "POS", ""): 1}
            # Issued invoice numbers never change; old payments keep no receipt number.
            assert await conn.fetchval("SELECT invoice_number FROM invoices WHERE id = $1", inv) == "INV-0001"
            assert await conn.fetchval("SELECT receipt_number FROM payments WHERE id = $1", pay) is None
            modes = {r["logo_bg_mode"] for r in await conn.fetch("SELECT logo_bg_mode FROM clinics")}
            assert modes == {"as_is"}
            with pytest.raises(asyncpg.UniqueViolationError):
                await conn.execute("UPDATE prescriptions SET number = 'SPC-RX-000001' WHERE id = $1", rx[30])
            with pytest.raises(asyncpg.CheckViolationError):
                await conn.execute("UPDATE clinics SET logo_bg_mode = 'blur'")
        finally:
            await conn.close()

        _alembic(database_url, "downgrade", PARENT)
        conn = await asyncpg.connect(dsn)
        try:
            gone = await conn.fetchval(
                "SELECT count(*) FROM pg_tables WHERE tablename IN ('document_counters', 'psychosocial_reports')"
            )
            assert gone == 0
            cols = {r["column_name"] for r in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name IN ('clinics', 'prescriptions', 'payments')")}
            assert not cols & {"display_doctor_name", "website", "logo_bg_mode", "number", "receipt_number"}
            assert await conn.fetchval("SELECT count(*) FROM prescriptions") == 4
            assert await conn.fetchval("SELECT invoice_number FROM invoices") == "INV-0001"
        finally:
            await conn.close()

        _alembic(database_url, "upgrade", "head")
        assert REVISION in _alembic(database_url, "current")
        conn = await asyncpg.connect(dsn)
        try:
            assert await conn.fetchval("SELECT number FROM prescriptions WHERE id = $1", rx[30]) == "SPC-RX-000003"
        finally:
            await conn.close()
    finally:
        admin = await asyncpg.connect(admin_dsn)
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally:
            await admin.close()
