from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.core.platform_security import create_platform_access_token
from app.core.security import get_password_hash
from app.models.clinic import Clinic
from app.models.organization import Organization
from app.models.platform import PlatformAuditLog, PlatformOperator
from app.models.usage_event import UsageEvent

pytestmark = pytest.mark.asyncio
API = "/api/v1/platform"


def operator(role="owner"):
    return PlatformOperator(
        email=f"s3-{uuid.uuid4()}@example.com",
        password_hash=get_password_hash("S3TestPass123!"),
        name="S3 Test Operator",
        role=role,
        is_active=True,
        mfa_enabled=True,
        mfa_secret="encrypted-test-secret",
    )


async def test_s3_routes_require_platform_auth_and_product_contract(client, db_session):
    anonymous = await client.get(f"{API}/products")
    assert anonymous.status_code == 401

    owner = operator()
    db_session.add(owner)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    response = await client.get(f"{API}/products", headers=headers)
    assert response.status_code == 200
    assert all(row["key"] != "clinical-decision-support" for row in response.json()["data"])


async def test_organization_mutations_require_reason_and_audit_success(client, db_session):
    owner = operator()
    db_session.add(owner)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}

    invalid_slug = f"s3-{uuid.uuid4()}"
    audit_count = await db_session.scalar(select(func.count(PlatformAuditLog.id))) or 0
    invalid = await client.post(
        f"{API}/organizations", headers=headers,
        json={"name": "S3 Org", "slug": invalid_slug, "type": "clinic", "reason": "  "},
    )
    assert invalid.status_code == 422
    await db_session.flush()
    assert (await db_session.scalar(select(func.count(PlatformAuditLog.id))) or 0) == audit_count

    slug = f"s3-{uuid.uuid4()}"
    created = await client.post(
        f"{API}/organizations", headers=headers,
        json={"name": "S3 Org", "slug": slug, "type": "clinic", "reason": "support request"},
    )
    assert created.status_code == 200
    org_id = created.json()["data"]["id"]
    await db_session.flush()
    logs = (await db_session.scalars(select(PlatformAuditLog).where(PlatformAuditLog.target_id == org_id))).all()
    assert len(logs) == 1
    assert logs[0].operator_id == owner.id
    assert logs[0].reason == "support request"
    assert logs[0].details["before"] is None
    assert logs[0].details["after"]["slug"] == slug


async def test_usage_event_model_has_no_patient_fields_and_delete_routes_do_not_exist(client, db_session):
    columns = set(UsageEvent.__table__.columns.keys())
    assert not columns.intersection({"patient_id", "patient_name", "phone", "diagnosis"})
    owner = operator()
    db_session.add(owner)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    clinic_delete = await client.delete(f"{API}/clinics/{uuid.uuid4()}", headers=headers)
    org_delete = await client.delete(f"{API}/organizations/{uuid.uuid4()}", headers=headers)
    assert clinic_delete.status_code == 405
    assert org_delete.status_code == 405


async def test_failed_usage_event_insert_isolated_from_following_session_work(db_session):
    from app.services.usage_events import record_usage

    clinic = await db_session.scalar(select(Clinic).limit(1))
    assert clinic is not None
    await record_usage(db_session, clinic, None, "x" * 81, "invalid_key")
    await record_usage(db_session, clinic, None, "platform", "login")
    await db_session.flush()
    valid = await db_session.scalar(
        select(UsageEvent).where(
            UsageEvent.clinic_id == clinic.id,
            UsageEvent.product_key == "platform",
            UsageEvent.event_type == "login",
        )
    )
    assert valid is not None
    assert valid.organization_id == clinic.organization_id


async def test_support_is_forbidden_from_platform_mutations(client, db_session):
    support = operator("support")
    db_session.add(support)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(support)}"}
    org_id = uuid.uuid4()
    clinic_id = uuid.uuid4()
    requests = [
        ("post", f"{API}/organizations", {"name": "Nope", "slug": f"nope-{uuid.uuid4()}", "type": "clinic", "reason": "test"}),
        ("patch", f"{API}/organizations/{org_id}", {"name": "Nope", "reason": "test"}),
        ("post", f"{API}/organizations/{org_id}/suspend", {"reason": "test"}),
        ("post", f"{API}/organizations/{org_id}/activate", {"reason": "test"}),
        ("post", f"{API}/organizations/{org_id}/clinics", {"name": "Nope", "slug": f"nope-{uuid.uuid4()}", "type": "clinic", "reason": "test"}),
        ("post", f"{API}/organizations/{org_id}/merge", {"source_organization_id": str(uuid.uuid4()), "reason": "test"}),
        ("post", f"{API}/clinics/{clinic_id}/suspend", {"reason": "test"}),
        ("post", f"{API}/clinics/{clinic_id}/activate", {"reason": "test"}),
        ("put", f"{API}/clinics/{clinic_id}/products/crm", {"status": "enabled", "valid_from": None, "valid_until": None, "reason": "test"}),
        ("patch", f"{API}/operators/{uuid.uuid4()}", {"is_active": False, "reason": "test"}),
    ]
    for method, path, body in requests:
        response = await getattr(client, method)(path, headers=headers, json=body)
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["meta"]["error"]["code"] == "FORBIDDEN"


async def test_organization_clinic_entitlement_usage_and_merge_flow(client, db_session):
    from datetime import date, datetime, timedelta, timezone
    from app.services.usage_events import record_usage

    owner = operator()
    db_session.add(owner)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}

    target = await client.post(
        f"{API}/organizations",
        headers=headers,
        json={"name": "Target Org", "slug": f"target-{uuid.uuid4()}", "type": "chain", "reason": "onboard"},
    )
    source = await client.post(
        f"{API}/organizations",
        headers=headers,
        json={"name": "Source Org", "slug": f"source-{uuid.uuid4()}", "type": "clinic", "reason": "onboard"},
    )
    assert target.status_code == source.status_code == 200
    target_id = target.json()["data"]["id"]
    source_id = source.json()["data"]["id"]

    created = await client.post(
        f"{API}/organizations/{source_id}/clinics",
        headers=headers,
        json={"name": "Branch", "slug": f"branch-{uuid.uuid4()}", "type": "clinic", "reason": "new branch"},
    )
    assert created.status_code == 200, created.text
    clinic = created.json()["data"]
    clinic_id = clinic["id"]
    assert clinic["organization_id"] == source_id
    assert clinic["status"] == "active" and clinic["staff_count"] == 0

    detail = await client.get(f"{API}/clinics/{clinic_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["products"] == []

    entitlement = await client.put(
        f"{API}/clinics/{clinic_id}/products/crm",
        headers=headers,
        json={"status": "enabled", "valid_from": None, "valid_until": None, "reason": "grant CRM"},
    )
    assert entitlement.status_code == 200, entitlement.text
    assert entitlement.json()["data"]["source"] == "direct"
    assert entitlement.json()["data"]["is_effective"] is True

    future_start = await client.put(
        f"{API}/clinics/{clinic_id}/products/crm", headers=headers,
        json={"status": "enabled", "valid_from": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), "valid_until": None, "reason": "future grant"},
    )
    assert future_start.status_code == 200 and future_start.json()["data"]["is_effective"] is False
    exclusive_end = await client.put(
        f"{API}/clinics/{clinic_id}/products/crm", headers=headers,
        json={"status": "enabled", "valid_from": None, "valid_until": datetime.now(timezone.utc).isoformat(), "reason": "expired grant"},
    )
    assert exclusive_end.status_code == 200 and exclusive_end.json()["data"]["is_effective"] is False
    restored = await client.put(
        f"{API}/clinics/{clinic_id}/products/crm", headers=headers,
        json={"status": "enabled", "valid_from": None, "valid_until": None, "reason": "restore grant"},
    )
    assert restored.status_code == 200 and restored.json()["data"]["is_effective"] is True

    clinic_row = await db_session.get(Clinic, uuid.UUID(clinic_id))
    await record_usage(db_session, clinic_row, None, "crm", "appointment_created")
    await db_session.flush()
    today = date.today().isoformat()
    usage = await client.get(f"{API}/usage?clinic_id={clinic_id}&product_key=crm&date_from={today}&date_to={today}", headers=headers)
    assert usage.status_code == 200, usage.text
    assert usage.json()["meta"] == {"total": 1, "page": 1, "page_size": 20}
    assert usage.json()["data"][0]["count"] == 1

    suspended = await client.post(f"{API}/clinics/{clinic_id}/suspend", headers=headers, json={"reason": "temporary"})
    assert suspended.status_code == 200
    after_suspend = await client.get(f"{API}/usage?clinic_id={clinic_id}&product_key=crm", headers=headers)
    assert after_suspend.json()["data"][0]["count"] == 1
    activated = await client.post(f"{API}/clinics/{clinic_id}/activate", headers=headers, json={"reason": "resume"})
    assert activated.status_code == 200 and activated.json()["data"]["status"] == "active"
    disabled = await client.put(
        f"{API}/clinics/{clinic_id}/products/crm", headers=headers,
        json={"status": "disabled", "valid_from": None, "valid_until": None, "reason": "disable CRM"},
    )
    assert disabled.status_code == 200 and disabled.json()["data"]["is_effective"] is False
    after_disable = await client.get(f"{API}/usage?clinic_id={clinic_id}&product_key=crm", headers=headers)
    assert after_disable.json()["data"][0]["count"] == 1

    merged = await client.post(
        f"{API}/organizations/{target_id}/merge",
        headers=headers,
        json={"source_organization_id": source_id, "reason": "consolidation"},
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["data"]["id"] == target_id
    assert any(row["id"] == clinic_id for row in merged.json()["data"]["clinics"])
    source_detail = await client.get(f"{API}/organizations/{source_id}", headers=headers)
    assert source_detail.status_code == 200
    assert source_detail.json()["data"]["clinics"] == []
    assert await db_session.get(Organization, uuid.UUID(source_id)) is not None
    await db_session.flush()
    audit_rows = (
        await db_session.scalars(
            select(PlatformAuditLog).where(
                PlatformAuditLog.operator_id == owner.id,
                PlatformAuditLog.target_id.in_([target_id, source_id, clinic_id, f"{clinic_id}:crm"]),
            )
        )
    ).all()
    assert len(audit_rows) == 11
    entitlement_audit = next(row for row in audit_rows if row.target_type == "entitlement")
    assert "is_effective" in entitlement_audit.details["after"]
    assert "updated_at" in entitlement_audit.details["after"]


async def test_platform_list_filters_pagination_audit_joins_and_overview(client, db_session):
    owner = operator()
    db_session.add_all([owner, operator("support")])
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    prefix = f"filter-{uuid.uuid4().hex[:8]}"
    for suffix in ("a", "b"):
        response = await client.post(
            f"{API}/organizations",
            headers=headers,
            json={"name": f"{prefix}-{suffix}", "slug": f"{prefix}-{suffix}", "type": "chain", "reason": "test"},
        )
        assert response.status_code == 200, response.text
    await db_session.flush()

    page_one = await client.get(
        f"{API}/organizations?search={prefix}&type=chain&status=active&page=1&page_size=1",
        headers=headers,
    )
    page_two = await client.get(
        f"{API}/organizations?search={prefix}&type=chain&status=active&page=2&page_size=1",
        headers=headers,
    )
    assert page_one.status_code == page_two.status_code == 200
    assert page_one.json()["meta"] == {"total": 2, "page": 1, "page_size": 1}
    assert page_two.json()["meta"] == {"total": 2, "page": 2, "page_size": 1}
    assert page_one.json()["data"][0]["id"] != page_two.json()["data"][0]["id"]
    assert (await client.get(f"{API}/organizations?page=1&page_size=101", headers=headers)).status_code == 422
    assert (await client.get(f"{API}/organizations?page=0", headers=headers)).status_code == 422

    org_id = page_one.json()["data"][0]["id"]
    updated = await client.patch(
        f"{API}/organizations/{org_id}", headers=headers,
        json={"name": f"{prefix}-renamed", "contact_email": None, "reason": "rename"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["name"] == f"{prefix}-renamed"
    suspended = await client.post(f"{API}/organizations/{org_id}/suspend", headers=headers, json={"reason": "pause"})
    assert suspended.status_code == 200 and suspended.json()["data"]["status"] == "suspended"
    suspended_list = await client.get(f"{API}/organizations?status=suspended&search={prefix}", headers=headers)
    assert suspended_list.json()["meta"]["total"] == 1
    activated = await client.post(f"{API}/organizations/{org_id}/activate", headers=headers, json={"reason": "resume"})
    assert activated.status_code == 200 and activated.json()["data"]["status"] == "active"

    audit = await client.get(
        f"{API}/audit-logs?operator_id={owner.id}&action=organization.created&page=1&page_size=1",
        headers=headers,
    )
    assert audit.status_code == 200, audit.text
    audit_data = audit.json()["data"][0]
    assert audit.json()["meta"]["total"] == 2
    assert audit_data["operator_name"] == owner.name
    assert audit_data["target_name"].startswith(prefix)

    operators = await client.get(f"{API}/operators?page=1&page_size=1", headers=headers)
    assert operators.status_code == 200
    assert operators.json()["meta"]["total"] >= 2
    assert operators.json()["meta"]["page"] == 1
    assert operators.json()["meta"]["page_size"] == 1
    assert len(operators.json()["data"]) == 1

    overview = await client.get(f"{API}/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    products = overview.json()["data"]["products"]
    assert products
    assert all(row["effective_clinics"] >= 0 for row in products)
    assert "clinical-decision-support" not in {row["product_key"] for row in products}


async def test_all_s3_mutations_reject_missing_reasons(client, db_session):
    owner = operator()
    db_session.add(owner)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    org_id, clinic_id, other_org_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    requests = [
        ("post", f"{API}/organizations", {"name": "No reason", "slug": f"no-reason-{uuid.uuid4()}", "type": "clinic"}),
        ("patch", f"{API}/organizations/{org_id}", {"name": "No reason"}),
        ("post", f"{API}/organizations/{org_id}/suspend", {}),
        ("post", f"{API}/organizations/{org_id}/activate", {}),
        ("post", f"{API}/organizations/{org_id}/clinics", {"name": "No reason", "slug": f"no-reason-{uuid.uuid4()}", "type": "clinic"}),
        ("post", f"{API}/organizations/{org_id}/merge", {"source_organization_id": str(other_org_id)}),
        ("post", f"{API}/clinics/{clinic_id}/suspend", {}),
        ("post", f"{API}/clinics/{clinic_id}/activate", {}),
        ("put", f"{API}/clinics/{clinic_id}/products/crm", {"status": "enabled", "valid_from": None, "valid_until": None}),
        ("patch", f"{API}/operators/{uuid.uuid4()}", {"is_active": False}),
    ]
    for method, path, body in requests:
        response = await getattr(client, method)(path, headers=headers, json=body)
        assert response.status_code == 422, (method, path, response.text)
        assert response.json()["meta"]["error"]["code"] == "VALIDATION_ERROR"


async def test_duplicate_organization_and_clinic_slug_return_409_without_audit(client, db_session):
    owner = operator()
    db_session.add(owner)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    slug = f"dup-{uuid.uuid4()}"
    first = await client.post(f"{API}/organizations", headers=headers, json={"name": "Dup Org", "slug": slug, "type": "clinic", "reason": "onboard"})
    assert first.status_code == 200
    org_id = first.json()["data"]["id"]
    second = await client.post(f"{API}/organizations", headers=headers, json={"name": "Dup Org 2", "slug": slug, "type": "clinic", "reason": "onboard"})
    assert second.status_code == 409
    assert second.json()["meta"]["error"]["code"] == "CONFLICT"

    clinic_slug = f"dup-clinic-{uuid.uuid4()}"
    body = {"name": "Branch", "slug": clinic_slug, "type": "clinic", "reason": "new branch"}
    assert (await client.post(f"{API}/organizations/{org_id}/clinics", headers=headers, json=body)).status_code == 200
    dup = await client.post(f"{API}/organizations/{org_id}/clinics", headers=headers, json=body)
    assert dup.status_code == 409
    await db_session.flush()
    org_rows = await db_session.scalar(select(func.count(PlatformAuditLog.id)).where(PlatformAuditLog.action == "organization.created", PlatformAuditLog.target_id == org_id))
    clinic_rows = await db_session.scalar(select(func.count(PlatformAuditLog.id)).where(PlatformAuditLog.action == "clinic.created", PlatformAuditLog.organization_id == uuid.UUID(org_id)))
    assert org_rows == 1 and clinic_rows == 1  # failed duplicates write no audit row


async def test_overview_recent_audit_has_target_name(client, db_session):
    owner = operator()
    db_session.add(owner)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_platform_access_token(owner)}"}
    name = f"Named Org {uuid.uuid4()}"
    created = await client.post(f"{API}/organizations", headers=headers, json={"name": name, "slug": f"named-{uuid.uuid4()}", "type": "clinic", "reason": "onboard"})
    assert created.status_code == 200
    org_id = created.json()["data"]["id"]
    overview = await client.get(f"{API}/overview", headers=headers)
    assert overview.status_code == 200
    rows = [r for r in overview.json()["data"]["recent_audit"] if r["target_id"] == org_id]
    assert rows and rows[0]["target_name"] == name
