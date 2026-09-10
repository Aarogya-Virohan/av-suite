import cv2
import numpy as np
from mediapipe.python.solutions import drawing_utils, pose

from .decoder import decode_image_bytes
from .exceptions import VISIBILITY_THRESHOLD
from .schemas import Landmark

mp_drawing = drawing_utils
mp_pose = pose

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24

# Reference layer colours, BGR. Kept deliberately low-contrast so the
# neon-green skeleton stays the most prominent thing on the photograph.
# A bright grid competes with the landmarks and makes the image harder
# to read, not easier.
# The grid is background reference and stays faint. The centre line and
# the shoulder/hip level lines are the part a clinician actually reads,
# so they get the brand orange, full opacity and double thickness. At a
# shared colour and weight they disappeared into the grid, which defeated
# the point of drawing them.
GRID_COLOR = (210, 210, 210)
AXIS_COLOR = (43, 121, 232)
LEVEL_COLOR = (43, 121, 232)

GRID_ALPHA = 0.15
AXIS_ALPHA = 0.85

# 5 cm fills a full-body frame with roughly 1,400 squares and hides the
# patient. 10 cm stays readable at the distance these photographs are
# taken from.
GRID_SPACING_CM = 10.0


def _draw_reference_layer(
    canvas,
    landmarks: list[Landmark] | None,
    pixels_per_cm: float | None,
    view: str,
) -> None:
    """
    Draw the clinical reference layer: a height-calibrated grid, a vertical
    centre line, and on the frontal and posterior views horizontal lines at
    shoulder and hip level.

    This is a visual aid only. No measurement is derived from it, and no
    deviation from any line is reported. Kendall's ideal alignment has never
    been empirically validated, so a line on a photograph must not be
    presented as a standard the patient is failing.

    Drawn in place on `canvas`. Anything that cannot be drawn safely is
    skipped rather than raised, because the caller treats an exception as
    "produce no photograph at all".
    """

    height_px, width_px = canvas.shape[:2]

    overlay = canvas.copy()

    # Grid. Calibrated to the patient's height so one square is the same
    # real-world size on every photograph, which is the whole point of it.
    # Skipped when calibration is unavailable, since a grid at an unknown
    # scale tells the clinician nothing.
    if pixels_per_cm and pixels_per_cm > 0:

        spacing_px = pixels_per_cm * GRID_SPACING_CM

        # A spacing that fine would fill the frame with lines and hide the
        # patient. Treat it as a failed calibration rather than drawing it.
        if spacing_px >= 12:

            x = spacing_px
            while x < width_px:
                cv2.line(overlay, (int(x), 0), (int(x), height_px), GRID_COLOR, 1)
                x += spacing_px

            y = spacing_px
            while y < height_px:
                cv2.line(overlay, (0, int(y)), (width_px, int(y)), GRID_COLOR, 1)
                y += spacing_px

            cv2.addWeighted(overlay, GRID_ALPHA, canvas, 1 - GRID_ALPHA, 0, canvas)

    # Vertical centre line, on the frame rather than on the patient. It is a
    # fixed reference the clinician reads the body against; anchoring it to a
    # landmark would move it with the very asymmetry it is meant to reveal.
    overlay = canvas.copy()

    centre_x = width_px // 2
    cv2.line(overlay, (centre_x, 0), (centre_x, height_px), AXIS_COLOR, 2)

    # Shoulder and hip level lines. Frontal and posterior only: from the side
    # the two shoulders sit one behind the other, so a horizontal line through
    # them means nothing.
    if view in ("front", "back") and landmarks is not None:

        pairs = [
            (LEFT_SHOULDER, RIGHT_SHOULDER),
            (LEFT_HIP, RIGHT_HIP),
        ]

        for left_idx, right_idx in pairs:

            left = landmarks[left_idx]
            right = landmarks[right_idx]

            # Only drawn when both landmarks were actually seen. A line drawn
            # through an estimated landmark reads as fact on a photograph and
            # is more convincing than a wrong number would be.
            if (
                left.visibility < VISIBILITY_THRESHOLD
                or right.visibility < VISIBILITY_THRESHOLD
            ):
                continue

            y_mid = int(((left.y + right.y) / 2) * height_px)

            if 0 <= y_mid < height_px:
                cv2.line(overlay, (0, y_mid), (width_px, y_mid), LEVEL_COLOR, 2)

    cv2.addWeighted(overlay, AXIS_ALPHA, canvas, 1 - AXIS_ALPHA, 0, canvas)


def annotate_pose(
    image_bytes: bytes,
    results,
    landmarks: list[Landmark] | None = None,
    pixels_per_cm: float | None = None,
    view: str = "front",
) -> bytes:

    image = decode_image_bytes(image_bytes)

    annotated = image.copy()

    # Reference layer first, so the skeleton draws on top of it and stays
    # the most legible thing in the frame.
    try:
        _draw_reference_layer(annotated, landmarks, pixels_per_cm, view)
    except Exception:
        # An overlay failure must not cost the caller the photograph. The
        # caller catches ValueError and returns an empty image URL, so a
        # broken grid would silently remove the annotated photo from the
        # report entirely.
        annotated = image.copy()

    # mediapipe's POSE_CONNECTIONS is a frozenset; draw_landmarks expects a list (or None)
    connections = (
        list(mp_pose.POSE_CONNECTIONS) if mp_pose.POSE_CONNECTIONS is not None else None
    )

    # Neon green, slightly thicker than the default (2px) for better
    # visibility against varied backgrounds. Landmark dots keep the
    # library default (red).
    connection_drawing_spec = mp_drawing.DrawingSpec(
        color=(20, 255, 57),  # BGR for neon green (#39FF14)
        thickness=3,
    )

    mp_drawing.draw_landmarks(
        annotated,
        results.pose_landmarks,
        connections,
        connection_drawing_spec=connection_drawing_spec,
    )

    success, buffer = cv2.imencode(".jpg", annotated)

    if not success:
        raise ValueError("Image encoding failed")

    return buffer.tobytes()
