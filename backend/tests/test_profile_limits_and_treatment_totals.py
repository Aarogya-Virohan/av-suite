"""L-43: clinic profile lengths give 422, not 500. Treatment list total counts
every matching session, and its dates are India days.

Each test registers its own clinic so the shared seeded clinic is not changed.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.config import settings
from app.models.treatment import TreatmentSession
from app.models.user import User

API = settings.API_V1_PREFIX


async def _clinic(client, name):
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": f"Limits {name}", "email": f"limits-{name}@physiodemo.in",
              "password": "Password123!", "first_name": "Limit", "last_name": "Admin"},
    )
    assert reg.status_code in (200, 201), reg.text
    headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    me = await client.get(f"{API}/auth/me", headers=headers)
    body = me.json().get("data", me.json())
    user_id = body.get("id") or body["user"]["id"]
    clinic_id = body.get("clinic_id") or (body.get("clinic") or {}).get("id")
    return headers, UUID(str(user_id)), UUID(str(clinic_id))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,limit",
    [("city", 120), ("state", 120), ("phone", 50), ("registration_number", 120),
     ("authorised_person", 255), ("address_line", 500)],
)
async def test_clinic_profile_lengths_return_422_not_500(client, field, limit):
    headers, _, _ = await _clinic(client, f"len-{field}")
    at_limit = await client.patch(f"{API}/settings/clinic", json={field: "1" * limit}, headers=headers)
    over = await client.patch(f"{API}/settings/clinic", json={field: "1" * (limit + 1)}, headers=headers)
    assert at_limit.status_code == 200, at_limit.text
    assert at_limit.json()[field] == "1" * limit
    assert over.status_code == 422, over.text
    saved = await client.get(f"{API}/settings/clinic", headers=headers)
    assert saved.json()[field] == "1" * limit  # the rejected value was not saved


@pytest.mark.asyncio
async def test_treatment_total_counts_all_pages_and_uses_india_days(client, db_session):
    headers, user_id, clinic_id = await _clinic(client, "treatments")
    patient = await client.post(
        f"{API}/patients",
        json={"first_name": "Total", "last_name": "Count", "phone": "9898700201"},
        headers=headers,
    )
    assert patient.status_code in (200, 201), patient.text
    patient_id = UUID(patient.json()["data"]["id"])

    # 2026-03-15 in India is [14 Mar 18:30Z, 15 Mar 18:30Z).
    times = {
        "before": datetime(2026, 3, 14, 18, 29, tzinfo=timezone.utc),  # 14 Mar 23:59 IST
        "start": datetime(2026, 3, 14, 18, 30, tzinfo=timezone.utc),  # 15 Mar 00:00 IST
        "noon": datetime(2026, 3, 15, 6, 30, tzinfo=timezone.utc),  # 15 Mar 12:00 IST
        "after": datetime(2026, 3, 15, 18, 30, tzinfo=timezone.utc),  # 16 Mar 00:00 IST
    }
    ids = {k: uuid4() for k in times}
    db_session.add_all([
        TreatmentSession(id=ids[k], clinic_id=clinic_id, patient_id=patient_id, therapist_id=user_id,
                         treatment_date=t, treatment=k)
        for k, t in times.items()
    ])
    await db_session.flush()

    page = await client.get(
        f"{API}/treatments", params={"patient_id": str(patient_id), "limit": 2, "offset": 0}, headers=headers
    )
    assert page.status_code == 200, page.text
    assert len(page.json()["items"]) == 2
    assert page.json()["total"] == 4  # was 2 (the page size)

    day = await client.get(
        f"{API}/treatments",
        params={"patient_id": str(patient_id), "start_date": "2026-03-15", "end_date": "2026-03-15"},
        headers=headers,
    )
    assert day.status_code == 200, day.text
    assert {row["id"] for row in day.json()["items"]} == {str(ids["start"]), str(ids["noon"])}
    assert day.json()["total"] == 2


async def _staff(client, admin_headers, email, role, perms):
    created = await client.post(
        f"{API}/users",
        json={"email": email, "password": "Password123!", "role": role, "first_name": role.title(), "last_name": "Staff"},
        headers=admin_headers,
    )
    assert created.status_code in (200, 201), created.text
    user_id = created.json()["data"]["id"]
    granted = await client.put(
        f"{API}/users/{user_id}/permissions",
        json=[{"capability_key": k, "scope": s} for k, s in perms.items()],
        headers=admin_headers,
    )
    assert granted.status_code == 200, granted.text
    login = await client.post(f"{API}/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200, login.text
    return user_id, {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_assignable_therapists_for_booking(client, db_session):
    """D-029: Book Visit lists therapists without `users.view`."""
    admin_headers, admin_id, _ = await _clinic(client, "assign")
    therapist_id, therapist_headers = await _staff(
        client, admin_headers, "assign-therapist@physiodemo.in", "therapist",
        {"appointments.create": "own", "appointments.view": "own"},
    )
    desk_id, desk_headers = await _staff(
        client, admin_headers, "assign-desk@physiodemo.in", "front_desk",
        {"appointments.create": "all", "appointments.view": "all"},
    )
    inactive_id, _ = await _staff(
        client, admin_headers, "assign-gone@physiodemo.in", "therapist", {"appointments.view": "own"},
    )
    # No API deactivates a user, so it is set in the database.
    gone = await db_session.get(User, UUID(inactive_id))
    gone.is_active = False
    await db_session.flush()
    _, nobody_headers = await _staff(
        client, admin_headers, "assign-none@physiodemo.in", "front_desk", {"appointments.view": "all"},
    )

    desk = await client.get(f"{API}/appointments/therapists", headers=desk_headers)
    assert desk.status_code == 200, desk.text
    ids = {row["id"] for row in desk.json()}
    assert ids >= {str(admin_id), therapist_id}
    assert desk_id not in ids  # front desk is not a therapist
    assert inactive_id not in ids  # inactive therapists are not offered
    assert set(desk.json()[0]) == {"id", "name", "role"}  # no email or phone

    own = await client.get(f"{API}/appointments/therapists", headers=therapist_headers)
    assert own.status_code == 200, own.text
    assert [row["id"] for row in own.json()] == [therapist_id]

    users = await client.get(f"{API}/users", headers=desk_headers)
    assert users.status_code == 403  # the user list itself stays closed
    denied = await client.get(f"{API}/appointments/therapists", headers=nobody_headers)
    assert denied.status_code == 403
