import pytest

from app.services.posture.calculator import (
    angle_between_points,
    calc_cva,
    calc_elbow_carrying_angle,
    calc_knee_hyperextension,
    calc_pelvic_obliquity,
    distance_between_points,
    LEFT_ELBOW,
    LEFT_SHOULDER,
    LEFT_WRIST,
    RIGHT_SHOULDER,
)

from app.services.posture.schemas import Landmark


@pytest.fixture
def landmarks() -> list[Landmark]:

    points = [
        Landmark(
            index=index,
            x=0.0,
            y=0.0,
            z=0.0,
            visibility=1.0,
        )
        for index in range(33)
    ]

    points[7] = Landmark(
        index=7,
        x=0.3,
        y=0.40,
        z=0.0,
        visibility=1.0,
    )

    points[8] = Landmark(
        index=8,
        x=0.7,
        y=0.45,
        z=0.0,
        visibility=1.0,
    )

    points[11] = Landmark(
        index=11,
        x=0.3,
        y=0.60,
        z=0.0,
        visibility=1.0,
    )

    points[12] = Landmark(
        index=12,
        x=0.7,
        y=0.65,
        z=0.0,
        visibility=1.0,
    )

    points[23] = Landmark(
        index=23,
        x=0.4,
        y=0.80,
        z=0.0,
        visibility=1.0,
    )

    points[24] = Landmark(
        index=24,
        x=0.8,
        y=0.75,
        z=0.0,
        visibility=1.0,
    )

    points[25] = Landmark(
        index=25,
        x=0.4,
        y=0.90,
        z=0.0,
        visibility=1.0,
    )

    points[26] = Landmark(
        index=26,
        x=0.8,
        y=0.95,
        z=0.0,
        visibility=1.0,
    )

    return points
    return points


def test_distance_between_points() -> None:

    result = distance_between_points(
        (0, 0),
        (3, 4),
    )

    assert result == pytest.approx(5.0)


def test_angle_between_points() -> None:

    result = angle_between_points(
        (0, 0),
        (1, 0),
        (1, 1),
    )

    assert result == pytest.approx(90.0)


def test_angle_between_points_zero_length() -> None:

    result = angle_between_points(
        (0, 0),
        (0, 0),
        (1, 1),
    )

    assert result == 0.0


def test_calc_cva(
    landmarks: list[Landmark],
) -> None:

    result = calc_cva(
        landmarks,
    )

    # CVA is, by definition, the acute angle between the ear-shoulder
    # line and horizontal — always between 0 and 90 degrees.
    assert 0 <= result <= 90


def test_calc_pelvic_obliquity(
    landmarks: list[Landmark],
) -> None:

    result = calc_pelvic_obliquity(
        landmarks,
    )

    # PT-A04 is now the angle of the L-Hip/R-Hip line from horizontal (degrees),
    # not the old *100 pseudo-mm value.
    assert result == pytest.approx(7.125, rel=1e-3)


def _blank_landmarks() -> list[Landmark]:

    return [
        Landmark(index=index, x=0.0, y=0.0, z=0.0, visibility=1.0)
        for index in range(33)
    ]


def _set(points: list[Landmark], index: int, x: float, y: float) -> None:

    points[index] = Landmark(index=index, x=x, y=y, z=0.0, visibility=1.0)


def test_calc_knee_hyperextension_flexion_is_positive() -> None:

    points = _blank_landmarks()

    # Facing direction: ear.x > shoulder.x -> facing toward +x.
    _set(points, RIGHT_SHOULDER, 0.5, 0.3)
    _set(points, 8, 0.6, 0.3)  # RIGHT_EAR

    # Hip directly above ankle (straight vertical reference line).
    _set(points, 24, 0.5, 0.5)  # RIGHT_HIP
    _set(points, 28, 0.5, 1.0)  # RIGHT_ANKLE

    # Knee anterior (toward facing direction, +x) of the hip-ankle line.
    _set(points, 26, 0.6, 0.75)  # RIGHT_KNEE

    result = calc_knee_hyperextension(points, "right")

    assert result > 0


def test_calc_knee_hyperextension_posterior_is_negative() -> None:

    points = _blank_landmarks()

    # Facing direction: ear.x > shoulder.x -> facing toward +x.
    _set(points, RIGHT_SHOULDER, 0.5, 0.3)
    _set(points, 8, 0.6, 0.3)  # RIGHT_EAR

    # Hip directly above ankle (straight vertical reference line).
    _set(points, 24, 0.5, 0.5)  # RIGHT_HIP
    _set(points, 28, 0.5, 1.0)  # RIGHT_ANKLE

    # Knee posterior (away from facing direction, -x) of the hip-ankle line.
    _set(points, 26, 0.4, 0.75)  # RIGHT_KNEE

    result = calc_knee_hyperextension(points, "right")

    assert result < 0


def test_calc_knee_hyperextension_straight_leg_is_zero() -> None:

    points = _blank_landmarks()

    _set(points, RIGHT_SHOULDER, 0.5, 0.3)
    _set(points, 8, 0.6, 0.3)  # RIGHT_EAR

    _set(points, 24, 0.5, 0.5)  # RIGHT_HIP
    _set(points, 26, 0.5, 0.75)  # RIGHT_KNEE, on the hip-ankle line
    _set(points, 28, 0.5, 1.0)  # RIGHT_ANKLE

    result = calc_knee_hyperextension(points, "right")

    assert result == pytest.approx(0.0)


def test_calc_elbow_carrying_angle_valgus_is_positive() -> None:

    points = _blank_landmarks()

    # Body midline (mean of both shoulders) at x = 0.5.
    _set(points, LEFT_SHOULDER, 0.3, 0.3)
    _set(points, RIGHT_SHOULDER, 0.7, 0.3)

    _set(points, LEFT_ELBOW, 0.3, 0.5)
    # Left side: wrist.x < midline_x (0.5) -> valgus -> positive.
    _set(points, LEFT_WRIST, 0.2, 0.7)

    result = calc_elbow_carrying_angle(points, "left")

    assert result > 0


def test_calc_elbow_carrying_angle_varus_is_negative() -> None:

    points = _blank_landmarks()

    _set(points, LEFT_SHOULDER, 0.3, 0.3)
    _set(points, RIGHT_SHOULDER, 0.7, 0.3)

    _set(points, LEFT_ELBOW, 0.3, 0.5)
    # Left side: wrist.x >= midline_x (0.5) -> varus -> negative.
    _set(points, LEFT_WRIST, 0.6, 0.7)

    result = calc_elbow_carrying_angle(points, "left")

    assert result < 0
