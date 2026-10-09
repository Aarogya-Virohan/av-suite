import pytest

from app.services.posture.review import (
    InvalidDetectionToken,
    make_detection_token,
    read_detection_token,
    review_indices,
    rows_to_landmarks,
)
from app.services.posture.schemas import Landmark


def _landmarks():
    return [
        Landmark(index=i, x=0.1 + i / 97, y=0.2 + i / 89, z=-0.03, visibility=0.9 - i / 101)
        for i in range(33)
    ]


def test_token_round_trip_is_exact():

    # Untouched points must reproduce the model's report exactly, so the
    # token may not round or reformat anything.
    lm = _landmarks()
    token = make_detection_token(
        {"front": {"landmarks": lm, "width_px": 1832, "height_px": 4096, "iris": ((10.5, 20.25), (30.0, 21.0))}}
    )
    view = read_detection_token(token)["front"]

    assert rows_to_landmarks(view["landmarks"]) == lm
    assert view["iris"] == [[10.5, 20.25], [30.0, 21.0]]


def test_tampered_token_is_rejected():

    token = make_detection_token({"back": {"landmarks": _landmarks(), "width_px": 1, "height_px": 1}})
    with pytest.raises(InvalidDetectionToken):
        read_detection_token(token[:-4] + "AAAA")


def test_review_covers_every_point_a_measurement_reads():

    # Traced on 10 October 2026: every landmark index _report_from_points
    # reads, across all seven test subjects. If a measurement starts reading
    # a new point, it must be added to review or it escapes the clinician.
    front_traced = {0, 7, 8, 11, 12, 23, 24, 25, 26, 27, 28}
    back_traced = {0, 11, 12, 23, 24, 27, 28}

    assert set(review_indices("front")) == front_traced
    assert set(review_indices("back")) == back_traced
    # Side: nose plus the facing side only.
    assert set(review_indices("side", "left")) == {0, 7, 11, 23, 25, 27}
    assert set(review_indices("side", "right")) == {0, 8, 12, 24, 26, 28}
