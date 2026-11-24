"""clinics.code and the Patient ID on PDFs / WhatsApp texts (delivery item 10, 24 Nov 2026)."""

import importlib.util
import io
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pypdf import PdfReader
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.clinic import Clinic
from app.services import prescription_service
from app.services.clinic_code import derive_clinic_code, next_free_code, normalize_clinic_code
from app.services.invoice_pdf import InvoiceDoc, build_invoice_html
from app.services.patient_number import format_patient_id
from app.services.prescription_pdf import RxDoc, RxItem, build_prescription_html

API = settings.API_V1_PREFIX


def _pdf_text(pdf: bytes) -> str:
    return " ".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)


def _squash(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


# ------------------------------------------------------------------ rule


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Aarogya Dhara Physio", "ADP"),
        ("Spine & Care Clinic Noida", "SCC"),
        ("SpineAct", "SPI"),
        ("Physio", "PHY"),
        ("A", "A"),
        ("Dr. Rao's Clinic", "DRS"),
        ("123 456", "PT"),
        ("सेहत", "PT"),
        ("   ", "PT"),
        (None, "PT"),
    ],
)
def test_derive_matches_the_old_frontend_rule(name, expected):
    # Mirrors frontend/crm/src/lib/patientNumber.ts (the apostrophe splits a word).
    assert derive_clinic_code(name) == expected


def test_next_free_code_adds_a_number_and_stays_within_six():
    assert next_free_code("ADP", set()) == "ADP"
    assert next_free_code("ADP", {"ADP"}) == "ADP2"
    assert next_free_code("ADP", {"ADP", "ADP2"}) == "ADP3"
    assert next_free_code("ABCDEF", {"ABCDEF"}) == "ABCDE2"


@pytest.mark.parametrize("raw,ok", [("adp", "ADP"), (" Adp1 ", "ADP1"), ("A", "A"), ("ABCDEF", "ABCDEF")])
def test_normalize_accepts(raw, ok):
    assert normalize_clinic_code(raw) == ok


@pytest.mark.parametrize("raw", ["", "   ", "ABCDEFG", "AB-C", "AB C", "ए बी", "A_B", "AB!"])
def test_normalize_rejects(raw):
    with pytest.raises(ValueError):
        normalize_clinic_code(raw)


def test_format_patient_id():
    assert format_patient_id("ADP", 3) == "ADP-000003"
    assert format_patient_id("ADP", 1234567) == "ADP-1234567"
    assert format_patient_id(None, 3) == ""
    assert format_patient_id("ADP", None) == ""


# ------------------------------------------------------------------ new clinics


@pytest.mark.asyncio
async def test_new_clinics_get_a_code_and_never_share_one(db_session):
    one = Clinic(name="Zeta Omega Physio")
    two = Clinic(name="Zeta Omega Physio")
    db_session.add_all([one, two])
    await db_session.flush()  # both in the same flush
    three = Clinic(name="Zeta Omega Physio")
    db_session.add(three)
    await db_session.flush()
    codes = {one.code, two.code, three.code}
    assert len(codes) == 3
    assert all(c.startswith("ZOP") for c in codes)
    explicit = Clinic(name="Zeta Omega Physio", code="MYCODE")
    db_session.add(explicit)
    await db_session.flush()
    assert explicit.code == "MYCODE"
    await db_session.rollback()


# ------------------------------------------------------------------ Settings API


@pytest.mark.asyncio
async def test_settings_and_me_return_the_code(client, auth_headers):
    me = await client.get(f"{API}/auth/me", headers=auth_headers)
    code = me.json()["data"]["clinic"]["code"]
    assert re.fullmatch(r"[A-Z0-9]{1,6}", code)
    got = await client.get(f"{API}/settings/clinic", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["code"] == code


@pytest.mark.asyncio
async def test_admin_edits_code_validation_and_uniqueness(client, auth_headers, therapist_auth_headers, db_session):
    original = (await client.get(f"{API}/settings/clinic", headers=auth_headers)).json()["code"]
    other = Clinic(name="Other Clinic For Code Test", code="TAKEN1")
    db_session.add(other)
    await db_session.commit()
    url = f"{API}/settings/clinic"
    try:
        # lower case and spaces are tidied
        ok = await client.patch(url, json={"code": " abc12 "}, headers=auth_headers)
        assert ok.status_code == 200, ok.text
        assert ok.json()["code"] == "ABC12"
        assert (await client.get(f"{API}/auth/me", headers=auth_headers)).json()["data"]["clinic"]["code"] == "ABC12"

        # the same code again is not a conflict with itself
        again = await client.patch(url, json={"code": "ABC12"}, headers=auth_headers)
        assert again.status_code == 200

        for bad in ("", "   ", "ABCDEFG", "AB-1", "AB 1", None, 5):
            res = await client.patch(url, json={"code": bad}, headers=auth_headers)
            assert res.status_code == 422, (bad, res.text)

        taken = await client.patch(url, json={"code": "taken1"}, headers=auth_headers)
        assert taken.status_code == 400
        assert "already used" in taken.text
        # nothing changed by the failed attempts
        assert (await client.get(url, headers=auth_headers)).json()["code"] == "ABC12"

        # other fields alone leave the code untouched
        other_field = await client.patch(url, json={"city": "Noida"}, headers=auth_headers)
        assert other_field.json()["code"] == "ABC12"

        # a therapist cannot edit
        denied = await client.patch(url, json={"code": "NOPE"}, headers=therapist_auth_headers)
        assert denied.status_code == 403

        audit = await db_session.scalars(
            select(AuditLog).where(AuditLog.entity_type == "clinic", AuditLog.action == "update")
        )
        assert any((a.details or {}).get("code") == "ABC12" for a in audit)
    finally:
        await client.patch(url, json={"code": original}, headers=auth_headers)
        await db_session.delete(other)
        await db_session.commit()


@pytest.mark.asyncio
async def test_patient_id_on_invoice_and_receipt_pdf_and_whatsapp(client, auth_headers):
    code = (await client.get(f"{API}/settings/clinic", headers=auth_headers)).json()["code"]
    patient = (
        await client.post(
            f"{API}/patients",
            json={"first_name": "Isha", "last_name": "Verma", "phone": "9898765022", "age": 31},
            headers=auth_headers,
        )
    ).json()["data"]
    expected = f"{code}-{patient['display_number']:06d}"
    created = await client.post(
        f"{API}/invoices",
        json={
            "patient_id": patient["id"],
            "issue_date": "2026-10-20T20:30:00Z",
            "due_date": "2026-10-30T06:00:00Z",
            "items": [{"description": "Session", "quantity": 1, "unit_price": "500.00"}],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    invoice = created.json()
    for kind in ("invoice", "receipt"):
        res = await client.get(
            f"{API}/invoices/{invoice['id']}/pdf/download", params={"kind": kind}, headers=auth_headers
        )
        assert res.status_code == 200, res.text
        body = _squash(_pdf_text(res.content))
        assert _squash("Patient ID") in body
        assert _squash(expected) in body
    sent = await client.post(f"{API}/invoices/{invoice['id']}/pdf", headers=auth_headers)
    assert sent.status_code == 200, sent.text
    assert f"Patient%20ID%3A%20{expected}" in sent.json()["whatsapp_link"]


# ------------------------------------------------------------------ templates


def _invoice(**kw):
    base = dict(
        kind="invoice", invoice_number="INV-1", status="issued", issue_date=None, due_date=None,
        clinic_name="Grove Physio", patient_name="Jane Doe",
    )
    base.update(kw)
    return InvoiceDoc(**base)


@pytest.mark.parametrize("kind", ["invoice", "receipt"])
def test_invoice_html_shows_patient_id_label_and_value(kind):
    html = build_invoice_html(_invoice(kind=kind, patient_id="ADP-000003"))
    assert "Patient ID" in html and "ADP-000003" in html
    assert html.index("Jane Doe") < html.index("Patient ID") < html.index("ADP-000003")


def test_invoice_html_without_patient_id_has_no_empty_label():
    assert "Patient ID" not in build_invoice_html(_invoice())


def _rx(**kw):
    base = dict(
        rx_id=str(uuid.uuid4()), clinic_name="Grove Physio", physio_name="Asha Rao",
        patient_name="Jane Doe", patient_phone="9876543210", patient_dob=date(1990, 1, 1),
        prescribed_on=datetime(2026, 10, 19, 20, 0, tzinfo=timezone.utc), physio_notes=None,
        items=[RxItem("Bridge", "Hip", "", 3, 10, 0, "Daily", None, None, image_src="")],
    )
    base.update(kw)
    return RxDoc(**base)


def test_rx_html_shows_patient_id_label_and_value():
    html = build_prescription_html(_rx(patient_id="ADP-000003"))
    assert "Patient ID" in html and "ADP-000003" in html
    assert html.index("Patient name") < html.index("Patient ID")


def test_rx_html_without_patient_id_leaves_the_row_out():
    assert "Patient ID" not in build_prescription_html(_rx())


def test_prescription_whatsapp_text():
    with_id = prescription_service._build_prescription_message("Jane", "Grove", "ADP-000003")
    assert "Patient ID: ADP-000003" in with_id
    assert "Patient ID" not in prescription_service._build_prescription_message("Jane", "Grove")


# ------------------------------------------------------------------ migration


@pytest.mark.asyncio
async def test_migration_backfills_code_from_name_and_numbers_duplicates(engine, setup_db):
    if make_url(settings.TEST_DATABASE_URL or settings.DATABASE_URL).get_backend_name() != "postgresql":
        pytest.skip("PostgreSQL required to exercise the migration")
    path = Path(__file__).parents[1] / "alembic/versions/20261124_clinics_code.py"
    spec = importlib.util.spec_from_file_location("clinics_code_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    schema = f"clinics_code_{uuid.uuid4().hex}"
    names = [
        ("Aarogya Dhara Physio", 1),
        ("Anand Dental Practice", 2),
        ("Physio", 3),
        ("सेहत", 4),
        ("Spine & Care Clinic Noida", 5),
        ("Another Dhaam Place", 6),
    ]
    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        await connection.execute(text(
            "CREATE TABLE clinics (id uuid PRIMARY KEY, name varchar(255) NOT NULL, created_at timestamptz NOT NULL)"
        ))
        for index, (name, created) in enumerate(names, start=1):
            await connection.execute(
                text("INSERT INTO clinics (id, name, created_at) VALUES (:id, :n, :c)"),
                {"id": f"10000000-0000-0000-0000-00000000000{index}", "n": name, "c": datetime(2026, 1, created, tzinfo=timezone.utc)},
            )

        def run(sync_connection, fn):
            with Operations.context(MigrationContext.configure(sync_connection)):
                fn()

        await connection.run_sync(run, migration.upgrade)
        rows = (await connection.execute(text("SELECT name, code FROM clinics ORDER BY created_at"))).all()
        assert [r.code for r in rows] == ["ADP", "ADP2", "PHY", "PT", "SCC", "ADP3"]
        # the same value the running code would give a new clinic
        assert [derive_clinic_code(n) for n, _ in names][:4] == ["ADP", "ADP", "PHY", "PT"]
        nullable = await connection.scalar(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_schema = :s AND table_name = 'clinics' AND column_name = 'code'"
        ), {"s": schema})
        assert nullable == "NO"
        with pytest.raises(Exception):
            async with connection.begin_nested():
                await connection.execute(text("UPDATE clinics SET code = 'ADP' WHERE code = 'PHY'"))

        await connection.run_sync(run, migration.downgrade)
        cols = (await connection.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = :s AND table_name = 'clinics'"
        ), {"s": schema})).scalars().all()
        assert "code" not in cols
        assert (await connection.scalar(text("SELECT count(*) FROM clinics"))) == len(names)
        await connection.run_sync(run, migration.upgrade)
        again = (await connection.execute(text("SELECT code FROM clinics ORDER BY created_at"))).scalars().all()
        assert again == ["ADP", "ADP2", "PHY", "PT", "SCC", "ADP3"]
        await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.asyncio
async def test_prescription_pdf_and_whatsapp_carry_the_patient_id(client, db_session, monkeypatch):
    from tests.test_prescription_pdf import _FakeStorage, _create_rx, _setup

    storage = _FakeStorage()
    monkeypatch.setattr(prescription_service, "_storage_client", lambda: storage)
    clinic, _user, patient, exercise, headers = await _setup(db_session)
    rx_id = await _create_rx(client, headers, patient, exercise)
    expected = f"{clinic.code}-{patient.display_number:06d}"

    gen = await client.post(f"{API}/prescriptions/{rx_id}/pdf", headers=headers)
    assert gen.status_code == 200, gen.text
    assert f"Patient%20ID%3A%20{expected}" in gen.json()["data"]["whatsapp_link"]
    dl = await client.get(f"{API}/prescriptions/{rx_id}/pdf/download", headers=headers)
    assert dl.status_code == 200
    body = _squash(_pdf_text(dl.content))
    assert _squash("Patient ID") in body and _squash(expected) in body
