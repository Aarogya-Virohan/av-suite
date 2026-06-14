import pytest

from app.services.posture.calculator import (
    angle_between_points,
    calc_cva,
    calc_pelvic_obliquity,
    distance_between_points,
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
