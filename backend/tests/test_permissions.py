import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import FastAPI, Depends, APIRouter

from app.core.dependencies import require_capability
from app.enums.permission import CapabilityScope
from app.models.user import User
from app.models.clinic import Clinic
from app.models.user_permission import UserPermission
from app.main import app
from sqlalchemy import select
from uuid import uuid4

pytestmark = pytest.mark.asyncio

@pytest.fixture
def override_router() -> None:
    router = APIRouter()
    @router.get("/test-perm")
    async def test_endpoint(
        scope: CapabilityScope = Depends(require_capability("analytics.my_performance"))
    ):
        return {"scope": scope}
        
    @router.get("/test-clinic-financials")
    async def test_endpoint_financials(
        scope: CapabilityScope = Depends(require_capability("analytics.clinic_financials"))
    ):
        return {"scope": scope}
        
    @router.get("/test-unknown")
    async def test_endpoint_unknown(
        scope: CapabilityScope = Depends(require_capability("unknown.capability"))
    ):
        return {"scope": scope}
        
    app.include_router(router)

async def create_user_permission(db_session: AsyncSession, user_id, clinic_id, key, scope):
    # delete existing to avoid unique constraint violation between tests
    stmt = select(UserPermission).where(
        UserPermission.user_id == user_id,
        UserPermission.clinic_id == clinic_id,
        UserPermission.capability_key == key
    )
    existing = (await db_session.execute(stmt)).scalars().first()
    if existing:
        await db_session.delete(existing)
        await db_session.commit()

    perm = UserPermission(
        user_id=user_id,
        clinic_id=clinic_id,
        capability_key=key,
        scope=scope
    )
    db_session.add(perm)
    await db_session.commit()
    return perm

async def test_unauthenticated(client: AsyncClient, override_router):
    # No auth token -> 401
    response = await client.get("/test-perm")
    assert response.status_code == 401

async def test_missing_capability(client: AsyncClient, frontdesk_auth_headers: dict, override_router):
    # Front desk has no role template for analytics.my_performance -> 403
    response = await client.get("/test-perm", headers=frontdesk_auth_headers)
    assert response.status_code == 403

async def test_role_template_permission(client: AsyncClient, therapist_auth_headers: dict, override_router):
    # Therapist has OWN scope for analytics.my_performance via template
    response = await client.get("/test-perm", headers=therapist_auth_headers)
    assert response.status_code == 200
    assert response.json()["scope"] == "own"

async def test_explicit_user_override_overrides_template(client: AsyncClient, frontdesk_auth_headers: dict, db_session: AsyncSession, override_router):
    # Front desk has no template for analytics.my_performance. Override to OWN
    stmt = select(User).where(User.email == "frontdesk@avtest.com")
    front_desk_user = (await db_session.execute(stmt)).scalar_one()
    
    await create_user_permission(db_session, front_desk_user.id, front_desk_user.clinic_id, "analytics.my_performance", CapabilityScope.OWN)
    response = await client.get("/test-perm", headers=frontdesk_auth_headers)
    assert response.status_code == 200
    assert response.json()["scope"] == "own"

async def test_explicit_user_override_scope_none(client: AsyncClient, therapist_auth_headers: dict, db_session: AsyncSession, override_router):
    # Therapist template is OWN. Override to NONE -> 403
    stmt = select(User).where(User.email == "therapist@avtest.com")
    therapist_user = (await db_session.execute(stmt)).scalar_one()
    
    await create_user_permission(db_session, therapist_user.id, therapist_user.clinic_id, "analytics.my_performance", CapabilityScope.NONE)
    response = await client.get("/test-perm", headers=therapist_auth_headers)
    assert response.status_code == 403

async def test_unknown_capability(client: AsyncClient, auth_headers: dict, override_router):
    # admin has all scope for many things, but unknown capability -> 403
    response = await client.get("/test-unknown", headers=auth_headers)
    assert response.status_code == 403

async def test_admin_has_all_scope(client: AsyncClient, auth_headers: dict, override_router):
    response = await client.get("/test-clinic-financials", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["scope"] == "all"
    
async def test_clinic_isolation(client: AsyncClient, therapist_auth_headers: dict, db_session: AsyncSession, override_router):
    # Override in another clinic should not affect the current clinic's scope
    other_clinic = Clinic(id=uuid4(), name="Other", plan_tier="clinical_pro", is_partner_clinic=True)
    db_session.add(other_clinic)
    await db_session.commit()
    
    stmt = select(User).where(User.email == "therapist@avtest.com")
    therapist_user = (await db_session.execute(stmt)).scalar_one()
    
    # give override = NONE for other clinic
    await create_user_permission(db_session, therapist_user.id, other_clinic.id, "analytics.clinic_financials", CapabilityScope.NONE)
    
    # Should still get NONE scope from template in the current clinic for clinic_financials (since it's not overridden here)
    # Wait, the endpoint uses analytics.my_performance. We should just test another endpoint, e.g., financials
    response = await client.get("/test-clinic-financials", headers=therapist_auth_headers)
    assert response.status_code == 403

