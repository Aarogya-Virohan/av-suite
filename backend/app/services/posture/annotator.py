import cv2

from .decoder import decode_image_bytes
from .exceptions import VISIBILITY_THRESHOLD
from .review import review_indices
from .schemas import Landmark

LEFT_EAR = 7
RIGHT_EAR = 8
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

# Visual language, 11 October 2026: the report photograph now matches the
# landmark review screen (white skeleton with a dark halo, teal points with
# a white ring) instead of MediaPipe's default neon green and red, which
# read as a debug overlay on a document that goes to a patient.
#
# Only the points the clinician reviewed are drawn (review.review_indices),
# joined the same way the review screen joins them. The other landmarks
# (hands, feet, face) are never measured, and drawing them put unreviewed
# model guesses on the page next to confirmed ones.
#
# Drawing only. No measurement reads anything in this file.

# BGR.
LINE_COLOR = (255, 255, 255)
HALO_COLOR = (28, 28, 28)
POINT_FILL = (143, 136, 78)     # #4E888F, logo teal
POINT_RING = (255, 255, 255)

# Reference layer. The grid is background and stays faint. The centre line
# and the shoulder and hip level lines are what a clinician reads the body
# against, so they are clearly visible but thinner and quieter than the
# skeleton, in the darker brand teal.
GRID_COLOR = (225, 225, 225)
AXIS_COLOR = (112, 106, 59)     # #3B6A70
LEVEL_COLOR = (112, 106, 59)

GRID_ALPHA = 0.12
AXIS_ALPHA = 0.75
HALO_ALPHA = 0.45

# 5 cm fills a full-body frame with roughly 1,400 squares and hides the
# patient. 10 cm stays readable at the distance these photographs are
# taken from.
GRID_SPACING_CM = 10.0

# Same pairs as EDGES in frontend LandmarkReview.tsx. Side view uses only
# the side facing the camera, see _side_edges.
_FRONT_EDGES = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, LEFT_KNEE),
    (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_KNEE),
    (RIGHT_KNEE, RIGHT_ANKLE),
]
_BACK_EDGES = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_ANKLE),
]


def _side_edges(lateral_side: str | None) -> list[tuple[int, int]]:
    left = lateral_side == "left"
    ear = LEFT_EAR if left else RIGHT_EAR
    shoulder = LEFT_SHOULDER if left else RIGHT_SHOULDER
    hip = LEFT_HIP if left else RIGHT_HIP
    knee = LEFT_KNEE if left else RIGHT_KNEE
    ankle = LEFT_ANKLE if left else RIGHT_ANKLE
    return [(ear, shoulder), (shoulder, hip), (hip, knee), (knee, ankle)]


def _edges(view: str, lateral_side: str | None) -> list[tuple[int, int]]:
    if view == "side":
        return _side_edges(lateral_side)
    if view == "back":
        return list(_BACK_EDGES)
    return list(_FRONT_EDGES)


def _scale(height_px: int) -> float:
    """Stroke and point sizes follow the image, so a small display copy and
    a full photograph look the same once printed at the same size."""
    return max(height_px / 900.0, 0.6)


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
    s = _scale(height_px)
    ref_thickness = max(1, int(round(1.5 * s)))

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
    cv2.line(
        overlay, (centre_x, 0), (centre_x, height_px), AXIS_COLOR, ref_thickness, cv2.LINE_AA
    )

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
                _dashed_hline(overlay, y_mid, width_px, LEVEL_COLOR, ref_thickness, s)

    cv2.addWeighted(overlay, AXIS_ALPHA, canvas, 1 - AXIS_ALPHA, 0, canvas)


def _dashed_hline(canvas, y: int, width_px: int, color, thickness: int, s: float) -> None:
    """Level lines are dashed so they never read as part of the skeleton."""
    dash = max(6, int(round(14 * s)))
    gap = max(4, int(round(8 * s)))
    x = 0
    while x < width_px:
        cv2.line(canvas, (x, y), (min(x + dash, width_px), y), color, thickness, cv2.LINE_AA)
        x += dash + gap


def _draw_skeleton(
    canvas,
    landmarks: list[Landmark],
    view: str,
    lateral_side: str | None,
) -> None:
    height_px, width_px = canvas.shape[:2]
    s = _scale(height_px)

    def px(i: int) -> tuple[int, int]:
        lm = landmarks[i]
        return int(round(lm.x * width_px)), int(round(lm.y * height_px))

    edges = _edges(view, lateral_side)

    try:
        points = review_indices(view, lateral_side)
    except ValueError:
        points = sorted({i for e in edges for i in e})

    line_w = max(1, int(round(2.2 * s)))
    halo_w = line_w + max(2, int(round(2.4 * s)))

    # Halo first, translucent, so white lines stay legible on a white wall.
    halo = canvas.copy()
    for a, b in edges:
        cv2.line(halo, px(a), px(b), HALO_COLOR, halo_w, cv2.LINE_AA)
    cv2.addWeighted(halo, HALO_ALPHA, canvas, 1 - HALO_ALPHA, 0, canvas)

    for a, b in edges:
        cv2.line(canvas, px(a), px(b), LINE_COLOR, line_w, cv2.LINE_AA)

    r_outer = max(3, int(round(6.5 * s)))
    r_inner = max(2, int(round(4.6 * s)))

    halo = canvas.copy()
    for i in points:
        cv2.circle(halo, px(i), r_outer + max(1, int(round(1.5 * s))), HALO_COLOR, -1, cv2.LINE_AA)
    cv2.addWeighted(halo, HALO_ALPHA, canvas, 1 - HALO_ALPHA, 0, canvas)

    for i in points:
        cv2.circle(canvas, px(i), r_outer, POINT_RING, -1, cv2.LINE_AA)
        cv2.circle(canvas, px(i), r_inner, POINT_FILL, -1, cv2.LINE_AA)


def _landmarks_from_results(results) -> list[Landmark] | None:
    pose_landmarks = getattr(results, "pose_landmarks", None)
    if pose_landmarks is None:
        return None
    return [
        Landmark(index=i, x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
        for i, lm in enumerate(pose_landmarks.landmark)
    ]


def annotate_pose(
    image_bytes: bytes,
    results,
    landmarks: list[Landmark] | None = None,
    pixels_per_cm: float | None = None,
    view: str = "front",
    lateral_side: str | None = None,
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

    points = landmarks if landmarks is not None else _landmarks_from_results(results)

    if points is not None and len(points) >= 33:
        before_skeleton = annotated.copy()
        try:
            _draw_skeleton(annotated, points, view, lateral_side)
        except Exception:
            # Same reasoning as the reference layer: a drawing failure must
            # not remove the photograph.
            annotated = before_skeleton

    # High quality JPEG: the lines are thin and antialiased, and the default
    # quality smeared them into the background.
    success, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])

    if not success:
        raise ValueError("Image encoding failed")

    return buffer.tobytes()
