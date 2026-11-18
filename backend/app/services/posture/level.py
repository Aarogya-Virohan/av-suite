"""
Phone tilt correction, 27 October 2026.

Until now the capture screen refused to take a photograph until the phone
was within 1.5 degrees of level in both directions. Held by hand that was
close to impossible, and the founders and Onkar both found it unusable.
It was also less strict than it looked: a phone accelerometer carries a
fixed offset of its own, about 1 degree on a typical part and 5 on a bad
one (ST application note on low-g accelerometer calibration; the iPhone 5s
accelerometer episode), so a phone reading 1.5 could be several degrees
off.

The replacement measures the tilt instead of demanding that it be zero.

- Side tilt (roll, rotation about the camera axis) turns the whole picture.
  Every angle measured against the image horizontal or vertical moves by
  exactly that much: head tilt, pelvic obliquity, shoulder level, CVA,
  trunk lean. Angles between two body segments (knee alignment) do not
  move. Distances do not move. So the fix is exact: rotate the reviewed
  points back by the measured roll before anything is measured.
- Forward tilt (pitch) does not need correcting within the 10 degrees the
  capture screen allows. A pinhole simulation on 27 October gave at most
  0.2 degrees on any graded angle at 10 degrees of pitch; horizontal lines
  stay horizontal under pitch, only verticals converge slightly.

The roll comes from the phone, at the moment of capture, with the phone's
own offset removed when it has been calibrated (reversal method, see the
capture screen). The photograph itself is not rotated or re-encoded for
measurement: detection runs on the original pixels, and only the points
are rotated, which is pure geometry and adds no error.

Convention: correction_deg is the angle, in degrees, by which the
photograph must be turned counterclockwise as seen on screen for true
vertical to become the image vertical. Positive means counterclockwise.
PIL's Image.rotate uses the same sense.
"""

from __future__ import annotations

import io
import math

from PIL import Image

from .schemas import Landmark

# The capture screen allows up to 10 degrees of roll. Anything beyond 15
# did not come from that screen and is refused.
MAX_CORRECTION_DEG = 15.0

# Background for the corners a rotated display photograph leaves empty.
# The report paper colour, so the corners read as margin.
_FILL_RGB = (255, 253, 247)


def _rotate_px(x: float, y: float, cx: float, cy: float, deg: float) -> tuple[float, float]:
    """
    Rotate a pixel position about (cx, cy) counterclockwise as seen on
    screen. Image y grows downward, which is why the signs differ from the
    textbook rotation matrix.
    """
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    dx, dy = x - cx, y - cy
    return (cx + dx * c + dy * s, cy - dx * s + dy * c)


def validate_correction(value: float | None) -> float | None:
    """None or a finite angle within MAX_CORRECTION_DEG; ValueError otherwise."""
    if value is None:
        return None
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("Tilt correction is not a number.")
    if abs(v) > MAX_CORRECTION_DEG:
        raise ValueError(
            f"Tilt correction of {v:.1f} degrees is outside the allowed "
            f"{MAX_CORRECTION_DEG:.0f}. Retake the photograph."
        )
    return v


def rotate_landmarks(
    landmarks: list[Landmark], width_px: int, height_px: int, correction_deg: float
) -> list[Landmark]:
    """
    Landmarks as they would sit in the photograph turned by correction_deg
    about its centre. Rotation happens in pixels, where x and y have the
    same scale, then goes back to MediaPipe's normalised coordinates.
    z and visibility are unchanged.
    """
    if not correction_deg:
        return list(landmarks)
    cx, cy = width_px / 2.0, height_px / 2.0
    out = []
    for lm in landmarks:
        x, y = _rotate_px(lm.x * width_px, lm.y * height_px, cx, cy, correction_deg)
        out.append(
            Landmark(index=lm.index, x=x / width_px, y=y / height_px, z=lm.z, visibility=lm.visibility)
        )
    return out


def rotate_pixel_pair(
    pair: tuple[tuple[float, float], tuple[float, float]] | None,
    width_px: int,
    height_px: int,
    correction_deg: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Rotate the pupil centres (pixels), keeping image-left first."""
    if pair is None or not correction_deg:
        return pair
    cx, cy = width_px / 2.0, height_px / 2.0
    pts = sorted((_rotate_px(x, y, cx, cy, correction_deg) for x, y in pair), key=lambda p: p[0])
    return (pts[0], pts[1])


def rotate_display_image(image_bytes: bytes, correction_deg: float) -> bytes:
    """
    The small display copy used only for the annotated picture on the
    report, turned by the same angle so the rotated points land on it.
    Same size, so the display scale does not change. Never measured.
    """
    if not correction_deg:
        return image_bytes
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    rotated = img.rotate(correction_deg, resample=Image.BICUBIC, expand=False, fillcolor=_FILL_RGB)
    buf = io.BytesIO()
    rotated.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
