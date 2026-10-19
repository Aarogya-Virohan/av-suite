"""Golden-value tests for screening scoring.

Expected values are written out by hand from the published norms, never
derived from the definitions under test. Sources:
- PHQ-9: Kroenke, Spitzer & Williams, J Gen Intern Med 2001.
- GAD-7: Spitzer, Kroenke, Williams & Lowe, Arch Intern Med 2006.
- DASS-21: Lovibond & Lovibond, DASS Manual 2nd ed., 1995 (subscale x 2).
"""

from __future__ import annotations

import pytest

from app.screening.registry import get_instrument, list_instruments
from app.screening.scoring import ScoringError, score

PHQ9 = get_instrument("phq9")
GAD7 = get_instrument("gad7")
DASS21 = get_instrument("dass21")


def answers(prefix: str, values: list[int]) -> dict[str, int]:
    return {f"{prefix}_{n}": v for n, v in enumerate(values, start=1)}


def spread(prefix: str, item_numbers: list[int], total: int) -> dict[str, int]:
    """Responses on the given items that sum to ``total`` (each item 0-3)."""
    assert 0 <= total <= 3 * len(item_numbers)
    out: dict[str, int] = {}
    remaining = total
    for n in item_numbers:
        v = min(3, remaining)
        out[f"{prefix}_{n}"] = v
        remaining -= v
    return out


# ---------------------------------------------------------------------------
# Published band tables, written independently of the definitions.
# ---------------------------------------------------------------------------
PHQ9_BANDS = [(0, 4, "None-minimal"), (5, 9, "Mild"), (10, 14, "Moderate"),
              (15, 19, "Moderately severe"), (20, 27, "Severe")]
GAD7_BANDS = [(0, 4, "None-minimal"), (5, 9, "Mild"), (10, 14, "Moderate"),
              (15, 21, "Severe")]
DASS_BANDS = {
    "depression": [(0, 9, "Normal"), (10, 13, "Mild"), (14, 20, "Moderate"),
                   (21, 27, "Severe"), (28, 42, "Extremely severe")],
    "anxiety": [(0, 7, "Normal"), (8, 9, "Mild"), (10, 14, "Moderate"),
                (15, 19, "Severe"), (20, 42, "Extremely severe")],
    "stress": [(0, 14, "Normal"), (15, 18, "Mild"), (19, 25, "Moderate"),
               (26, 33, "Severe"), (34, 42, "Extremely severe")],
}
DASS_ITEMS = {
    "depression": [3, 5, 10, 13, 16, 17, 21],
    "anxiety": [2, 4, 7, 9, 15, 19, 20],
    "stress": [1, 6, 8, 11, 12, 14, 18],
}


def expected_band(table, value):
    hits = [label for lo, hi, label in table if lo <= value <= hi]
    assert len(hits) == 1
    return hits[0]


# ---------------------------------------------------------------------------
# PHQ-9
# ---------------------------------------------------------------------------
PHQ9_GOLDEN = [
    # responses (items 1-9)            total band               referral risk
    ([0, 0, 0, 0, 0, 0, 0, 0, 0],      0,  "None-minimal",       False,  False),
    ([1, 1, 0, 1, 0, 0, 1, 0, 0],      4,  "None-minimal",       False,  False),
    ([1, 1, 1, 1, 1, 0, 0, 0, 0],      5,  "Mild",               False,  False),
    ([2, 1, 1, 1, 1, 1, 1, 1, 0],      9,  "Mild",               False,  False),
    ([2, 2, 1, 1, 1, 1, 1, 1, 0],      10, "Moderate",           True,   False),
    ([2, 2, 2, 2, 2, 2, 1, 1, 0],      14, "Moderate",           True,   False),
    ([2, 2, 2, 2, 2, 2, 2, 1, 0],      15, "Moderately severe",  True,   False),
    ([3, 3, 3, 2, 2, 2, 2, 2, 0],      19, "Moderately severe",  True,   False),
    ([3, 3, 3, 3, 2, 2, 2, 2, 0],      20, "Severe",             True,   False),
    ([3, 3, 3, 3, 3, 3, 3, 3, 3],      27, "Severe",             True,   True),
    # item 9 > 0 with a low total: risk flag forces referral (S-D-005)
    ([0, 0, 0, 0, 0, 0, 0, 0, 1],      1,  "None-minimal",       True,   True),
    ([1, 1, 1, 0, 0, 0, 0, 0, 2],      5,  "Mild",               True,   True),
]


@pytest.mark.parametrize("values,total,band,referral,risk", PHQ9_GOLDEN)
def test_phq9_golden(values, total, band, referral, risk):
    result = score(PHQ9, answers("phq9", values))
    total_scale = result.scale("total")
    assert total_scale.score == total
    assert total_scale.band_label == band
    assert result.referral_flag is referral
    assert result.risk_item_flag is risk


@pytest.mark.parametrize("total", range(0, 28))
def test_phq9_every_total_maps_to_published_band(total):
    # item 9 kept at 0 so the risk rule does not interfere
    responses = spread("phq9", [1, 2, 3, 4, 5, 6, 7, 8], min(total, 24))
    if total > 24:
        responses["phq9_9"] = total - 24
    else:
        responses["phq9_9"] = 0
    result = score(PHQ9, responses).scale("total")
    assert result.score == total
    assert result.band_label == expected_band(PHQ9_BANDS, total)
    assert result.referral is (total >= 10)


def test_phq9_difficulty_item_is_recorded_but_not_scored():
    base = answers("phq9", [1] * 9)
    with_difficulty = {**base, "phq9_difficulty": 3}
    assert score(PHQ9, base).scale("total").score == 9
    assert score(PHQ9, with_difficulty).scale("total").score == 9


# ---------------------------------------------------------------------------
# GAD-7
# ---------------------------------------------------------------------------
GAD7_GOLDEN = [
    ([0, 0, 0, 0, 0, 0, 0],   0,  "None-minimal",  False),
    ([1, 1, 1, 1, 0, 0, 0],   4,  "None-minimal",  False),
    ([1, 1, 1, 1, 1, 0, 0],   5,  "Mild",          False),
    ([2, 2, 1, 1, 1, 1, 1],   9,  "Mild",          False),
    ([2, 2, 2, 1, 1, 1, 1],   10, "Moderate",      True),
    ([2, 2, 2, 2, 2, 2, 2],   14, "Moderate",      True),
    ([3, 2, 2, 2, 2, 2, 2],   15, "Severe",        True),
    ([3, 3, 3, 3, 3, 3, 3],   21, "Severe",        True),
]


@pytest.mark.parametrize("values,total,band,referral", GAD7_GOLDEN)
def test_gad7_golden(values, total, band, referral):
    result = score(GAD7, answers("gad7", values))
    assert result.scale("total").score == total
    assert result.scale("total").band_label == band
    assert result.referral_flag is referral
    assert result.risk_item_flag is False


@pytest.mark.parametrize("total", range(0, 22))
def test_gad7_every_total_maps_to_published_band(total):
    result = score(GAD7, spread("gad7", list(range(1, 8)), total)).scale("total")
    assert result.score == total
    assert result.band_label == expected_band(GAD7_BANDS, total)
    assert result.referral is (total >= 10)


# ---------------------------------------------------------------------------
# DASS-21
# ---------------------------------------------------------------------------
def dass(depression: int, anxiety: int, stress: int) -> dict[str, int]:
    """Responses whose raw subscale sums are the given values (0-21 each)."""
    return {
        **spread("dass21", DASS_ITEMS["depression"], depression),
        **spread("dass21", DASS_ITEMS["anxiety"], anxiety),
        **spread("dass21", DASS_ITEMS["stress"], stress),
    }


DASS21_GOLDEN = [
    # raw sums (D, A, S)  scored (x2)     bands                                           referral
    ((0, 0, 0),    (0, 0, 0),     ("Normal", "Normal", "Normal"),                        False),
    ((4, 3, 7),    (8, 6, 14),    ("Normal", "Normal", "Normal"),                        False),
    ((5, 4, 8),    (10, 8, 16),   ("Mild", "Mild", "Mild"),                              False),
    ((7, 5, 10),   (14, 10, 20),  ("Moderate", "Moderate", "Moderate"),                  False),
    ((10, 7, 12),  (20, 14, 24),  ("Moderate", "Moderate", "Moderate"),                  False),
    ((11, 2, 2),   (22, 4, 4),    ("Severe", "Normal", "Normal"),                        True),
    ((1, 8, 1),    (2, 16, 2),    ("Normal", "Severe", "Normal"),                        True),
    ((1, 1, 13),   (2, 2, 26),    ("Normal", "Normal", "Severe"),                        True),
    ((14, 10, 17), (28, 20, 34),  ("Extremely severe", "Extremely severe", "Extremely severe"), True),
    ((21, 21, 21), (42, 42, 42),  ("Extremely severe", "Extremely severe", "Extremely severe"), True),
]


@pytest.mark.parametrize("raw,scored,bands,referral", DASS21_GOLDEN)
def test_dass21_golden(raw, scored, bands, referral):
    result = score(DASS21, dass(*raw))
    for idx, scale_id in enumerate(("depression", "anxiety", "stress")):
        scale = result.scale(scale_id)
        assert scale.raw_sum == raw[idx]
        assert scale.score == scored[idx]
        assert scale.band_label == bands[idx]
    assert result.referral_flag is referral
    assert result.risk_item_flag is False


@pytest.mark.parametrize("scale_id", ["depression", "anxiety", "stress"])
@pytest.mark.parametrize("raw", range(0, 22))
def test_dass21_every_subscale_total_maps_to_published_band(scale_id, raw):
    sums = {"depression": 0, "anxiety": 0, "stress": 0, scale_id: raw}
    result = score(DASS21, dass(sums["depression"], sums["anxiety"], sums["stress"]))
    scale = result.scale(scale_id)
    assert scale.score == raw * 2
    band = expected_band(DASS_BANDS[scale_id], raw * 2)
    assert scale.band_label == band
    assert scale.referral is (band in ("Severe", "Extremely severe"))


def test_dass21_subscales_partition_all_21_items():
    seen = [i for items in DASS_ITEMS.values() for i in items]
    assert sorted(seen) == list(range(1, 22))
    for scale in DASS21.scales:
        assert [int(i.split("_")[1]) for i in scale.item_ids] == DASS_ITEMS[scale.id]


# ---------------------------------------------------------------------------
# Validation and definition integrity
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "responses,message",
    [
        (answers("phq9", [0] * 8), "Missing"),
        ({**answers("phq9", [0] * 9), "phq9_99": 0}, "Unknown"),
        (answers("phq9", [0] * 8 + [4]), "not a valid option"),
        (answers("phq9", [0] * 8 + [-1]), "not a valid option"),
        (answers("phq9", [0] * 8 + [True]), "integer"),
        ({**answers("phq9", [0] * 9), "phq9_difficulty": 7}, "not a valid option"),
    ],
)
def test_invalid_responses_are_rejected(responses, message):
    with pytest.raises(ScoringError, match=message):
        score(PHQ9, responses)


@pytest.mark.parametrize("instrument", list_instruments(), ids=lambda i: i.id)
def test_bands_cover_full_range_without_gaps_or_overlap(instrument):
    for scale in instrument.scales:
        bands = sorted(scale.bands, key=lambda b: b.min_score)
        assert bands[0].min_score == 0
        for prev, nxt in zip(bands, bands[1:]):
            assert prev.max_score is not None
            assert nxt.min_score == prev.max_score + 1
        assert [b.level for b in bands] == list(range(len(bands)))
        max_possible = 3 * len(scale.item_ids) * scale.multiplier
        assert scale.max_score == max_possible
        last = bands[-1]
        assert last.max_score is None or last.max_score == max_possible


def test_item_counts_match_published_instruments():
    assert len(PHQ9.scored_items) == 9
    assert len(GAD7.scored_items) == 7
    assert len(DASS21.scored_items) == 21
    for instrument in list_instruments():
        assert [i.number for i in instrument.items] == list(
            range(1, len(instrument.items) + 1)
        )


def test_published_response_options():
    labels = [o.label for o in PHQ9.options]
    assert labels == ["Not at all", "Several days", "More than half the days",
                      "Nearly every day"]
    assert GAD7.options == PHQ9.options
    assert [o.value for o in DASS21.options] == [0, 1, 2, 3]


def test_unknown_instrument_and_version():
    with pytest.raises(KeyError):
        get_instrument("nope")
    with pytest.raises(KeyError):
        get_instrument("phq9", "9.9.9")
    assert get_instrument("phq9", "1.0.0") is PHQ9
