"""Phone tilt correction (services/posture/level.py), 27 October 2026."""

import io
import math

import pytest
from PIL import Image, ImageDraw

from app.services.posture.calculator import (
    LEFT_HIP,
    LEFT_SHOULDER,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    calc_pelvic_obliquity,
    to_geometric_space,
)
from app.services.posture.level import (
    MAX_CORRECTION_DEG,
    rotate_display_image,
    rotate_landmarks,
    rotate_pixel_pair,
    validate_correction,
)
from app.services.posture.schemas import Landmark

W, H = 1080, 1440  # portrait 3:4, not square on purpose


def _body(hip_drop_px: float = 0.0) -> list[Landmark]:
    """33 landmarks; hips and shoulders placed, the rest at the centre."""
    pts = {i: (W / 2, H / 2) for i in range(33)}
    pts[LEFT_SHOULDER] = (W / 2 + 180, 500)
    pts[RIGHT_SHOULDER] = (W / 2 - 180, 500)
    pts[LEFT_HIP] = (W / 2 + 120, 850 + hip_drop_px)
    pts[RIGHT_HIP] = (W / 2 - 120, 850)
    return [
        Landmark(index=i, x=x / W, y=y / H, z=0.0, visibility=0.99)
        for i, (x, y) in sorted(pts.items())
    ]


def _xy(lms):
    return [(lm.x * W, lm.y * H) for lm in lms]


@pytest.mark.parametrize("deg", [-10.0, -3.3, 0.7, 4.0, 15.0])
def test_rotation_round_trips(deg):
    body = _body(hip_drop_px=20)
    back = rotate_landmarks(rotate_landmarks(body, W, H, deg), W, H, -deg)
    for a, b in zip(_xy(body), _xy(back)):
        assert a == pytest.approx(b, abs=1e-6)


def test_rotation_keeps_distances():
    body = _body(hip_drop_px=20)
    rot = rotate_landmarks(body, W, H, 7.5)
    a, b = _xy(body), _xy(rot)
    assert math.dist(a[LEFT_HIP], a[RIGHT_SHOULDER]) == pytest.approx(
        math.dist(b[LEFT_HIP], b[RIGHT_SHOULDER]), abs=1e-6
    )


@pytest.mark.parametrize("phone_roll", [-8.0, -2.5, 1.5, 6.0])
def test_correction_recovers_level_pelvis(phone_roll):
    """
    A level pelvis photographed with the phone rolled reads as obliquity
    equal to the roll; corrected by the same roll it reads level again.
    """
    level = _body()
    true_value = calc_pelvic_obliquity(to_geometric_space(level, W, H))
    assert true_value == pytest.approx(0.0, abs=1e-9)

    # Whatever the phone's roll, the photograph is the scene turned by
    # minus the correction, and applying the correction turns it back.
    taken = rotate_landmarks(level, W, H, -phone_roll)
    uncorrected = calc_pelvic_obliquity(to_geometric_space(taken, W, H))
    assert uncorrected == pytest.approx(abs(phone_roll), abs=1e-6)

    corrected = rotate_landmarks(taken, W, H, phone_roll)
    assert calc_pelvic_obliquity(to_geometric_space(corrected, W, H)) == pytest.approx(0.0, abs=1e-6)


def test_correction_keeps_a_real_obliquity():
    tilted = _body(hip_drop_px=30)  # real pelvic obliquity
    true_value = calc_pelvic_obliquity(to_geometric_space(tilted, W, H))
    assert true_value > 5
    taken = rotate_landmarks(tilted, W, H, -4.0)
    corrected = rotate_landmarks(taken, W, H, 4.0)
    assert calc_pelvic_obliquity(to_geometric_space(corrected, W, H)) == pytest.approx(true_value, abs=1e-6)


def test_points_match_the_rotated_display_image():
    """rotate_landmarks and PIL's rotate turn the same way, so the
    annotated picture and the measured points stay together."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    px, py = W / 2 + 300, H / 2  # right of centre
    # Red, so the cream fill in the rotated corners cannot be mistaken for it.
    ImageDraw.Draw(img).ellipse([px - 6, py - 6, px + 6, py + 6], fill=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    out = Image.open(io.BytesIO(rotate_display_image(buf.getvalue(), 10.0))).convert("RGB")
    xs, ys, n = 0.0, 0.0, 0
    data = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b = data[x, y]
            if r > 128 and g < 90 and b < 90:
                xs += x
                ys += y
                n += 1
    assert n > 0
    found = (xs / n, ys / n)

    lm = [Landmark(index=0, x=px / W, y=py / H, z=0.0, visibility=1.0)]
    expect = _xy(rotate_landmarks(lm, W, H, 10.0))[0]
    assert found[0] == pytest.approx(expect[0], abs=2.0)
    assert found[1] == pytest.approx(expect[1], abs=2.0)
    assert expect[1] < py  # counterclockwise on screen: a point right of centre moves up


def test_display_image_keeps_its_size():
    img = Image.new("RGB", (300, 400), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    out = Image.open(io.BytesIO(rotate_display_image(buf.getvalue(), -6.0)))
    assert out.size == (300, 400)


def test_zero_correction_changes_nothing():
    body = _body()
    assert rotate_landmarks(body, W, H, 0.0) == body
    raw = b"not an image"
    assert rotate_display_image(raw, 0.0) is raw


def test_pupils_stay_image_left_first():
    pair = ((400.0, 300.0), (680.0, 310.0))
    out = rotate_pixel_pair(pair, W, H, 12.0)
    assert out[0][0] < out[1][0]
    assert math.dist(*out) == pytest.approx(math.dist(*pair), abs=1e-6)
    assert rotate_pixel_pair(None, W, H, 5.0) is None


def test_validate_correction():
    assert validate_correction(None) is None
    assert validate_correction(3.25) == 3.25
    assert validate_correction(-MAX_CORRECTION_DEG) == -MAX_CORRECTION_DEG
    for bad in (MAX_CORRECTION_DEG + 0.1, -20.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            validate_correction(bad)


def test_pdf_names_the_correction():
    from app.services.posture.pdf_service import _view_section

    view = {
        "photoUrl": "",
        "measurements": [],
        "interpretation": "",
        "captureSource": "camera",
        "levelCorrection": {"degrees": -2.34, "calibrated": True},
    }
    html = _view_section("Front", view, "front")
    assert "Guided camera capture, levelled by 2.3°" in html

    view["levelCorrection"] = None
    html = _view_section("Front", view, "front")
    assert "levelled by" not in html
    assert "Guided camera capture, tilt not measured" in html

    # A report saved before 27 October has no key and prints as it did.
    del view["levelCorrection"]
    html = _view_section("Front", view, "front")
    assert "tilt not measured" not in html and "levelled by" not in html

    # An upload never claims a correction.
    view.update(captureSource="upload", levelCorrection={"degrees": 3.0, "calibrated": True})
    html = _view_section("Front", view, "front")
    assert "levelled by" not in html
