"""Screener limiter: counters live in the database, not in process memory."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.platform_rate_limit import clear_all_limits, consume_limits

WINDOW = timedelta(seconds=60)
T0 = datetime(2026, 11, 24, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
async def _clean(setup_db):
    await clear_all_limits()
    yield
    await clear_all_limits()


async def hit(key, limit=3, at=0):
    return await consume_limits([("t", key, limit, WINDOW)], now=T0 + timedelta(seconds=at))


async def test_window_allows_up_to_limit_then_blocks_then_recovers():
    assert [(await hit("k", at=t)).allowed for t in (0, 1, 2)] == [True, True, True]
    blocked = await hit("k", at=3)
    assert not blocked.allowed
    assert blocked.retry_after == 57  # the window opened at t=0 and ends at t=60
    assert (await hit("k", at=60.5)).allowed


async def test_keys_are_independent():
    assert (await hit("a", limit=1, at=0)).allowed
    assert (await hit("b", limit=1, at=0)).allowed
    assert not (await hit("a", limit=1, at=1)).allowed


async def test_one_blocked_key_blocks_the_request_but_counts_both():
    both = [("t", "x", 1, WINDOW), ("t", "y", 5, WINDOW)]
    assert (await consume_limits(both, now=T0)).allowed
    assert not (await consume_limits(both, now=T0 + timedelta(seconds=1))).allowed


async def test_genuine_patient_volume_fits():
    # All three instruments on one link: 37 answers + 3 submits + consent +
    # a page load per answer, doubled for retries. Still under the limit.
    from app.screening.rate_limit import TOKEN_LIMIT

    assert (37 + 3 + 1 + 37) * 2 < TOKEN_LIMIT
