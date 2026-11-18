"""GET /appointments: order=desc and open-ended India-day ranges (D-028, L-39).

Each test registers its own clinic. The test database is shared by the whole
session, and adding patients to the seeded clinic pushes other tests' rows
off the first page of patient lists.
"""

from datetime import datetime, timezone

import pytest

from app.core.config import settings

API = settings.API_V1_PREFIX

# India times as UTC. 2024-03-15 in India is [14 Mar 18:30Z, 15 Mar 18:30Z).
SLOTS = {
    "d14_late": datetime(2024, 3, 14, 18, 29, tzinfo=timezone.utc),  # 14 Mar 23:59 IST
    "d15_early": datetime(2024, 3, 14, 18, 30, tzinfo=timezone.utc),  # 15 Mar 00:00 IST
    "d15_noon": datetime(2024, 3, 15, 6, 30, tzinfo=timezone.utc),  # 15 Mar 12:00 IST
    "d16_early": datetime(2024, 3, 15, 18, 30, tzinfo=timezone.utc),  # 16 Mar 00:00 IST
}


async def _setup(client, name):
    """Register a clinic, add one patient and the four SLOTS appointments."""
    reg = await client.post(
        f"{API}/auth/register",
        json={"clinic_name": f"Order Range {name}", "email": f"order-range-{name}@physiodemo.in",
              "password": "Password123!", "first_name": "Order", "last_name": "Admin"},
    )
    assert reg.status_code in (200, 201), reg.text
    headers = {"Authorization": f"Bearer {reg.json()['data']['access_token']}"}
    me = await client.get(f"{API}/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    body = me.json().get("data", me.json())
    user_id = body.get("id") or body["user"]["id"]
    patient = await client.post(
        f"{API}/patients",
        json={"first_name": "Order", "last_name": "Range", "phone": "9898700101"},
        headers=headers,
    )
    assert patient.status_code in (200, 201), patient.text
    patient_id = patient.json()["data"]["id"]
    ids = {}
    for key, at in SLOTS.items():
        res = await client.post(
            f"{API}/appointments",
            json={"patient_id": patient_id, "therapist_id": user_id,
                  "scheduled_at": at.isoformat(), "duration_minutes": 30},
            headers=headers,
        )
        assert res.status_code in (200, 201), res.text
        ids[key] = res.json().get("data", res.json())["id"]
    return headers, ids


async def _list(client, headers, **params):
    return await client.get(f"{API}/appointments", params=params, headers=headers)


@pytest.mark.asyncio
async def test_order_desc_puts_newest_first_and_default_stays_asc(client):
    headers, ids = await _setup(client, "order")
    asc = await _list(client, headers)
    desc = await _list(client, headers, order="desc")
    assert asc.status_code == desc.status_code == 200
    order = ["d14_late", "d15_early", "d15_noon", "d16_early"]
    assert [a["id"] for a in asc.json()["items"]] == [ids[k] for k in order]
    assert [a["id"] for a in desc.json()["items"]] == [ids[k] for k in reversed(order)]
    page2 = await _list(client, headers, order="desc", offset=1, limit=2)
    assert [a["id"] for a in page2.json()["items"]] == [ids["d15_noon"], ids["d15_early"]]
    assert page2.json()["total"] == 4


@pytest.mark.asyncio
async def test_open_ended_ranges_use_india_days(client):
    headers, ids = await _setup(client, "ranges")
    upcoming = await _list(client, headers, start_date="2024-03-15")
    assert upcoming.status_code == 200, upcoming.text
    assert [a["id"] for a in upcoming.json()["items"]] == [
        ids["d15_early"], ids["d15_noon"], ids["d16_early"]
    ]
    assert upcoming.json()["total"] == 3

    past = await _list(client, headers, end_date="2024-03-15", order="desc")
    assert past.status_code == 200, past.text
    assert [a["id"] for a in past.json()["items"]] == [
        ids["d15_noon"], ids["d15_early"], ids["d14_late"]
    ]
    assert past.json()["total"] == 3

    day = await _list(client, headers, date="2024-03-15")
    assert {a["id"] for a in day.json()["items"]} == {ids["d15_early"], ids["d15_noon"]}
    assert day.json()["total"] == 2


@pytest.mark.asyncio
async def test_status_filter_with_total_and_bad_inputs(client):
    headers, ids = await _setup(client, "status")
    cancel = await client.patch(
        f"{API}/appointments/{ids['d15_noon']}", json={"status": "cancelled"}, headers=headers
    )
    assert cancel.status_code == 200, cancel.text
    cancelled = await _list(client, headers, start_date="2024-03-15", status="cancelled")
    assert [a["id"] for a in cancelled.json()["items"]] == [ids["d15_noon"]]
    assert cancelled.json()["total"] == 1

    reversed_range = await _list(client, headers, start_date="2024-03-16", end_date="2024-03-15")
    bad_order = await _list(client, headers, order="newest")
    assert reversed_range.status_code == 422
    assert bad_order.status_code == 422
