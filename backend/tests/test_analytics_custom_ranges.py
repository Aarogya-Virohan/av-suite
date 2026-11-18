from datetime import date, datetime, timezone

import pytest
from app.core.config import settings
from app.core.timezone import CLINIC_TZ
from app.enums.analytics import AnalyticsPeriod
from app.utils.analytics_periods import AnalyticsPeriods


def test_india_midnight_boundary_and_custom_range():
    periods = AnalyticsPeriods.containing(datetime(2024, 1, 1, 18, 29, tzinfo=timezone.utc))
    assert periods.today.start.date() == date(2024, 1, 1)
    assert AnalyticsPeriods.containing(datetime(2024, 1, 1, 18, 30, tzinfo=timezone.utc)).today.start.date() == date(2024, 1, 2)
    selected = AnalyticsPeriods.explicit(date(2024, 3, 1), date(2024, 3, 2))
    assert selected.start.isoformat() == "2024-03-01T00:00:00+05:30"
    assert selected.end.isoformat() == "2024-03-03T00:00:00+05:30"
    assert CLINIC_TZ.key == "Asia/Kolkata"
    assert AnalyticsPeriod.CUSTOM.value == "custom"


@pytest.mark.asyncio
async def test_custom_range_responses_and_validation(client, auth_headers):
    for endpoint in ("analytics/overview", "analytics/my-performance"):
        response = await client.get(f"{settings.API_V1_PREFIX}/{endpoint}?start_date=2026-10-01&end_date=2026-10-15", headers=auth_headers)
        assert response.status_code == 200, response.text
        metadata = response.json()["meta"]
        assert metadata["period"] == "custom"
        assert metadata["start"].startswith("2026-10-01T00:00:00")
        assert metadata["end"].startswith("2026-10-16T00:00:00")
        assert metadata["start"].endswith("+05:30")
        assert metadata["end"].endswith("+05:30")

        for query in ("start_date=2026-10-01", "end_date=2026-10-15", "start_date=2026-10-15&end_date=2026-10-01", "start_date=2024-01-01&end_date=2026-01-02"):
            invalid = await client.get(f"{settings.API_V1_PREFIX}/{endpoint}?{query}", headers=auth_headers)
            assert invalid.status_code == 422
