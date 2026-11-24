"""BE fixes before delivery (pipeline report section E and D).

1. bcrypt off the event loop + CRM login limiter + failed login audit
2. limiters hold across two worker processes (database-backed counters)
3. pool timeout gives a clear 503
4. writes are committed before the response starts
5. platform usage / audit date filters are IST calendar days
6. patient search with '@'
7. patient age or date of birth required on create / edit
8. audit rows: Rx, documents, failed login, SOAP / treatment, fee list
9. upload size caps (documents, clinic logo) with a clear 413
"""

from __future__ import annotations

import asyncio
import base64
import os
import sys
import textwrap
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_db
from app.core.platform_security import create_platform_access_token
from app.core.security import (
    create_access_token,
    get_password_hash,
    get_password_hash_async,
    verify_password_async,
)
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.middleware.commit_before_response import CommitBeforeResponseMiddleware
from app.models.audit import AuditLog
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.organization import Organization
from app.models.platform import PlatformAuditLog, PlatformAuthRateLimit, PlatformOperator
from app.models.product import WorkspaceProduct
from app.models.usage_event import UsageEvent
from app.models.user import User
from app.services import login_guard
from app.services.product_entitlements import ensure_crm_entitlement

pytestmark = pytest.mark.asyncio
API = settings.API_V1_PREFIX
BACKEND = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
async def make_clinic(db: AsyncSession, *, documents: bool = False):
    """A fresh clinic with an admin, a patient (with age) and an exercise."""
    clinic = Clinic(name=f"BE Fix Clinic {uuid.uuid4().hex[:6]}", is_documents_enabled=documents)
    admin = User(
        id=uuid.uuid4(), clinic_id=None, email=f"befix-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=UserRole.ADMIN, first_name="Be", last_name="Fix", is_active=True,
    )
    db.add_all([clinic, admin])
    await db.flush()
    admin.clinic_id = clinic.id
    db.add(Membership(user_id=admin.id, clinic_id=clinic.id, role=UserRole.ADMIN))
    db.add(WorkspaceProduct(clinic_id=clinic.id, product_id="exercise-prescription", status=EntitlementStatus.ENABLED))
    await ensure_crm_entitlement(db, clinic.id)
    patient = Patient(
        clinic_id=clinic.id, display_number=uuid.uuid4().int % 9_000_000_000 + 1,
        first_name="Audit", last_name="Patient", age=40,
    )
    exercise = Exercise(clinic_id=clinic.id, title="Bridge", is_free=True)
    db.add_all([patient, exercise])
    await db.commit()
    token = create_access_token(subject=admin.id, clinic_id=clinic.id, role=UserRole.ADMIN.value)
    return clinic, admin, {"Authorization": f"Bearer {token}"}, patient, exercise


async def audit_rows(db: AsyncSession, clinic_id, entity_type: str, action: str | None = None):
    query = select(AuditLog).where(AuditLog.clinic_id == clinic_id, AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    return list((await db.scalars(query.order_by(AuditLog.created_at))).all())


def operator(role="owner"):
    return PlatformOperator(
        email=f"befix-{uuid.uuid4()}@example.com",
        password_hash=get_password_hash("S3TestPass123!"),
        name="BE Fix Operator", role=role, is_active=True, mfa_enabled=True,
        mfa_secret="encrypted-test-secret",
    )


# --------------------------------------------------------------------------
# 1. bcrypt off the event loop, CRM login limiter, failed login audit
# --------------------------------------------------------------------------
async def test_password_hash_and_verify_do_not_block_the_event_loop():
    hashed = await get_password_hash_async("Loop-Check-1")
    assert await verify_password_async("Loop-Check-1", hashed) is True
    assert await verify_password_async("not-it", hashed) is False

    gaps: list[float] = []
    stop = False

    async def ticker():
        last = time.perf_counter()
        while not stop:
            await asyncio.sleep(0.005)
            now = time.perf_counter()
            gaps.append(now - last)
            last = now

    task = asyncio.create_task(ticker())
    await asyncio.sleep(0.05)
    started = time.perf_counter()
    results = await asyncio.gather(*(verify_password_async("Loop-Check-1", hashed) for _ in range(4)))
    busy_for = time.perf_counter() - started
    stop = True
    await task
    assert results == [True] * 4
    # Four bcrypt checks take well over 0.3 s together; the loop must stay free.
    assert busy_for > 0.2
    assert max(gaps) < 0.12, f"event loop stalled for {max(gaps):.3f}s"


async def test_crm_login_limits_attempts_per_account_with_a_clear_429(client):
    url = f"{API}/auth/login"
    body = {"email": "admin@avtest.com", "password": "wrong-password"}
    for _ in range(8):
        assert (await client.post(url, json=body)).status_code == 401
    blocked = await client.post(url, json=body)
    assert blocked.status_code == 429
    detail = blocked.json()["detail"]
    assert detail["code"] == "RATE_LIMITED"
    assert "wait" in detail["message"] and "minute" in detail["message"]
    assert 1 <= int(blocked.headers["Retry-After"]) <= 300
    # The right password is refused too while the window is open.
    right = await client.post(url, json={"email": "admin@avtest.com", "password": "Password123!"})
    assert right.status_code == 429
    # Other accounts are not affected (limit is per account).
    other = await client.post(url, json={"email": "therapist@avtest.com", "password": "Password123!"})
    assert other.status_code == 200
    # Case of the email does not give a fresh allowance.
    upper = await client.post(url, json={"email": "ADMIN@avtest.com", "password": "x"})
    assert upper.status_code == 429


async def test_crm_login_counts_every_attempt_not_only_failures(client):
    url = f"{API}/auth/login"
    ok = {"email": "frontdesk@avtest.com", "password": "Password123!"}
    for _ in range(8):
        assert (await client.post(url, json=ok)).status_code == 200
    assert (await client.post(url, json=ok)).status_code == 429


async def test_crm_login_limits_attempts_per_ip(client, monkeypatch):
    monkeypatch.setattr(login_guard, "LOGIN_IP_LIMIT", 3)
    url = f"{API}/auth/login"
    for index in range(3):
        res = await client.post(url, json={"email": f"nobody{index}@avtest.com", "password": "x"})
        assert res.status_code == 401
    res = await client.post(url, json={"email": "someone-else@avtest.com", "password": "x"})
    assert res.status_code == 429
    assert res.json()["detail"]["code"] == "RATE_LIMITED"


async def test_failed_crm_login_is_audited_without_password_or_extra_pii(client, db_session):
    user = await db_session.scalar(select(User).where(User.email == "therapist@avtest.com"))
    before = len(await audit_rows(db_session, user.clinic_id, "user", "login_failed"))
    secret = "Super-Secret-Wrong-Pw-1"
    res = await client.post(f"{API}/auth/login", json={"email": "therapist@avtest.com", "password": secret})
    assert res.status_code == 401
    rows = await audit_rows(db_session, user.clinic_id, "user", "login_failed")
    assert len(rows) == before + 1
    row = rows[-1]
    assert row.user_id == user.id and row.entity_id == user.id
    assert row.details == {"email": "therapist@avtest.com", "reason": "bad_password"}
    assert secret not in str(row.details)
    # A successful login writes no failure row, an unknown email writes none (no clinic).
    ok = await client.post(f"{API}/auth/login", json={"email": "therapist@avtest.com", "password": "Password123!"})
    assert ok.status_code == 200
    unknown = await client.post(f"{API}/auth/login", json={"email": "ghost@avtest.com", "password": "x"})
    assert unknown.status_code == 401
    assert len(await audit_rows(db_session, user.clinic_id, "user", "login_failed")) == before + 1


async def test_failed_platform_login_is_audited_with_email_only(client, db_session):
    op = operator()
    db_session.add(op)
    await db_session.commit()
    bad = await client.post("/api/v1/platform/auth/login", json={"email": op.email, "password": "NotThePassword1!"})
    assert bad.status_code == 401
    ghost = f"ghost-{uuid.uuid4().hex[:6]}@example.com"
    unknown = await client.post("/api/v1/platform/auth/login", json={"email": ghost, "password": "NotThePassword1!"})
    assert unknown.status_code == 401
    rows = (
        await db_session.scalars(
            select(PlatformAuditLog).where(PlatformAuditLog.action == "auth.login_failed")
            .order_by(PlatformAuditLog.created_at.desc()).limit(10)
        )
    ).all()
    mine = [r for r in rows if r.details.get("email") in (op.email.lower(), ghost)]
    assert {r.details["reason"] for r in mine} == {"bad_password", "unknown_account"}
    for row in mine:
        assert set(row.details) == {"email", "reason"}
        assert "NotThePassword1!" not in str(row.details)
    known = next(r for r in mine if r.details["reason"] == "bad_password")
    assert known.target_id == str(op.id) and known.target_type == "operator"


# --------------------------------------------------------------------------
# 2. limits hold with two worker processes (no per-process memory)
# --------------------------------------------------------------------------
async def test_limit_holds_across_two_worker_processes():
    """Two separate Python processes (two workers) share one counter."""
    key = uuid.uuid4().hex
    code = textwrap.dedent(
        """
        import asyncio, sys
        from datetime import timedelta
        from app.services.platform_rate_limit import consume_limits

        async def main():
            allowed = 0
            for _ in range(int(sys.argv[2])):
                result = await consume_limits([("worker-test", sys.argv[1], 8, timedelta(minutes=5))])
                allowed += int(result.allowed)
            print("ALLOWED", allowed)

        asyncio.run(main())
        """
    )
    procs = [
        await asyncio.create_subprocess_exec(
            sys.executable, "-c", code, key, "6",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(BACKEND), env=os.environ.copy(),
        )
        for _ in range(2)
    ]
    outputs = await asyncio.gather(*(p.communicate() for p in procs))
    allowed = []
    for proc, (out, err) in zip(procs, outputs):
        assert proc.returncode == 0, err.decode()
        allowed.append(int(out.decode().split("ALLOWED")[-1].strip()))
    # 12 attempts over two processes, limit 8: exactly 8 get through.
    # A counter kept in each process's memory would let 12 through.
    assert sum(allowed) == 8, allowed


async def test_screener_limit_is_shared_state_not_process_memory(client, monkeypatch):
    from app.screening import rate_limit

    monkeypatch.setattr(rate_limit, "IP_LIMIT", 2)
    await client.get(f"{API}/screener/{'a' * 43}")
    # Same counter row seen through a brand new engine = another worker.
    other_engine = create_async_engine(settings.DATABASE_URL)
    async with other_engine.connect() as conn:
        count = await conn.scalar(text("SELECT sum(attempt_count) FROM platform_auth_rate_limits"))
    await other_engine.dispose()
    assert count and count >= 1


# --------------------------------------------------------------------------
# 3. pool timeout -> clear 503
# --------------------------------------------------------------------------
async def test_exhausted_pool_gives_a_clear_503(client):
    from app.main import app

    async def busy():
        raise SATimeoutError("QueuePool limit of size 4 overflow 3 reached")

    app.add_api_route("/__pool_busy_probe", busy, methods=["GET"])
    try:
        res = await client.get("/__pool_busy_probe")
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/__pool_busy_probe"]
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "SERVER_BUSY"
    assert "try again" in res.json()["detail"]["message"]
    assert res.headers["Retry-After"] == "5"


async def test_pool_settings_are_bounded_for_two_workers():
    assert settings.DB_POOL_TIMEOUT <= 10
    assert 2 * (settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW) <= 15  # Supabase session pooler size
    from app.core.database import engine

    if engine.dialect.name == "postgresql":
        assert engine.pool.timeout() == settings.DB_POOL_TIMEOUT
        assert engine.pool.size() == settings.DB_POOL_SIZE


# --------------------------------------------------------------------------
# 4. commit before the response is sent
# --------------------------------------------------------------------------
def _probe_app(with_middleware: bool, status_code: int = 200) -> FastAPI:
    probe = FastAPI()
    if with_middleware:
        probe.add_middleware(CommitBeforeResponseMiddleware)

    @probe.post("/write")
    async def write(key: str, db: AsyncSession = Depends(get_db)):
        now = datetime.now(timezone.utc)
        db.add(PlatformAuthRateLimit(key_hash=key, window_started_at=now, attempt_count=1, updated_at=now))
        await db.flush()
        if status_code >= 400:
            raise HTTPException(status_code=status_code, detail="nope")
        return {"ok": True}

    return probe


async def _row_visible_when_response_starts(probe: FastAPI, key: str) -> tuple[bool, int]:
    """Call the app at ASGI level; at `http.response.start` look from another connection."""
    seen: dict[str, object] = {}
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": "/write", "raw_path": b"/write", "root_path": "",
        "query_string": f"key={key}".encode(), "headers": [(b"host", b"test")],
        "client": ("127.0.0.1", 5000), "server": ("test", 80), "state": {},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            seen["status"] = message["status"]
            other = create_async_engine(settings.DATABASE_URL)
            async with other.connect() as conn:
                seen["visible"] = bool(
                    await conn.scalar(text("SELECT count(*) FROM platform_auth_rate_limits WHERE key_hash = :k"), {"k": key})
                )
            await other.dispose()

    await probe(scope, receive, send)
    return bool(seen["visible"]), int(seen["status"])


async def test_write_is_committed_before_the_response_starts(setup_db):
    key = f"commit-first-{uuid.uuid4().hex}"
    visible, status_code = await _row_visible_when_response_starts(_probe_app(True), key)
    assert status_code == 200
    assert visible, "the row was not in the database when the 200 started"


async def test_without_the_middleware_the_write_lands_after_the_response(setup_db):
    """Control: this is the old behaviour the middleware fixes."""
    key = f"commit-late-{uuid.uuid4().hex}"
    visible, status_code = await _row_visible_when_response_starts(_probe_app(False), key)
    assert status_code == 200
    assert not visible


async def test_error_answers_are_not_committed(setup_db):
    key = f"commit-error-{uuid.uuid4().hex}"
    visible, status_code = await _row_visible_when_response_starts(_probe_app(True, 400), key)
    assert status_code == 400 and not visible
    await asyncio.sleep(0.1)
    other = create_async_engine(settings.DATABASE_URL)
    async with other.connect() as conn:
        assert not await conn.scalar(text("SELECT count(*) FROM platform_auth_rate_limits WHERE key_hash = :k"), {"k": key})
    await other.dispose()


async def test_failed_commit_gives_500_not_a_success():
    class Broken:
        def in_transaction(self):
            return True

        async def commit(self):
            raise RuntimeError("commit failed")

        async def rollback(self):
            pass

    sent = []

    async def inner(scope, receive, send):
        scope["state"]["db_session"] = Broken()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    async def send(message):
        sent.append(message)

    await CommitBeforeResponseMiddleware(inner)({"type": "http", "state": {}}, None, send)
    assert sent[0]["status"] == 500
    assert b"SAVE_FAILED" in sent[1]["body"]
    assert len(sent) == 2  # the original 200 and its body were dropped


async def test_middleware_is_registered_on_the_app():
    from app.main import app

    assert CommitBeforeResponseMiddleware in [m.cls for m in app.user_middleware]


# --------------------------------------------------------------------------
# 5. platform usage + audit filters are IST calendar days
# --------------------------------------------------------------------------
async def test_usage_and_audit_date_filters_use_ist_days(client, db_session):
    owner = operator()
    org = Organization(name="IST Org", slug=f"ist-{uuid.uuid4().hex[:8]}", type="clinic")
    clinic = Clinic(name=f"IST Clinic {uuid.uuid4().hex[:6]}")
    db_session.add_all([owner, org, clinic])
    await db_session.flush()
    clinic.organization_id = org.id
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    utc = timezone.utc
    stamps = {
        "before": datetime(2026, 11, 20, 18, 0, tzinfo=utc),  # 20 Nov 23:30 IST
        "early": datetime(2026, 11, 20, 18, 45, tzinfo=utc),  # 21 Nov 00:15 IST
        "late": datetime(2026, 11, 21, 18, 15, tzinfo=utc),  # 21 Nov 23:45 IST
        "after": datetime(2026, 11, 21, 18, 45, tzinfo=utc),  # 22 Nov 00:15 IST
    }
    for name, at in stamps.items():
        db_session.add(UsageEvent(organization_id=org.id, clinic_id=clinic.id, product_key="crm", event_type=f"ist_{name}", created_at=at))
        db_session.add(PlatformAuditLog(action=f"ist.{name}", target_type="probe", created_at=at))
    await db_session.commit()

    usage = await client.get(
        f"{API}/platform/usage?clinic_id={clinic.id}&date_from=2026-11-21&date_to=2026-11-21", headers=headers
    )
    assert usage.status_code == 200, usage.text
    rows = usage.json()["data"]
    assert {r["event_type"] for r in rows} == {"ist_early", "ist_late"}
    assert {r["date"] for r in rows} == {"2026-11-21"}  # grouped by IST day too

    for action, expected in (("ist.early", 1), ("ist.late", 1), ("ist.before", 0), ("ist.after", 0)):
        audit = await client.get(
            f"{API}/platform/audit-logs?action={action}&date_from=2026-11-21&date_to=2026-11-21", headers=headers
        )
        assert audit.status_code == 200, audit.text
        assert len(audit.json()["data"]) == expected, action

    one_sided = await client.get(f"{API}/platform/usage?clinic_id={clinic.id}&date_from=2026-11-22", headers=headers)
    assert {r["event_type"] for r in one_sided.json()["data"]} == {"ist_after"}


# --------------------------------------------------------------------------
# 6. patient search with '@'
# --------------------------------------------------------------------------
async def test_patient_search_with_at_sign_no_longer_crashes(client, auth_headers):
    res = await client.get(f"{API}/patients?search=a@b.com", headers=auth_headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"] == []
    assert res.json()["meta"]["total"] == 0


async def test_patient_search_has_real_total_and_stable_pages(client, db_session):
    clinic, _admin, headers, _patient, _ex = await make_clinic(db_session)
    marker = "Searchmark"
    for index in range(5):
        created = await client.post(
            f"{API}/patients", headers=headers,
            json={"first_name": f"Pat{index}", "last_name": marker, "age": 30 + index},
        )
        assert created.status_code == 201, created.text
    first = (await client.get(f"{API}/patients?search={marker}&page=1&page_size=2", headers=headers)).json()
    second = (await client.get(f"{API}/patients?search={marker}&page=2&page_size=2", headers=headers)).json()
    third = (await client.get(f"{API}/patients?search={marker}&page=3&page_size=2", headers=headers)).json()
    assert first["meta"]["total"] == 5
    ids = [p["id"] for p in first["data"] + second["data"] + third["data"]]
    assert len(ids) == 5 and len(set(ids)) == 5
    numbers = [p["display_number"] for p in first["data"] + second["data"] + third["data"]]
    assert numbers == sorted(numbers)


# --------------------------------------------------------------------------
# 7. age or date of birth required
# --------------------------------------------------------------------------
async def test_patient_create_requires_age_or_date_of_birth(client, db_session):
    _c, _a, auth_headers, _p, _e = await make_clinic(db_session)  # own clinic: keeps the shared test clinic's list short
    url = f"{API}/patients"
    base = {"first_name": "Needs", "last_name": "Age"}
    missing = await client.post(url, headers=auth_headers, json=base)
    assert missing.status_code == 422
    assert "Age or date of birth is required" in str(missing.json())
    blank = await client.post(url, headers=auth_headers, json={**base, "age": None, "date_of_birth": None})
    assert blank.status_code == 422
    with_age = await client.post(url, headers=auth_headers, json={**base, "age": 34})
    assert with_age.status_code == 201 and with_age.json()["data"]["age"] == 34
    with_dob = await client.post(url, headers=auth_headers, json={**base, "date_of_birth": "1990-05-01"})
    assert with_dob.status_code == 201
    assert (await client.post(url, headers=auth_headers, json={**base, "age": 131})).status_code == 422
    assert (await client.post(url, headers=auth_headers, json={**base, "age": -1})).status_code == 422
    zero = await client.post(url, headers=auth_headers, json={**base, "age": 0})
    assert zero.status_code == 201


async def test_patient_edit_cannot_remove_the_last_of_age_and_dob(client, db_session):
    _c, _a, auth_headers, _p, _e = await make_clinic(db_session)  # own clinic: keeps the shared test clinic's list short
    created = await client.post(
        f"{API}/patients", headers=auth_headers, json={"first_name": "Edit", "last_name": "Rule", "age": 50}
    )
    pid = created.json()["data"]["id"]
    url = f"{API}/patients/{pid}"
    cleared = await client.patch(url, headers=auth_headers, json={"age": None})
    assert cleared.status_code == 422
    assert "Age or date of birth is required" in str(cleared.json())
    # Clearing age is fine when a date of birth stays (and the other way round).
    both = await client.patch(url, headers=auth_headers, json={"date_of_birth": "1975-01-01"})
    assert both.status_code == 200
    assert (await client.patch(url, headers=auth_headers, json={"age": None})).status_code == 200
    assert (await client.patch(url, headers=auth_headers, json={"date_of_birth": None})).status_code == 422
    assert (await client.patch(url, headers=auth_headers, json={"age": 200})).status_code == 422


async def test_existing_patients_without_age_keep_working(client, db_session):
    _c, _a, auth_headers, _p, _e = await make_clinic(db_session)
    created = await client.post(
        f"{API}/patients", headers=auth_headers, json={"first_name": "Legacy", "last_name": "Patient", "age": 61}
    )
    pid = created.json()["data"]["id"]
    await db_session.execute(update(Patient).where(Patient.id == uuid.UUID(pid)).values(age=None, date_of_birth=None))
    await db_session.commit()
    url = f"{API}/patients/{pid}"
    read = await client.get(url, headers=auth_headers)
    assert read.status_code == 200 and read.json()["data"]["age"] is None
    listed = await client.get(f"{API}/patients?search=Legacy", headers=auth_headers)
    assert listed.status_code == 200 and any(p["id"] == pid for p in listed.json()["data"])
    # Changing something else does not demand an age ...
    assert (await client.patch(url, headers=auth_headers, json={"chief_complaint": "knee"})).status_code == 200
    assert (await client.patch(url, headers=auth_headers, json={"status": "active"})).status_code == 200
    # ... but the age fields themselves can be filled in.
    assert (await client.patch(url, headers=auth_headers, json={"age": 62})).status_code == 200


# --------------------------------------------------------------------------
# 8. audit rows
# --------------------------------------------------------------------------
async def test_prescription_create_edit_delete_pdf_are_audited_without_clinical_text(client, db_session):
    clinic, admin, headers, patient, exercise = await make_clinic(db_session)
    note = "Patient has severe knee pain, avoid squats"
    created = await client.post(
        f"{API}/prescriptions", headers=headers,
        json={"patient_id": str(patient.id), "physio_notes": note,
              "items": [{"exercise_id": str(exercise.id), "sets": 3, "reps": 12, "note": "private item note"}]},
    )
    assert created.status_code == 201, created.text
    rx_id = created.json()["data"]["id"]
    [row] = await audit_rows(db_session, clinic.id, "prescription", "create")
    assert str(row.entity_id) == rx_id and row.user_id == admin.id
    assert row.details == {"patient_id": str(patient.id), "item_count": 1}

    edited = await client.patch(
        f"{API}/prescriptions/{rx_id}", headers=headers, json={"physio_notes": "new note text", "status": "completed"}
    )
    assert edited.status_code == 200, edited.text
    [update_row] = await audit_rows(db_session, clinic.id, "prescription", "update")
    assert update_row.details["fields"] == ["physio_notes", "status"]
    assert update_row.details["status"] == ["active", "completed"]

    pdf = await client.post(f"{API}/prescriptions/{rx_id}/pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert len(await audit_rows(db_session, clinic.id, "prescription", "generate_pdf")) == 1

    deleted = await client.delete(f"{API}/prescriptions/{rx_id}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert len(await audit_rows(db_session, clinic.id, "prescription", "delete")) == 1

    everything = str([r.details for r in await audit_rows(db_session, clinic.id, "prescription")])
    for secret in (note, "new note text", "private item note"):
        assert secret not in everything


async def test_soap_and_treatment_notes_are_audited_without_note_text(client, db_session):
    clinic, admin, headers, patient, _ex = await make_clinic(db_session)
    diagnosis = "Suspected ACL tear, secret diagnosis"
    soap = await client.post(
        f"{API}/assessments", headers=headers,
        json={"patient_id": str(patient.id), "therapist_id": str(admin.id), "specialty": "physiotherapy",
              "diagnosis": diagnosis, "form_data": {"subjective": "private answer"}},
    )
    assert soap.status_code == 201, soap.text
    soap_id = soap.json()["id"]
    edit = await client.patch(
        f"{API}/assessments/{soap_id}", headers=headers, json={"diagnosis": "changed text", "finalized": True}
    )
    assert edit.status_code == 200, edit.text
    [created_row] = await audit_rows(db_session, clinic.id, "soap_assessment", "create")
    assert created_row.details == {
        "patient_id": str(patient.id), "specialty": "physiotherapy", "is_reassessment": False, "finalized": False,
    }
    [edited_row] = await audit_rows(db_session, clinic.id, "soap_assessment", "update")
    assert edited_row.details["fields"] == ["diagnosis", "finalized"]
    assert edited_row.details["finalized"] == [False, True]

    note = "Manual therapy and ultrasound, private treatment text"
    treat = await client.post(
        f"{API}/treatments", headers=headers,
        json={"patient_id": str(patient.id), "therapist_id": str(admin.id),
              "treatment_date": datetime.now(timezone.utc).isoformat(), "treatment": note,
              "notes": "private notes", "pain_score": 7},
    )
    assert treat.status_code == 201, treat.text
    treat_id = treat.json()["id"]
    assert (await client.patch(f"{API}/treatments/{treat_id}", headers=headers, json={"notes": "edited private"})).status_code == 200
    assert (await client.delete(f"{API}/treatments/{treat_id}", headers=headers)).status_code == 204
    for action in ("create", "update", "delete"):
        assert len(await audit_rows(db_session, clinic.id, "treatment_session", action)) == 1, action

    everything = str(
        [r.details for r in await audit_rows(db_session, clinic.id, "soap_assessment")]
        + [r.details for r in await audit_rows(db_session, clinic.id, "treatment_session")]
    )
    for secret in (diagnosis, "changed text", "private answer", note, "private notes", "edited private"):
        assert secret not in everything
    assert "pain" not in everything


class FakeStorage:
    def __init__(self):
        self.uploaded: list[tuple[str, int]] = []

    def upload_file(self, path, data, content_type):
        self.uploaded.append((path, len(data)))
        return path

    def download_file(self, path):
        return b"x"


async def test_document_upload_and_delete_are_audited(client, db_session, monkeypatch):
    from app.core import storage

    fake = FakeStorage()
    monkeypatch.setattr(storage, "storage_client", fake)
    clinic, admin, headers, patient, _ex = await make_clinic(db_session, documents=True)
    up = await client.post(
        f"{API}/patients/{patient.id}/documents", headers=headers,
        data={"label": "Private label X-ray", "category": "x_ray_scan", "notes": "private notes"},
        files={"file": ("scan.pdf", b"%PDF-1.4 small", "application/pdf")},
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]
    assert fake.uploaded
    [row] = await audit_rows(db_session, clinic.id, "document", "upload")
    assert str(row.entity_id) == doc_id and row.user_id == admin.id
    assert row.details == {
        "patient_id": str(patient.id), "category": "x_ray_scan", "file_type": "application/pdf", "file_size": 14,
    }
    deleted = await client.delete(f"{API}/documents/{doc_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    [gone] = await audit_rows(db_session, clinic.id, "document", "delete")
    assert gone.details == {"patient_id": str(patient.id), "category": "x_ray_scan"}
    everything = str([r.details for r in await audit_rows(db_session, clinic.id, "document")])
    assert "Private label" not in everything and "private notes" not in everything


async def test_fee_list_changes_are_audited_with_before_after(client, db_session):
    clinic, admin, headers, _patient, _ex = await make_clinic(db_session)
    created = await client.post(
        f"{API}/settings/fee-items", headers=headers,
        json={"name": "Review visit", "category": "consultation", "default_price": "500.00"},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    [row] = await audit_rows(db_session, clinic.id, "fee_item", "create")
    assert row.details["name"] == "Review visit" and row.details["default_price"] == "500.00"
    patched = await client.patch(f"{API}/settings/fee-items/{item_id}", headers=headers, json={"default_price": "650.00"})
    assert patched.status_code == 200, patched.text
    [upd] = await audit_rows(db_session, clinic.id, "fee_item", "update")
    assert upd.details["changes"] == {"default_price": ["500.00", "650.00"]}
    assert (await client.delete(f"{API}/settings/fee-items/{item_id}", headers=headers)).status_code == 204
    [gone] = await audit_rows(db_session, clinic.id, "fee_item", "delete")
    assert gone.details == {"name": "Review visit"} and gone.user_id == admin.id


# --------------------------------------------------------------------------
# 9. upload size caps
# --------------------------------------------------------------------------
async def test_oversized_document_is_refused_with_413_and_nothing_stored(client, db_session, monkeypatch):
    from app.core import storage
    from app.core.upload_limits import MAX_DOCUMENT_BYTES

    fake = FakeStorage()
    monkeypatch.setattr(storage, "storage_client", fake)
    clinic, _admin, headers, patient, _ex = await make_clinic(db_session, documents=True)
    big = b"0" * (MAX_DOCUMENT_BYTES + 1)
    res = await client.post(
        f"{API}/patients/{patient.id}/documents", headers=headers,
        data={"label": "Too big", "category": "medical_report"},
        files={"file": ("big.pdf", big, "application/pdf")},
    )
    assert res.status_code == 413
    detail = res.json()["detail"]
    assert detail["code"] == "FILE_TOO_LARGE"
    assert "10 MB" in detail["message"] and "smaller" in detail["message"]
    assert fake.uploaded == []
    assert not await audit_rows(db_session, clinic.id, "document", "upload")

    exactly = b"0" * MAX_DOCUMENT_BYTES
    ok = await client.post(
        f"{API}/patients/{patient.id}/documents", headers=headers,
        data={"label": "Just fits", "category": "medical_report"},
        files={"file": ("ok.pdf", exactly, "application/pdf")},
    )
    assert ok.status_code == 201, ok.text


async def test_oversized_clinic_logo_is_refused_with_413(client, db_session):
    from app.core.upload_limits import MAX_LOGO_BYTES

    clinic, _admin, headers, _p, _e = await make_clinic(db_session)

    def uri(size: int) -> str:
        return "data:image/png;base64," + base64.b64encode(b"\x89PNG" + b"0" * (size - 4)).decode()

    res = await client.patch(f"{API}/settings/clinic", headers=headers, json={"branding_logo_url": uri(MAX_LOGO_BYTES + 3000)})
    assert res.status_code == 413
    assert res.json()["detail"]["code"] == "FILE_TOO_LARGE"
    assert "256 KB" in res.json()["detail"]["message"]
    ok = await client.patch(f"{API}/settings/clinic", headers=headers, json={"branding_logo_url": uri(MAX_LOGO_BYTES - 100)})
    assert ok.status_code == 200, ok.text
    # A normal https logo URL and clearing the logo still work.
    link = await client.patch(f"{API}/settings/clinic", headers=headers, json={"branding_logo_url": "https://example.com/logo.png"})
    assert link.status_code == 200
    cleared = await client.patch(f"{API}/settings/clinic", headers=headers, json={"branding_logo_url": None})
    assert cleared.status_code == 200
