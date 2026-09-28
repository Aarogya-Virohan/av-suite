import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.user import User
from app.enums.user import UserRole
from app.core.security import get_password_hash

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def patient_auth_headers(client: AsyncClient, db_session: AsyncSession):
    """Create a temporary PATIENT role user and return their auth headers."""
    # Find the clinic ID from the admin user
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.email == "admin@avtest.com"))
    admin_user = result.scalar_one()
    clinic_id = admin_user.clinic_id

    patient_user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email="patient@avtest.com",
        password_hash=get_password_hash("Password123!"),
        role=UserRole.PATIENT,
        first_name="Patient",
        last_name="User",
        phone="9876543214",
        is_active=True
    )
    db_session.add(patient_user)
    await db_session.commit()

    login_res = await client.post(f"{settings.API_V1_PREFIX}/auth/login", json={
        "email": "patient@avtest.com",
        "password": "Password123!"
    })
    token = login_res.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
    } # Removed Content-Type because we need to send multipart/form-data

@pytest.fixture
async def seeded_patient(client: AsyncClient, auth_headers: dict) -> str:
    """Create a patient record so we can upload documents to it."""
    # Ensure Content-Type is set for this JSON request
    headers = auth_headers.copy()
    headers["Content-Type"] = "application/json"
    
    res = await client.post(f"{settings.API_V1_PREFIX}/patients", json={
        "first_name": "Test",
        "last_name": "Bucket",
        "date_of_birth": "1990-01-01",
        "phone": "5555555555",
        "gender": "male"
    }, headers=headers)
    assert res.status_code == 201
    return res.json()["data"]["id"]

async def test_bucket_upload_admin(client: AsyncClient, auth_headers: dict, seeded_patient: str):
    """Admin should be able to upload documents."""
    headers = auth_headers.copy()
    headers.pop("Content-Type", None) # Let httpx set multipart boundary
    
    files = {"file": ("test.pdf", b"dummy pdf content", "application/pdf")}
    data = {"label": "Admin Upload", "category": "medical_report"}
    
    res = await client.post(
        f"{settings.API_V1_PREFIX}/patients/{seeded_patient}/documents",
        data=data,
        files=files,
        headers=headers
    )
    assert res.status_code == 201
    assert res.json()["label"] == "Admin Upload"

async def test_bucket_upload_therapist(client: AsyncClient, therapist_auth_headers: dict, seeded_patient: str):
    """Therapist should be able to upload documents."""
    headers = therapist_auth_headers.copy()
    headers.pop("Content-Type", None)
    
    files = {"file": ("test.pdf", b"dummy pdf content", "application/pdf")}
    data = {"label": "Therapist Upload", "category": "medical_report"}
    
    res = await client.post(
        f"{settings.API_V1_PREFIX}/patients/{seeded_patient}/documents",
        data=data,
        files=files,
        headers=headers
    )
    assert res.status_code == 201

async def test_bucket_upload_frontdesk(client: AsyncClient, frontdesk_auth_headers: dict, seeded_patient: str):
    """Front desk should be able to upload documents (based on RBAC defaults)."""
    headers = frontdesk_auth_headers.copy()
    headers.pop("Content-Type", None)
    
    files = {"file": ("test.pdf", b"dummy pdf content", "application/pdf")}
    data = {"label": "Frontdesk Upload", "category": "medical_report"}
    
    res = await client.post(
        f"{settings.API_V1_PREFIX}/patients/{seeded_patient}/documents",
        data=data,
        files=files,
        headers=headers
    )
    assert res.status_code == 201

async def test_bucket_upload_patient_forbidden(client: AsyncClient, patient_auth_headers: dict, seeded_patient: str):
    """Patient should NOT be able to upload documents to the clinic bucket directly via this endpoint."""
    headers = patient_auth_headers.copy()
    
    files = {"file": ("test.pdf", b"dummy pdf content", "application/pdf")}
    data = {"label": "Patient Upload", "category": "medical_report"}
    
    res = await client.post(
        f"{settings.API_V1_PREFIX}/patients/{seeded_patient}/documents",
        data=data,
        files=files,
        headers=headers
    )
    assert res.status_code == 403

async def test_bucket_setting_toggle_disable(client: AsyncClient, auth_headers: dict, seeded_patient: str):
    """Admin disables the document bucket setting, which blocks all uploads/downloads."""
    headers = auth_headers.copy()
    headers["Content-Type"] = "application/json"
    
    # Disable bucket access
    patch_res = await client.patch(
        f"{settings.API_V1_PREFIX}/settings/clinic",
        json={"is_documents_enabled": False},
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_documents_enabled"] is False

    # Try to upload now
    upload_headers = auth_headers.copy()
    upload_headers.pop("Content-Type", None)
    files = {"file": ("test.pdf", b"blocked content", "application/pdf")}
    data = {"label": "Blocked Upload", "category": "medical_report"}
    
    upload_res = await client.post(
        f"{settings.API_V1_PREFIX}/patients/{seeded_patient}/documents",
        data=data,
        files=files,
        headers=upload_headers
    )
    assert upload_res.status_code == 403
    assert "Documents bucket is disabled" in upload_res.json()["detail"]

    # Re-enable for subsequent tests (though pytest async sessions rollback, good practice)
    patch_res = await client.patch(
        f"{settings.API_V1_PREFIX}/settings/clinic",
        json={"is_documents_enabled": True},
        headers=headers
    )
    assert patch_res.status_code == 200
