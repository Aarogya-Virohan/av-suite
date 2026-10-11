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
    # 11 October 2026: ears 7 and 8 left the front set with PT-A10.
    front_traced = {0, 11, 12, 23, 24, 25, 26, 27, 28}
    back_traced = {0, 11, 12, 23, 24, 27, 28}

    assert set(review_indices("front")) == front_traced
    assert set(review_indices("back")) == back_traced
    # Side: nose plus the facing side only.
    assert set(review_indices("side", "left")) == {0, 7, 11, 23, 25, 27}
    assert set(review_indices("side", "right")) == {0, 8, 12, 24, 26, 28}


def _token_view(view, lateral_side=None, vis=0.4, iris=None):
    lm = [Landmark(index=i, x=0.5, y=i / 40, z=0.0, visibility=vis) for i in range(33)]
    token = make_detection_token(
        {view: {"landmarks": lm, "width_px": 1000, "height_px": 2000,
                "lateral_side": lateral_side, "iris": iris}}
    )
    return read_detection_token(token)[view]


def _all_points(view, lateral_side=None, **extra):
    return {"points": [{"index": i, "x": 0.5, "y": i / 40, **extra} for i in review_indices(view, lateral_side)]}


def test_confirmed_points_pass_the_visibility_guard_and_unreviewed_keep_model_values():
    from app.services.posture.exceptions import VISIBILITY_THRESHOLD
    from app.services.posture.review import apply_review

    tv = _token_view("back", vis=0.4)
    landmarks, _, audit = apply_review("back", tv, _all_points("back"))

    for i in review_indices("back"):
        assert landmarks[i].visibility == VISIBILITY_THRESHOLD
    assert landmarks[5].visibility == 0.4  # not reviewed, model value kept
    assert all(p["movedPx"] == 0.0 for p in audit["points"])


def test_not_visible_point_is_zeroed():
    from app.services.posture.review import apply_review

    sub = _all_points("back")
    sub["points"][0]["notVisible"] = True
    landmarks, _, _ = apply_review("back", _token_view("back", vis=0.99), sub)
    assert landmarks[sub["points"][0]["index"]].visibility == 0.0


def test_incomplete_review_is_rejected():
    from app.services.posture.review import ReviewRejected, apply_review

    sub = _all_points("front")
    sub["points"].pop()
    with pytest.raises(ReviewRejected):
        apply_review("front", _token_view("front"), sub)


def test_side_review_cannot_flip_the_facing_side():
    from app.services.posture.calculator import get_lateral_side
    from app.services.posture.review import apply_review

    # The model chose "right"; only the right side is reviewed, so raising
    # visibility can only strengthen that choice.
    tv = _token_view("side", lateral_side="right", vis=0.3)
    landmarks, _, _ = apply_review("side", tv, _all_points("side", "right"))
    assert get_lateral_side(landmarks) == "right"


def test_pupils_must_be_reviewed_when_the_model_found_them():
    from app.services.posture.review import ReviewRejected, apply_review

    tv = _token_view("front", iris=((100.0, 200.0), (300.0, 210.0)))
    with pytest.raises(ReviewRejected):
        apply_review("front", tv, _all_points("front"))
