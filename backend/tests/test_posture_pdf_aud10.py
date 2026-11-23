"""
AUD-10 (23 Nov 2026): POST /api/v1/posture/report/pdf checks the payload
shape. Bad input = 422 with a fixed message; an unexpected failure = 500
with a fixed message; exception text never reaches the client.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import posture as posture_api
from app.enums.user import UserRole
from tests.test_posture_auth import make_user

pytestmark = pytest.mark.asyncio

URL = "/api/v1/posture/report/pdf"


@pytest.mark.parametrize(
    "payload",
    [
        {"patient": "x"},
        {"views": [], "patient": {}},
        {"views": {"side": "x"}},
        {"views": {"front": {"measurements": "x"}}},
        {"views": {"back": {"measurements": [1]}}},
        {"views": {}, "patient": "x"},
        {"views": {}, "signature": {"regions": "x"}},
        {"views": {}, "synthesis": []},
        {"views": {}, "reportId": 5},
    ],
)
async def test_bad_payload_is_422_with_a_fixed_message(client: AsyncClient, db_session: AsyncSession, payload):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    response = await client.post(URL, headers=headers, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": posture_api.PDF_BAD_PAYLOAD}


async def test_unexpected_failure_is_500_without_exception_text(
    client: AsyncClient, db_session: AsyncSession, monkeypatch, caplog
):
    def boom(*_a, **_k):
        raise RuntimeError("secret internal detail /app/path")

    monkeypatch.setattr(posture_api, "generate_posture_pdf", boom)
    headers = await make_user(db_session, role=UserRole.ADMIN)
    response = await client.post(URL, headers=headers, json={"views": {}})
    assert response.status_code == 500
    assert response.json() == {"detail": posture_api.PDF_FAILED}
    assert "secret internal detail" not in response.text
    assert "secret internal detail" in caplog.text


async def test_valid_payload_still_returns_a_pdf(client: AsyncClient, db_session: AsyncSession):
    headers = await make_user(db_session, role=UserRole.ADMIN)
    report = {
        "patient": {"name": "Valid Payload", "age": 30, "gender": "Male"},
        "reportId": "PT-20261123-AAAA0000",
        "analysisVersion": "2026-11-21.1",
        "views": {"side": {"measurements": []}, "front": {}, "back": None},
        "signature": {"regions": []},
        "synthesis": {},
        "extraKey": [1, 2],
    }
    response = await client.post(URL, headers=headers, json=report)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
