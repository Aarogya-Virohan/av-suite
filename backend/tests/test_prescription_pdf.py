"""Prescription PDF: template, image embedding, storage and download.

Covers the redesign of 20 October 2026: images fetched in parallel and
embedded (no remote URL left for WeasyPrint), IST dates, durable storage with
a local fallback, regeneration when the stored file is gone, the download
file name, and clinic and OWN scope checks on the download endpoint.
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import date, datetime, timezone

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.enums.permission import CapabilityScope
from app.enums.product import EntitlementStatus
from app.enums.user import UserRole
from app.models.clinic import Clinic
from app.models.exercise import Exercise
from app.models.membership import Membership
from app.models.patient import Patient
from app.models.product import WorkspaceProduct
from app.models.user import User
from app.models.user_permission import UserPermission
from app.services import prescription_pdf, prescription_service
from app.services.prescription_pdf import (
    RxDoc,
    RxItem,
    build_prescription_html,
    embed_images,
    ist_date,
    pdf_filename,
)

pytestmark = pytest.mark.asyncio


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), (20, 120, 80, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _doc(**overrides) -> RxDoc:
    base = dict(
        rx_id=str(uuid.uuid4()),
        clinic_name="Grove <Physio>",
        physio_name="Asha Rao",
        patient_name="Priya <b>Sharma</b>",
        patient_phone="9876543210",
        patient_dob=date(1990, 10, 21),
        prescribed_on=datetime(2026, 10, 19, 20, 0, tzinfo=timezone.utc),
        physio_notes="Go slow",
        items=[
            RxItem("Chin tucks", "Neck", "Sit tall", 3, 10, 5, "Twice daily", "Relax <shoulders>",
                   "https://example.com/a.png", image_src=""),
        ],
    )
    base.update(overrides)
    return RxDoc(**base)


# ---------------------------------------------------------------- template


async def test_html_escapes_and_uses_ist_date() -> None:
    out = build_prescription_html(_doc())
    assert "<b>Sharma</b>" not in out and "Priya &lt;b&gt;Sharma&lt;/b&gt;" in out
    assert "Grove &lt;Physio&gt;" in out
    assert "Relax &lt;shoulders&gt;" in out
    # 20:00 UTC on 19 Oct is 01:30 IST on 20 Oct.
    assert "20 Oct 2026" in out
    # Age on the IST date: born 21 Oct 1990, so still 35 on 20 Oct 2026.
    assert ">35 Y<" in out
    # Remote image URLs never reach WeasyPrint.
    assert "https://example.com/a.png" not in out
    assert "Image not available" in out


async def test_ist_date_and_filename() -> None:
    assert ist_date(datetime(2026, 10, 19, 18, 29, tzinfo=timezone.utc)) == date(2026, 10, 19)
    assert ist_date(datetime(2026, 10, 19, 18, 30, tzinfo=timezone.utc)) == date(2026, 10, 20)
    assert pdf_filename("priya sharma-k", date(2026, 10, 20)) == "Rx_PriyaSharmaK_20Oct2026.pdf"
    assert pdf_filename("", date(2026, 1, 5)) == "Rx_Patient_05Jan2026.pdf"


# ---------------------------------------------------------------- images


@pytest.fixture(autouse=True)
def _public_hosts(monkeypatch: pytest.MonkeyPatch):
    """No DNS in tests: treat every host as public unless a test says otherwise."""
    prescription_pdf._image_cache.clear()
    monkeypatch.setattr(prescription_pdf, "_is_public_host", lambda host: host != "internal.test")
    yield
    prescription_pdf._image_cache.clear()


async def test_embed_images_parallel_resize_cache_and_rejects() -> None:
    big = _png(2000, 1500)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "https://img.test/big.png"})
        if request.url.path == "/missing":
            return httpx.Response(404)
        if request.url.path == "/notimage":
            return httpx.Response(200, content=b"not an image")
        return httpx.Response(200, content=big)

    transport = httpx.MockTransport(handler)
    urls = [
        "https://img.test/big.png",
        "https://img.test/redirect",
        "https://img.test/missing",
        "https://img.test/notimage",
        "http://img.test/plain-http.png",
        "https://internal.test/x.png",
    ]
    result = await embed_images(urls, transport=transport)

    ok = result["https://img.test/big.png"]
    assert ok.startswith("data:image/jpeg;base64,")
    import base64

    with Image.open(io.BytesIO(base64.b64decode(ok.split(",", 1)[1]))) as img:
        assert max(img.size) <= prescription_pdf.IMAGE_MAX_PX
    assert result["https://img.test/redirect"].startswith("data:image/jpeg")
    assert result["https://img.test/missing"] == ""
    assert result["https://img.test/notimage"] == ""
    assert result["http://img.test/plain-http.png"] == ""  # https only
    assert result["https://internal.test/x.png"] == ""  # private host
    assert not any("internal.test" in c or c.startswith("http://") for c in calls)

    # Second call is served from the cache.
    before = len(calls)
    again = await embed_images(["https://img.test/big.png"], transport=transport)
    assert again["https://img.test/big.png"] == ok
    assert len(calls) == before


async def test_embed_images_size_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prescription_pdf, "IMAGE_MAX_BYTES", 1000)
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=_png(400, 400) + b"\0" * 5000))
    result = await embed_images(["https://img.test/huge.png"], transport=transport)
    assert result["https://img.test/huge.png"] == ""


# ---------------------------------------------------------------- API


async def _setup(db: AsyncSession, role: UserRole = UserRole.ADMIN):
    clinic = Clinic(name=f"PDF Clinic {uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(), clinic_id=None, email=f"pdf-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=role, first_name="Asha", last_name="Rao", is_active=True,
    )
    db.add_all([clinic, user])
    await db.flush()
    user.clinic_id = clinic.id
    db.add(Membership(user_id=user.id, clinic_id=clinic.id, role=role))
    db.add(WorkspaceProduct(clinic_id=clinic.id, product_id="exercise-prescription",
                            status=EntitlementStatus.ENABLED))
    patient = Patient(clinic_id=clinic.id, first_name="Priya", last_name="Sharma", phone="9876543210")
    exercise = Exercise(clinic_id=clinic.id, title="Bridge", body_part="Hip", is_free=True)
    db.add_all([patient, exercise])
    await db.commit()
    token = create_access_token(subject=user.id, clinic_id=clinic.id, role=role.value)
    return clinic, user, patient, exercise, {"Authorization": f"Bearer {token}"}


async def _create_rx(client: AsyncClient, headers, patient, exercise) -> str:
    resp = await client.post(
        f"{settings.API_V1_PREFIX}/prescriptions",
        headers=headers,
        json={"patient_id": str(patient.id),
              "items": [{"exercise_id": str(exercise.id), "sets": 3, "reps": 10, "hold": 0,
                         "frequency": "Once daily"}]},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


class _FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def upload_file(self, path: str, data: bytes, content_type: str) -> str:
        assert content_type == "application/pdf"
        self.files[path] = data
        return path

    def download_file(self, path: str) -> bytes:
        from app.core.storage import StorageUnavailableError

        if path not in self.files:
            raise StorageUnavailableError()
        return self.files[path]


async def test_pdf_goes_to_storage_and_downloads_with_filename(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _FakeStorage()
    monkeypatch.setattr(prescription_service, "_storage_client", lambda: storage)
    clinic, _user, patient, exercise, headers = await _setup(db_session)
    rx_id = await _create_rx(client, headers, patient, exercise)

    gen = await client.post(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf", headers=headers)
    assert gen.status_code == 200, gen.text
    body = gen.json()["data"]
    assert body["pdf_url"] == f"/api/v1/prescriptions/{rx_id}/pdf/download"
    assert body["filename"].startswith("Rx_PriyaSharma_") and body["filename"].endswith(".pdf")
    assert "%2Fapi%2Fv1" not in body["whatsapp_link"]

    key = f"prescriptions/{clinic.id}/{rx_id}.pdf"
    assert list(storage.files) == [key]
    assert storage.files[key][:5] == b"%PDF-"

    # pdf_key in the DB, not just a 200.
    from app.models.prescription import Prescription

    db_session.expire_all()
    stored = await db_session.get(Prescription, uuid.UUID(rx_id))
    assert stored.pdf_key == key

    dl = await client.get(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf/download", headers=headers)
    assert dl.status_code == 200
    assert dl.content == storage.files[key]
    assert dl.headers["content-type"] == "application/pdf"
    assert f'filename="{body["filename"]}"' in dl.headers["content-disposition"]
    assert dl.headers["content-disposition"].startswith("attachment")

    # File lost from storage: download regenerates instead of 404.
    storage.files.clear()
    dl2 = await client.get(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf/download", headers=headers)
    assert dl2.status_code == 200 and dl2.content[:5] == b"%PDF-"
    assert key in storage.files


async def test_local_fallback_and_regenerate_after_redeploy(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prescription_service, "_storage_client", lambda: None)
    _clinic, _user, patient, exercise, headers = await _setup(db_session)
    rx_id = await _create_rx(client, headers, patient, exercise)

    # Never generated: the download still has no key, so 404 as before.
    none_yet = await client.get(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf/download", headers=headers)
    assert none_yet.status_code == 404

    gen = await client.post(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf", headers=headers)
    assert gen.status_code == 200
    path = os.path.join("static", "prescriptions", f"prescription_{rx_id}.pdf")
    assert os.path.exists(path)

    os.remove(path)  # what a Railway redeploy does to the local disk
    dl = await client.get(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf/download", headers=headers)
    assert dl.status_code == 200 and dl.content[:5] == b"%PDF-"
    os.remove(path)


async def test_download_is_clinic_scoped_and_own_scoped(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _FakeStorage()
    monkeypatch.setattr(prescription_service, "_storage_client", lambda: storage)
    clinic, _admin, patient, exercise, headers = await _setup(db_session)
    rx_id = await _create_rx(client, headers, patient, exercise)
    assert (await client.post(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf", headers=headers)).status_code == 200

    # Another clinic's admin cannot see it.
    _c2, _u2, _p2, _e2, other = await _setup(db_session)
    resp = await client.get(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf/download", headers=other)
    assert resp.status_code == 404

    # A therapist in the same clinic with OWN scope cannot download someone else's.
    therapist = User(
        id=uuid.uuid4(), clinic_id=clinic.id, email=f"th-{uuid.uuid4().hex[:8]}@avtest.com",
        password_hash="hash", role=UserRole.THERAPIST, first_name="T", last_name="One", is_active=True,
    )
    db_session.add(therapist)
    await db_session.flush()
    db_session.add(Membership(user_id=therapist.id, clinic_id=clinic.id, role=UserRole.THERAPIST))
    db_session.add(UserPermission(user_id=therapist.id, clinic_id=clinic.id,
                                  capability_key="prescriptions.view", scope=CapabilityScope.OWN))
    await db_session.commit()
    token = create_access_token(subject=therapist.id, clinic_id=clinic.id, role=UserRole.THERAPIST.value)
    resp = await client.get(
        f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------- letterhead (feedback 23 Oct)


def _data_uri(fmt: str, mime: str, size=(300, 120)) -> str:
    import base64

    buf = io.BytesIO()
    Image.new("RGBA" if fmt != "JPEG" else "RGB", size, (200, 30, 30)).save(buf, format=fmt)
    return f"data:image/{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii")


async def test_letterhead_wording_and_no_signature() -> None:
    out = build_prescription_html(_doc())
    assert "Exercise Prescription Tool" in out
    assert "Physical Therapy" not in out
    assert "Prescribed by" not in out
    assert "signature" not in out.lower()
    assert '<div class="caption">Date</div>' not in out
    assert "Treating therapist" in out and "Asha Rao" in out
    # AV logo top-left, clinic on the right.
    assert 'class="av-wordmark"' in out
    assert out.index('class="lh-av"') < out.index('class="lh-clinic"')
    assert "Grove &lt;Physio&gt;" in out
    # No logo stored: clinic name only, no logo cell.
    assert 'class="lh-logo"' not in out
    # Date stays in the top box.
    assert "Prescribed on" in out


async def test_letterhead_av_only_without_clinic_and_no_empty_therapist() -> None:
    out = build_prescription_html(_doc(clinic_name="", physio_name=""))
    assert 'class="lh-clinic"' not in out and 'class="lh-logo"' not in out
    assert ">Clinic<" not in out
    assert "Treating therapist" not in out
    assert 'class="av-wordmark"' in out


async def test_clinic_logo_is_used_when_valid() -> None:
    from app.services.report_letterhead import resolve_clinic_logo

    src = await resolve_clinic_logo(_data_uri("PNG", "png", (1600, 400)))
    assert src.startswith("data:image/png;base64,")
    import base64

    with Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1]))) as img:
        assert max(img.size) <= 400  # shrunk
    out = build_prescription_html(_doc(clinic_logo_src=src))
    assert f'<td class="lh-logo"><div class="tile"><img src="{src}"' in out


@pytest.mark.parametrize(
    ("fmt", "mime"), [("JPEG", "jpeg"), ("WEBP", "webp"), ("GIF", "gif"), ("PNG", "PNG")]
)
async def test_clinic_logo_raster_formats_become_png(fmt: str, mime: str) -> None:
    from app.services.report_letterhead import resolve_clinic_logo

    src = await resolve_clinic_logo(_data_uri(fmt, mime))
    assert src.startswith("data:image/png;base64,"), fmt


async def test_clinic_logo_bad_values_fall_back() -> None:
    import base64

    from app.services import report_letterhead
    from app.services.report_letterhead import resolve_clinic_logo

    svg = "data:image/svg+xml;base64," + base64.b64encode(
        b'<svg xmlns="http://www.w3.org/2000/svg"><image href="http://169.254.169.254/"/></svg>'
    ).decode()
    not_image = "data:image/png;base64," + base64.b64encode(b"hello world").decode()
    bad = [
        None, "", "   ", svg, not_image,
        "data:image/png;base64,@@@@",
        'data:image/png;base64,AAAA" onload="x',
        "http://example.com/logo.png",  # https only
        "https://example.com/logo.png",  # no fetcher given
        "/static/logo.png",
        "javascript:alert(1)",
        "data:image/png;base64," + "A" * (report_letterhead.LOGO_MAX_CHARS + 4),
    ]
    for value in bad:
        assert await resolve_clinic_logo(value) == "", value


async def test_clinic_logo_remote_url_uses_fetcher() -> None:
    from app.services.report_letterhead import resolve_clinic_logo

    seen: list[str] = []

    async def ok(url: str) -> bytes:
        seen.append(url)
        return _png(800, 200)

    async def none(url: str) -> None:
        return None

    async def boom(url: str) -> bytes:
        raise TimeoutError()

    async def junk(url: str) -> bytes:
        return b"<html>not a logo</html>"

    assert (await resolve_clinic_logo("https://cdn.test/l.png", ok)).startswith("data:image/png")
    assert seen == ["https://cdn.test/l.png"]
    assert await resolve_clinic_logo("https://cdn.test/l.png", none) == ""
    assert await resolve_clinic_logo("https://cdn.test/l.png", boom) == ""
    assert await resolve_clinic_logo("https://cdn.test/l.png", junk) == ""
    seen.clear()
    assert await resolve_clinic_logo("http://cdn.test/l.png", ok) == ""
    assert seen == []


async def test_fetch_logo_blocks_private_hosts_and_size(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/big":
            return httpx.Response(200, content=b"\0" * 2000)
        return httpx.Response(200, content=_png(10, 10))

    transport = httpx.MockTransport(handler)
    assert await prescription_pdf.fetch_logo("https://cdn.test/l.png", transport) is not None
    assert await prescription_pdf.fetch_logo("https://internal.test/l.png", transport) is None
    assert not any("internal.test" in c for c in calls)
    monkeypatch.setattr(prescription_pdf, "IMAGE_MAX_BYTES", 1000)
    assert await prescription_pdf.fetch_logo("https://cdn.test/big", transport) is None


async def test_generated_pdf_uses_clinic_logo_from_db(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _FakeStorage()
    monkeypatch.setattr(prescription_service, "_storage_client", lambda: storage)
    seen: list[str] = []
    real_render = prescription_pdf._render

    def spy(html_content: str) -> bytes:
        seen.append(html_content)
        return real_render(html_content)

    monkeypatch.setattr(prescription_pdf, "_render", spy)
    clinic, _user, patient, exercise, headers = await _setup(db_session)
    clinic.branding_logo_url = _data_uri("PNG", "png")
    await db_session.commit()
    rx_id = await _create_rx(client, headers, patient, exercise)

    gen = await client.post(f"{settings.API_V1_PREFIX}/prescriptions/{rx_id}/pdf", headers=headers)
    assert gen.status_code == 200, gen.text
    assert len(seen) == 1
    html_out = seen[0]
    assert '<td class="lh-logo"><div class="tile"><img src="data:image/png;base64,' in html_out
    assert clinic.name in html_out
    assert "Treating therapist" in html_out and "Asha Rao" in html_out
    assert storage.files[f"prescriptions/{clinic.id}/{rx_id}.pdf"][:5] == b"%PDF-"


async def test_exercise_picture_is_large_and_above_the_dose() -> None:
    """Founders, 27 Oct: pictures were too small for patients to follow.
    The picture now spans the card above the dose, and is kept sharp."""
    from app.services import prescription_pdf as pdf

    item = RxItem("Clamshell", "Hip", "", 3, 10, 0, "Daily", "",
                  "https://example.com/a.png", image_src="data:image/jpeg;base64,AAAA")
    out = build_prescription_html(_doc(items=[item]))
    card = out[out.index('<div class="ex-card">'):]
    assert card.index('<div class="ex-img"><img') < card.index('<table class="dose">')
    assert "max-height: 60mm" in out
    assert pdf.IMAGE_MAX_PX >= 1200
