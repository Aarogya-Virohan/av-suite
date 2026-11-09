from app.screening.rate_limit import SlidingWindowLimiter


def test_window_allows_up_to_limit_then_blocks_then_recovers():
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60)
    assert [limiter.hit("k", now=t) for t in (0, 1, 2)] == [0, 0, 0]
    wait = limiter.hit("k", now=3)
    assert wait == 57  # oldest hit at t=0 leaves the window at t=60
    assert limiter.hit("k", now=60.5) == 0


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
    assert limiter.hit("a", now=0) == 0
    assert limiter.hit("b", now=0) == 0
    assert limiter.hit("a", now=1) > 0


def test_memory_stays_bounded():
    limiter = SlidingWindowLimiter(limit=5, window_seconds=60, max_keys=100)
    for i in range(1000):
        limiter.hit(f"k{i}", now=float(i) / 1000)
    assert len(limiter._hits) <= 100


def test_genuine_patient_volume_fits():
    # All three instruments on one link: 37 answers + 3 submits + consent +
    # a page load per answer, doubled for retries. Still under the limit.
    from app.screening.rate_limit import TOKEN_LIMIT

    assert (37 + 3 + 1 + 37) * 2 < TOKEN_LIMIT
