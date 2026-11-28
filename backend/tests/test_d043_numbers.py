"""
D-043 document numbers (decided 26 Nov 2026) and the Round 4 clinic settings.

Clinical: <clinic code>-RX|POS|PSY-<6 digits>, per clinic per type, never
reset. Invoice INV-<FY>-<6 digits>, receipt RCP-<FY>-<6 digits> (one per
payment), per clinic per Indian financial year, at most 16 characters.
Numbers are made on the server only and are safe under concurrency.
"""

from __future__ import annotations

import asyncio
import base64
import io
import uuid
from datetime import date, datetime, timezone

import pytest
from PIL import Image
from sqlalchemy import select

from app.models.billing import Payment
from app.models.document_numbering import DocumentCounter, PsychosocialReport
from app.models.prescription import Prescription
from app.services import document_numbers as dn
from tests.test_be_fixes import API, make_clinic


# ---------------------------------------------------------------- pure helpers


@pytest.mark.parametrize(
    "moment, fy",
    [
        (date(2026, 4, 1), "2627"),
        (date(2026, 3, 31), "2526"),
        (date(2027, 3, 31), "2627"),
        (date(2099, 12, 1), "9900"),
        # 31 Mar 23:30 IST is 18:00 UTC: still the old year.
        (datetime(2027, 3, 31, 18, 0, tzinfo=timezone.utc), "2627"),
        # 1 Apr 00:10 IST is 31 Mar 18:40 UTC: already the new year.
        (datetime(2027, 3, 31, 18, 40, tzinfo=timezone.utc), "2728"),
        (datetime(2027, 3, 31, 18, 40), "2728"),  # naive = UTC
    ],
)
def test_financial_year_is_indian_april_to_march_in_ist(moment, fy):
    assert dn.financial_year(moment) == fy


def test_formats_and_16_character_limit():
    assert dn.format_clinical("asc2", "RX", 14) == "ASC2-RX-000014"
    assert dn.format_financial("INV", "2627", 3) == "INV-2627-000003"
    assert len(dn.format_financial("RCP", "2627", 9_999_999)) == 16
    with pytest.raises(dn.DocumentNumberError):
        dn.format_financial("INV", "2627", 10_000_000)


# ---------------------------------------------------------------- counter


async def test_twenty_concurrent_rx_numbers_are_unique_and_gapless(db_session, sessionmaker):
    clinic, *_ = await make_clinic(db_session)

    async def take():
        async with sessionmaker() as session:
            number = await dn.next_clinical_number(session, clinic.id, clinic.code, dn.RX)
            await session.commit()
            return number

    numbers = await asyncio.gather(*(take() for _ in range(20)))
    assert sorted(numbers) == [f"{clinic.code}-RX-{n:06d}" for n in range(1, 21)]


async def test_rolled_back_number_is_not_used_up(db_session, sessionmaker):
    clinic, *_ = await make_clinic(db_session)
    async with sessionmaker() as session:
        await dn.next_number(session, clinic.id, dn.PSY)
        await session.rollback()
    async with sessionmaker() as session:
        assert await dn.next_number(session, clinic.id, dn.PSY) == 1


async def test_counter_never_falls_behind_numbers_already_stored(db_session):
    clinic, admin, _h, patient, _e = await make_clinic(db_session)
    db_session.add(Prescription(clinic_id=clinic.id, patient_id=patient.id, physio_id=admin.id,
                                number=f"{clinic.code}-RX-000050"))
    await db_session.commit()
    assert await dn.next_clinical_number(db_session, clinic.id, clinic.code, dn.RX) == f"{clinic.code}-RX-000051"


async def test_financial_counters_restart_each_year_and_per_type(db_session):
    clinic, *_ = await make_clinic(db_session)
    march = datetime(2027, 3, 31, 12, 0, tzinfo=timezone.utc)
    april = datetime(2027, 4, 1, 12, 0, tzinfo=timezone.utc)
    got = [
        await dn.next_financial_number(db_session, clinic.id, dn.INV, march),
        await dn.next_financial_number(db_session, clinic.id, dn.INV, march),
        await dn.next_financial_number(db_session, clinic.id, dn.INV, april),
        await dn.next_financial_number(db_session, clinic.id, dn.RCP, april),
    ]
    assert got == ["INV-2627-000001", "INV-2627-000002", "INV-2728-000001", "RCP-2728-000001"]
    periods = {(c.doc_type, c.period) for c in (await db_session.scalars(
        select(DocumentCounter).where(DocumentCounter.clinic_id == clinic.id))).all()}
    assert periods == {("INV", "2627"), ("INV", "2728"), ("RCP", "2728")}


async def test_clinical_number_needs_a_clinic_code(db_session):
    clinic, *_ = await make_clinic(db_session)
    with pytest.raises(ValueError):
        await dn.next_clinical_number(db_session, clinic.id, " ", dn.RX)


# ---------------------------------------------------------------- wired in


async def test_prescription_gets_its_number_on_create(client, db_session):
    clinic, _a, headers, patient, exercise = await make_clinic(db_session)
    body = {"patient_id": str(patient.id), "items": [{"exercise_id": str(exercise.id), "sets": 3, "reps": 10}]}
    first = await client.post(f"{API}/prescriptions", headers=headers, json=body)
    second = await client.post(f"{API}/prescriptions", headers=headers, json={**body, "number": "HACK-1"})
    assert first.status_code == 201, first.text
    assert first.json()["data"]["number"] == f"{clinic.code}-RX-000001"
    assert second.json()["data"]["number"] == f"{clinic.code}-RX-000002"


async def test_psychosocial_export_gets_a_row_and_number_each_time(db_session):
    from app.services import psychosocial_report as report

    clinic, admin, _h, patient, _e = await make_clinic(db_session)
    one = await report._new_report_number(db_session, clinic, patient.id, admin.id)
    two = await report._new_report_number(db_session, clinic, patient.id, admin.id)
    await db_session.commit()
    assert (one, two) == (f"{clinic.code}-PSY-000001", f"{clinic.code}-PSY-000002")
    rows = (await db_session.scalars(select(PsychosocialReport).where(PsychosocialReport.clinic_id == clinic.id))).all()
    assert sorted(r.number for r in rows) == [one, two]


async def _invoice(client, headers, patient_id, total="900.00"):
    res = await client.post(f"{API}/invoices", headers=headers, json={
        "patient_id": str(patient_id), "issue_date": "2026-11-20T06:00:00Z",
        "items": [{"description": "Session", "quantity": 1, "unit_price": total}],
    })
    assert res.status_code == 201, res.text
    return res.json()


async def _pay(client, headers, inv, patient_id, amount, when="2026-11-21T06:00:00Z"):
    res = await client.post(f"{API}/invoices/{inv['id']}/payments", headers=headers, json={
        "invoice_id": inv["id"], "patient_id": str(patient_id), "amount": amount,
        "payment_method": "cash", "payment_date": when,
    })
    assert res.status_code == 201, res.text
    return res.json()


async def test_receipt_per_payment(client, db_session):
    from pypdf import PdfReader

    clinic, _a, headers, patient, _e = await make_clinic(db_session)
    inv = await _invoice(client, headers, patient.id)
    assert inv["invoice_number"] == "INV-2627-000001"
    p1 = await _pay(client, headers, inv, patient.id, "300.00")
    p2 = await _pay(client, headers, inv, patient.id, "200.00")
    assert (p1["receipt_number"], p2["receipt_number"]) == ("RCP-2627-000001", "RCP-2627-000002")

    url = f"{API}/invoices/{inv['id']}/pdf/download"
    for pay, amount in ((p1, "300.00"), (p2, "200.00")):
        res = await client.get(url, headers=headers, params={"kind": "receipt", "payment_id": pay["id"]})
        assert res.status_code == 200, res.text
        assert f'filename="Receipt-{pay["receipt_number"]}.pdf"' in res.headers["content-disposition"]
        text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages)
        assert pay["receipt_number"] in text and f"Rs. {amount}" in text
    # Old button, no payment_id: the latest completed payment, as before.
    latest = await client.get(url, headers=headers, params={"kind": "receipt"})
    assert f'Receipt-{p2["receipt_number"]}.pdf' in latest.headers["content-disposition"]
    # A payment of another invoice is a 404.
    other = await _invoice(client, headers, patient.id, "100.00")
    p3 = await _pay(client, headers, other, patient.id, "100.00")
    wrong = await client.get(url, headers=headers, params={"kind": "receipt", "payment_id": p3["id"]})
    assert wrong.status_code == 404
    # The number is stored on the payment row and listed.
    listed = await client.get(f"{API}/payments", headers=headers, params={"invoice_id": inv["id"]})
    assert {p["receipt_number"] for p in listed.json()["items"]} == {"RCP-2627-000001", "RCP-2627-000002"}
    row = await db_session.get(Payment, uuid.UUID(p1["id"]))
    await db_session.refresh(row)
    assert row.receipt_number == "RCP-2627-000001"


async def test_receipt_of_payment_from_before_d043_keeps_the_invoice_number(client, db_session):
    clinic, _a, headers, patient, _e = await make_clinic(db_session)
    inv = await _invoice(client, headers, patient.id)
    pay = await _pay(client, headers, inv, patient.id, "100.00")
    row = await db_session.get(Payment, uuid.UUID(pay["id"]))
    row.receipt_number = None  # as migrated payments are
    await db_session.commit()
    res = await client.get(f"{API}/invoices/{inv['id']}/pdf/download", headers=headers,
                           params={"kind": "receipt", "payment_id": pay["id"]})
    assert f'Receipt-{inv["invoice_number"]}.pdf' in res.headers["content-disposition"]


# ---------------------------------------------------------------- settings + logo rules


def _logo(size=(600, 300), fmt="PNG", color=(20, 90, 160, 255), mode="RGBA") -> str:
    buf = io.BytesIO()
    img = Image.new(mode, size, color if mode == "RGBA" else color[:3])
    img.save(buf, format=fmt)
    mime = {"PNG": "png", "JPEG": "jpeg", "WEBP": "webp", "GIF": "gif"}[fmt]
    return f"data:image/{mime};base64," + base64.b64encode(buf.getvalue()).decode()


async def test_settings_round4_fields(client, db_session):
    clinic, admin, headers, *_ = await make_clinic(db_session)
    res = await client.patch(f"{API}/settings/clinic", headers=headers, json={
        "display_doctor_name": "  Dr. Meera Rao (PT) ", "website": "www.meera-physio.in", "logo_bg_mode": "white",
    })
    assert res.status_code == 200, res.text
    out = res.json()
    assert (out["display_doctor_name"], out["website"], out["logo_bg_mode"]) == (
        "Dr. Meera Rao (PT)", "www.meera-physio.in", "white")
    got = (await client.get(f"{API}/settings/clinic", headers=headers)).json()
    assert got["logo_bg_mode"] == "white" and got["logo_low_contrast"] is False
    # Blank = not set; the report header then shows the owner admin's name.
    cleared = await client.patch(f"{API}/settings/clinic", headers=headers, json={"display_doctor_name": "  ", "website": ""})
    assert cleared.json()["display_doctor_name"] is None and cleared.json()["website"] is None
    from app.services.clinic_brand import display_doctor_name

    await db_session.refresh(clinic)
    assert await display_doctor_name(db_session, clinic) == "Be Fix"


@pytest.mark.parametrize("body", [
    {"website": "not a website"},
    {"website": "javascript:alert(1)"},
    {"logo_bg_mode": "blur"},
    {"logo_bg_mode": None},
    {"display_doctor_name": "x" * 256},
])
async def test_settings_round4_validation(client, db_session, body):
    _c, _a, headers, *_ = await make_clinic(db_session)
    res = await client.patch(f"{API}/settings/clinic", headers=headers, json=body)
    assert res.status_code == 422, res.text


@pytest.mark.parametrize("logo, status, code", [
    (_logo((150, 400)), 422, "LOGO_TOO_SMALL"),
    (_logo((1000, 200)), 422, "LOGO_ASPECT"),
    (_logo((400, 400), "GIF", mode="RGB"), 422, "LOGO_FORMAT"),
    ("data:image/svg+xml;base64," + base64.b64encode(b"<svg/>").decode(), 422, "LOGO_FORMAT"),
])
async def test_logo_upload_rules(client, db_session, logo, status, code):
    _c, _a, headers, *_ = await make_clinic(db_session)
    res = await client.patch(f"{API}/settings/clinic", headers=headers, json={"branding_logo_url": logo})
    assert res.status_code == status, res.text
    assert res.json()["detail"]["code"] == code
    preview = await client.post(f"{API}/settings/clinic/logo-preview", headers=headers, json={"logo": logo})
    assert preview.status_code == status and preview.json()["detail"]["code"] == code


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
async def test_logo_formats_are_resized_and_stored_small(client, db_session, fmt):
    from app.core.upload_limits import MAX_LOGO_BYTES

    _c, _a, headers, *_ = await make_clinic(db_session)
    # Busy, photo-like pictures: the hardest case for the 256 KB stored copy.
    noisy = Image.effect_noise((1200, 1200), 90).convert("L" if fmt == "PNG" else "RGB")
    buf = io.BytesIO()
    noisy.save(buf, format=fmt, quality=85)
    assert len(buf.getvalue()) < 2 * 1024 * 1024
    uri = f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()
    res = await client.patch(f"{API}/settings/clinic", headers=headers, json={"branding_logo_url": uri})
    assert res.status_code == 200, res.text
    stored = res.json()["branding_logo_url"]
    raw = base64.b64decode(stored.split(",", 1)[1])
    assert len(raw) <= MAX_LOGO_BYTES
    with Image.open(io.BytesIO(raw)) as img:
        assert max(img.size) <= 800 and min(img.size) >= 200


async def test_logo_preview_three_modes_and_contrast_warning(client, db_session):
    _c, _a, headers, *_ = await make_clinic(db_session)
    # Dark navy text on a white canvas: removed background leaves dark on teal.
    img = Image.new("RGB", (800, 300), "white")
    img.paste(Image.new("RGB", (600, 120), (12, 18, 56)), (100, 90))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    seen = {}
    for mode in ("as_is", "white", "transparent"):
        res = await client.post(f"{API}/settings/clinic/logo-preview", headers=headers,
                                json={"logo": uri, "logo_bg_mode": mode})
        assert res.status_code == 200, res.text
        seen[mode] = res.json()
    assert seen["white"]["low_contrast"] is False  # the white tile always reads
    assert seen["transparent"]["low_contrast"] is True
    # Background removed: the plain white margin is gone and the canvas is trimmed.
    t = seen["transparent"]
    assert t["width"] / t["height"] > seen["as_is"]["width"] / seen["as_is"]["height"]
    with Image.open(io.BytesIO(base64.b64decode(t["letterhead_logo"].split(",", 1)[1]))) as out:
        assert out.mode == "RGBA" and out.getchannel("A").getextrema()[0] == 0
    # Saving with the mode keeps the warning on the settings response.
    saved = await client.patch(f"{API}/settings/clinic", headers=headers,
                               json={"branding_logo_url": uri, "logo_bg_mode": "transparent"})
    assert saved.json()["logo_low_contrast"] is True


async def test_logo_preview_needs_settings_edit(client, db_session, therapist_auth_headers):
    res = await client.post(f"{API}/settings/clinic/logo-preview", headers=therapist_auth_headers,
                            json={"logo": _logo()})
    assert res.status_code == 403
