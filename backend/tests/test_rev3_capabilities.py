import pytest
from httpx import AsyncClient

from app.core.rbac import CAPABILITY_REGISTRY
from app.enums.permission import CapabilityScope

REV3_CAPABILITIES = {
    "assessments.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "assessments.create": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "assessments.edit": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "documents.view": {CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL},
    "documents.upload": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "billing.invoice.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "billing.invoice.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "billing.payment.record": {CapabilityScope.NONE, CapabilityScope.ALL},
    "packages.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "packages.manage": {CapabilityScope.NONE, CapabilityScope.ALL},
    "leads.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "leads.manage": {CapabilityScope.NONE, CapabilityScope.ALL},
    "booking.requests.manage": {CapabilityScope.NONE, CapabilityScope.ALL},
    "prescriptions.create": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "posture.view": {CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL},
    "posture.create": {CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL},
    "therapists.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "users.manage": {CapabilityScope.NONE, CapabilityScope.ALL},
    "settings.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "recyclebin.restore": {CapabilityScope.NONE, CapabilityScope.ALL},
    "audit.view": {CapabilityScope.NONE, CapabilityScope.ALL},
}


@pytest.mark.parametrize("capability, scopes", REV3_CAPABILITIES.items())
def test_rev3_capability_registry(
    capability: str, scopes: set[CapabilityScope]
) -> None:
    definition = CAPABILITY_REGISTRY.get(capability)

    assert definition is not None
    assert definition.allowed_scopes == scopes


@pytest.mark.asyncio
async def test_posture_analysis_is_authenticated(client: AsyncClient) -> None:
    response = await client.post("/api/v1/posture/posture/analyze")

    assert response.status_code == 401
