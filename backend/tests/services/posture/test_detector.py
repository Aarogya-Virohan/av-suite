import pytest

from app.services.posture.detector import check_limb_order
from app.services.posture.exceptions import ImplausibleLandmarkError
from app.services.posture.schemas import Landmark

HIP, KNEE, ANKLE = 23, 25, 27


def _leg(hip_y: float, knee_y: float, ankle_y: float) -> list[Landmark]:
    """A 33-point set with only the three joints under test positioned."""

    points = [
        Landmark(index=i, x=0.5, y=0.0, z=0.0, visibility=1.0)
        for i in range(33)
    ]
    for idx, y in ((HIP, hip_y), (KNEE, knee_y), (ANKLE, ankle_y)):
        points[idx] = Landmark(index=idx, x=0.5, y=y, z=0.0, visibility=1.0)

    return points


def test_standing_leg_passes():
    # y increases downward, so a standing leg reads hip < knee < ankle.
    check_limb_order(_leg(0.55, 0.72, 0.89), HIP, KNEE, ANKLE)


def test_ankle_above_knee_is_rejected():
    # The real case this guard was written for. On one side view the
    # model placed the ankle higher in the frame than its own knee,
    # visibility 0.84, and the resulting hip-knee-ankle angle reported a
    # knee flexion of 156 degrees graded NONE.
    with pytest.raises(ImplausibleLandmarkError):
        check_limb_order(_leg(0.5558, 0.7189, 0.6462), HIP, KNEE, ANKLE)


def test_knee_above_hip_is_rejected():
    with pytest.raises(ImplausibleLandmarkError):
        check_limb_order(_leg(0.72, 0.55, 0.89), HIP, KNEE, ANKLE)


def test_collapsed_landmarks_are_rejected():
    # Equal values are not a standing leg either. A back view once
    # returned every lower-limb landmark on the same spot on the floor,
    # all reporting visibility above the 0.65 threshold.
    with pytest.raises(ImplausibleLandmarkError):
        check_limb_order(_leg(0.7, 0.7, 0.7), HIP, KNEE, ANKLE)


def test_visibility_is_not_consulted():
    # The guard exists precisely because visibility does not detect a
    # misplaced landmark, so a perfect score must not rescue bad
    # geometry, and a poor score must not fail good geometry. Visibility
    # is check_visibility's job.
    bad = _leg(0.5558, 0.7189, 0.6462)
    for idx in (HIP, KNEE, ANKLE):
        bad[idx] = Landmark(index=idx, x=0.5, y=bad[idx].y, z=0.0, visibility=1.0)
    with pytest.raises(ImplausibleLandmarkError):
        check_limb_order(bad, HIP, KNEE, ANKLE)

    good = _leg(0.55, 0.72, 0.89)
    for idx in (HIP, KNEE, ANKLE):
        good[idx] = Landmark(index=idx, x=0.5, y=good[idx].y, z=0.0, visibility=0.1)
    check_limb_order(good, HIP, KNEE, ANKLE)
