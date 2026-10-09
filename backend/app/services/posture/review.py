"""
Landmark review step, founders' Q6, 10 October 2026.

The model's points are shown to the clinician before anything is measured.
Only the points a measurement actually reads are offered for review: the
list below was taken by tracing every landmark index _report_from_points
reads, across all seven test subjects, not from reading the code by eye.
The rest of the 33 landmarks feed only the skeleton drawing and the
landmark visibility badge, and keep the model's values.

The detection token carries the model's own points, signed with the app's
JWT secret, so the report can state what the model placed and what the
clinician confirmed without trusting the client for the first half.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

from .calculator import (
    NOSE,
    LEFT_EAR,
    RIGHT_EAR,
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_KNEE,
    RIGHT_KNEE,
    LEFT_ANKLE,
    RIGHT_ANKLE,
)
from .schemas import Landmark

TOKEN_PURPOSE = "posture-detection"
TOKEN_LIFETIME = timedelta(hours=2)

POINT_NAMES: dict[int, str] = {
    NOSE: "Nose",
    LEFT_EAR: "Left ear",
    RIGHT_EAR: "Right ear",
    LEFT_SHOULDER: "Left shoulder",
    RIGHT_SHOULDER: "Right shoulder",
    LEFT_HIP: "Left hip",
    RIGHT_HIP: "Right hip",
    LEFT_KNEE: "Left knee",
    RIGHT_KNEE: "Right knee",
    LEFT_ANKLE: "Left ankle",
    RIGHT_ANKLE: "Right ankle",
}

# From behind, the nose is not visible, but the millimetre calibration
# still uses it, so the clinician places it on the head midline.
BACK_NOSE_NAME = "Nose (estimate, head midline)"

_FRONT = [
    NOSE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER,
    LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE,
]
_BACK = [NOSE, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP, LEFT_ANKLE, RIGHT_ANKLE]


def review_indices(view: str, lateral_side: str | None = None) -> list[int]:
    """
    Landmark indices the clinician reviews on one view.

    The side view offers only the side facing the camera, plus the nose.
    The far side is hidden behind the body and anything placed there would
    be a guess; it keeps the model's values and is used only to scale the
    reference grid.
    """

    if view == "front":
        return list(_FRONT)
    if view == "back":
        return list(_BACK)
    if view == "side":
        left = lateral_side == "left"
        return [
            NOSE,
            LEFT_EAR if left else RIGHT_EAR,
            LEFT_SHOULDER if left else RIGHT_SHOULDER,
            LEFT_HIP if left else RIGHT_HIP,
            LEFT_KNEE if left else RIGHT_KNEE,
            LEFT_ANKLE if left else RIGHT_ANKLE,
        ]
    raise ValueError(f"Unknown view: {view}")


def point_name(view: str, index: int) -> str:
    if view == "back" and index == NOSE:
        return BACK_NOSE_NAME
    return POINT_NAMES[index]


def _landmarks_to_rows(landmarks: list[Landmark]) -> list[list[float]]:
    return [[lm.x, lm.y, lm.z, lm.visibility] for lm in landmarks]


def rows_to_landmarks(rows: list[list[float]]) -> list[Landmark]:
    return [
        Landmark(index=i, x=r[0], y=r[1], z=r[2], visibility=r[3])
        for i, r in enumerate(rows)
    ]


def make_detection_token(views: dict[str, dict[str, Any]]) -> str:
    """
    views: {"side"|"front"|"back": {"landmarks": [...33 Landmark],
    "width_px", "height_px", "lateral_side" (side only), "iris" (front
    only, pixel pairs image-left first, or None)}}
    """

    now = datetime.now(timezone.utc)
    payload = {
        "purpose": TOKEN_PURPOSE,
        "iat": now,
        "exp": now + TOKEN_LIFETIME,
        "views": {
            name: {
                "landmarks": _landmarks_to_rows(v["landmarks"]),
                "width_px": v["width_px"],
                "height_px": v["height_px"],
                "lateral_side": v.get("lateral_side"),
                "iris": [list(p) for p in v["iris"]] if v.get("iris") else None,
            }
            for name, v in views.items()
        },
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class InvalidDetectionToken(Exception):
    pass


def read_detection_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as e:
        raise InvalidDetectionToken(str(e)) from e

    if payload.get("purpose") != TOKEN_PURPOSE:
        raise InvalidDetectionToken("Not a posture detection token")

    return payload["views"]
