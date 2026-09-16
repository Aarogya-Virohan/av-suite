import pytest
from httpx import AsyncClient

from app.core.rbac import CAPABILITY_REGISTRY
from app.enums.permission import CapabilityScope

REV3_CAPABILITIES = {
    "patients.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "patients.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "patients.edit": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "patients.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "leads.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "leads.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "leads.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "leads.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "leads.convert": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "appointments.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "appointments.create": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "appointments.edit": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "appointments.delete": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "treatments.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "treatments.create": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "treatments.edit": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "treatments.delete": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "assessments.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "assessments.create": {
        CapabilityScope.NONE,
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
    "assessments.delete": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "prescriptions.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "prescriptions.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "prescriptions.edit": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "prescriptions.delete": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "exercises.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "exercises.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "exercises.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "exercises.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "packages.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "packages.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "packages.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "packages.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "packages.assign": {CapabilityScope.NONE, CapabilityScope.ALL},
    "invoices.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "invoices.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "invoices.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "invoices.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "payments.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "payments.record": {CapabilityScope.NONE, CapabilityScope.ALL},
    "payments.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "documents.view": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "documents.upload": {CapabilityScope.NONE, CapabilityScope.ALL},
    "documents.edit": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "documents.delete": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "booking.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "booking.approve": {CapabilityScope.NONE, CapabilityScope.ALL},
    "booking.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "booking.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "analytics.my_performance": {
        CapabilityScope.NONE,
        CapabilityScope.OWN,
        CapabilityScope.ALL,
    },
    "analytics.clinic_financials": {CapabilityScope.NONE, CapabilityScope.ALL},
    "settings.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "settings.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "users.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "users.create": {CapabilityScope.NONE, CapabilityScope.ALL},
    "users.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "users.delete": {CapabilityScope.NONE, CapabilityScope.ALL},
    "permissions.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "permissions.edit": {CapabilityScope.NONE, CapabilityScope.ALL},
    "audit.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "recyclebin.view": {CapabilityScope.NONE, CapabilityScope.ALL},
    "recyclebin.restore": {CapabilityScope.NONE, CapabilityScope.ALL},
    "posture.view": {CapabilityScope.NONE, CapabilityScope.OWN, CapabilityScope.ALL},
    "posture.create": {CapabilityScope.NONE, CapabilityScope.ALL},
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
