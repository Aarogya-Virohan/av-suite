import math
from typing import Literal

from .exceptions import InsufficientVisibilityError, VISIBILITY_THRESHOLD

NOSE = 0

LEFT_EAR = 7
RIGHT_EAR = 8

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12

LEFT_ELBOW = 13
RIGHT_ELBOW = 14

LEFT_WRIST = 15
RIGHT_WRIST = 16

LEFT_HIP = 23
RIGHT_HIP = 24

LEFT_KNEE = 25
RIGHT_KNEE = 26

LEFT_ANKLE = 27
RIGHT_ANKLE = 28

LEFT_HEEL = 29
RIGHT_HEEL = 30

LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32


def distance_between_points(a: tuple[float, float], b: tuple[float, float]) -> float:

    return math.dist(a, b)


def angle_between_points(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> float:

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    dot = ba[0] * bc[0] + ba[1] * bc[1]

    mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)
    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    cosine = dot / (mag_ba * mag_bc)

    cosine = max(-1.0, min(1.0, cosine))

    angle = math.degrees(math.acos(cosine))

    return angle


from .schemas import Landmark


def to_geometric_space(
    landmarks: list[Landmark],
    image_width_px: int,
    image_height_px: int,
) -> list[Landmark]:
    """
    Return a copy of the landmarks with x rescaled so one x unit and one y
    unit represent the same physical distance.

    MediaPipe normalises x by image width and y by image height. On any
    non-square image those units differ, so an angle computed from raw
    normalised coordinates is distorted by the frame shape. A 3:4 portrait
    photo inflates angles measured from vertical by about 33%, and the same
    patient shot at 9:16 reads differently again, which breaks visit-to-visit
    comparison.

    Multiplying x by (width / height) puts both axes into height-normalised
    units, the same scale a pixel-space calculation uses.

    Pass the result to the angle functions only. The millimetre functions and
    estimate_pixels_per_cm apply their own per-axis scaling and must keep
    receiving the raw landmarks.
    """

    if not image_width_px or not image_height_px:
        raise ValueError("Image dimensions are required to rescale landmarks")

    aspect = image_width_px / image_height_px

    return [
        Landmark(
            index=lm.index,
            x=lm.x * aspect,
            y=lm.y,
            z=lm.z,
            visibility=lm.visibility,
        )
        for lm in landmarks
    ]


def get_lateral_side(landmarks: list[Landmark]) -> Literal["left", "right"]:
    """
    For a side/lateral photo, only one side of the body faces the camera
    with usable visibility. This picks whichever side (left/right) has
    higher combined visibility across ear, shoulder, and hip landmarks.
    """

    left_score = (
        landmarks[LEFT_EAR].visibility
        + landmarks[LEFT_SHOULDER].visibility
        + landmarks[LEFT_HIP].visibility
    )

    right_score = (
        landmarks[RIGHT_EAR].visibility
        + landmarks[RIGHT_SHOULDER].visibility
        + landmarks[RIGHT_HIP].visibility
    )

    return "left" if left_score >= right_score else "right"


def calc_cva(landmarks: list[Landmark], side: Literal["left", "right"] | None = None) -> float:
    """
    PT-L01 — Craniovertebral Angle (Forward Head Posture).

    Returns the acute angle (0-90°) between the ear-shoulder line and
    horizontal. Using atan2(|dy|, |dx|) instead of a fixed +x horizontal
    reference makes this independent of which way the subject faces in
    the photo (a fixed reference can otherwise produce an obtuse/reflex
    angle like 114° for a person facing the other direction).
    """

    if side is None:
        side = get_lateral_side(landmarks)

    ear = landmarks[LEFT_EAR if side == "left" else RIGHT_EAR]
    shoulder = landmarks[LEFT_SHOULDER if side == "left" else RIGHT_SHOULDER]

    dx = ear.x - shoulder.x
    dy = ear.y - shoulder.y

    return math.degrees(math.atan2(abs(dy), abs(dx)))


def calc_pelvic_obliquity(landmarks: list[Landmark]) -> float:
    """
    PT-A04 — Angle of the hip landmark line from horizontal.
    Unit: degrees. (Previously this incorrectly returned a *100 pseudo-mm value.)
    """

    left = landmarks[LEFT_HIP]
    right = landmarks[RIGHT_HIP]

    dx = right.x - left.x
    dy = right.y - left.y

    return math.degrees(math.atan2(abs(dy), abs(dx)))



# Direction helpers.
#
# MediaPipe's y grows downward and its "left"/"right" landmark names are the
# subject's own left and right, not the viewer's. Every direction below is
# reported from the patient's perspective, which is how a physiotherapist
# records a finding.
#
# The magnitude is unchanged and the severity thresholds still run on it.
# These only say which way the deviation goes.


def _higher_side(left_y: float, right_y: float, tol: float = 1e-6) -> str | None:
    """Which side sits higher in the image (smaller y is higher)."""

    if abs(left_y - right_y) < tol:
        return None

    return "left" if left_y < right_y else "right"


def _shifted_side(a_x: float, b_x: float, tol: float = 1e-6) -> str | None:
    """Which way a is displaced relative to b, from the patient's view."""

    if abs(a_x - b_x) < tol:
        return None

    # A larger normalised x is further to the image right, which is the
    # patient's left when they face the camera.
    return "left" if a_x > b_x else "right"


def midpoint(
    a: tuple[float, float],
    b: tuple[float, float],
) -> tuple[float, float]:

    return (
        (a[0] + b[0]) / 2,
        (a[1] + b[1]) / 2,
    )


def calc_forward_trunk_lean(
    landmarks: list[Landmark], side: Literal["left", "right"] | None = None
) -> float:

    if side is None:
        side = get_lateral_side(landmarks)

    shoulder = landmarks[LEFT_SHOULDER if side == "left" else RIGHT_SHOULDER]
    hip = landmarks[LEFT_HIP if side == "left" else RIGHT_HIP]

    vertical_ref = (
        hip.x,
        hip.y - 1.0,
    )

    return angle_between_points(
        (shoulder.x, shoulder.y),
        (hip.x, hip.y),
        vertical_ref,
    )


def calc_knee_hyperextension(
    landmarks: list[Landmark], side: Literal["left", "right"]
) -> float:
    """
    PT-L06 — Knee Hyperextension (Genu Recurvatum), lateral view.

    Returns the hip-knee-ankle deviation in degrees, signed:
    positive = knee flexed/anterior to the hip-ankle line (normal),
    negative = knee hyperextended (posterior to the hip-ankle line),
    relative to the direction the subject is facing (ear-shoulder line).

    Note: sign convention is a geometric approximation based on the
    knee's horizontal offset from the expected straight hip-ankle line
    and the subject's facing direction. Should be reviewed against real
    photos before clinical use (same caveat as
    calc_knee_frontal_deviation).
    """

    hip = landmarks[LEFT_HIP if side == "left" else RIGHT_HIP]
    knee = landmarks[LEFT_KNEE if side == "left" else RIGHT_KNEE]
    ankle = landmarks[LEFT_ANKLE if side == "left" else RIGHT_ANKLE]
    ear = landmarks[LEFT_EAR if side == "left" else RIGHT_EAR]
    shoulder = landmarks[LEFT_SHOULDER if side == "left" else RIGHT_SHOULDER]

    raw_angle = angle_between_points(
        (hip.x, hip.y),
        (knee.x, knee.y),
        (ankle.x, ankle.y),
    )

    deviation = 180.0 - raw_angle

    if ankle.y != hip.y:
        t = (knee.y - hip.y) / (ankle.y - hip.y)
    else:
        t = 0.5

    expected_x = hip.x + t * (ankle.x - hip.x)
    offset = knee.x - expected_x

    facing_dx = ear.x - shoulder.x

    # Knee anterior (toward the facing direction) = flexion/normal,
    # positive. Knee posterior (away from facing direction) =
    # hyperextension, negative.
    if (offset >= 0) == (facing_dx >= 0):
        return deviation

    return -deviation


# ---------------------------------------------------------------------------
# Phase 2 — Anterior (Front) View Calculators
# ---------------------------------------------------------------------------


def calc_head_lateral_tilt(landmarks: list[Landmark]) -> float:
    """
    PT-A01 — Angle between the vertical axis and the
    nose-to-mid-shoulder line. Unit: degrees.
    """

    nose = landmarks[NOSE]

    mid_shoulder = midpoint(
        (landmarks[LEFT_SHOULDER].x, landmarks[LEFT_SHOULDER].y),
        (landmarks[RIGHT_SHOULDER].x, landmarks[RIGHT_SHOULDER].y),
    )

    vertical_ref = (
        mid_shoulder[0],
        mid_shoulder[1] - 1.0,
    )

    return angle_between_points(
        (nose.x, nose.y),
        mid_shoulder,
        vertical_ref,
    )



def head_lateral_tilt_side(landmarks: list[Landmark]) -> str | None:
    """
    Which way the head is tilted, for PT-A01. The angle itself comes from
    calc_head_lateral_tilt and is unsigned; this only names the direction,
    so no grade changes. Anterior view: the patient faces the camera, so
    image-right is the patient's left.
    """

    mid_shoulder_x = (
        landmarks[LEFT_SHOULDER].x + landmarks[RIGHT_SHOULDER].x
    ) / 2

    return _shifted_side(landmarks[NOSE].x, mid_shoulder_x)


def pelvic_obliquity_side(landmarks: list[Landmark]) -> str | None:
    """Which hip sits higher, for PT-A04. Anterior view."""

    return _higher_side(landmarks[LEFT_HIP].y, landmarks[RIGHT_HIP].y)


def shoulder_asymmetry_side(landmarks: list[Landmark]) -> str | None:
    """Which shoulder sits higher, for PT-A02 and PT-P02."""

    return _higher_side(landmarks[LEFT_SHOULDER].y, landmarks[RIGHT_SHOULDER].y)


def ear_asymmetry_side(landmarks: list[Landmark]) -> str | None:
    """Which ear sits higher, for PT-A10. Anterior view."""

    return _higher_side(landmarks[LEFT_EAR].y, landmarks[RIGHT_EAR].y)


def trunk_shift_side(landmarks: list[Landmark]) -> str | None:
    """
    Which way the shoulder midpoint sits relative to the hip midpoint, for
    PT-A03 (anterior) and PT-P01 (posterior). Left/right here are the
    landmark names, which are the patient's own sides in both views, so the
    result reads the same way from either photograph.
    """

    shoulder_mid = (landmarks[LEFT_SHOULDER].x + landmarks[RIGHT_SHOULDER].x) / 2
    hip_mid = (landmarks[LEFT_HIP].x + landmarks[RIGHT_HIP].x) / 2

    return _shifted_side(shoulder_mid, hip_mid)


def calc_knee_frontal_deviation(
    landmarks: list[Landmark], side: Literal["left", "right"]
) -> tuple[float, Literal["valgus", "varus", "neutral"]]:
    """
    PT-A05 / PT-A06 — Frontal-plane knee deviation (Hip-Knee-Ankle angle).

    Returns
    -------
    tuple[float, "valgus" | "varus" | "neutral"]
        (deviation in degrees from a straight hip-knee-ankle line,
         direction of deviation)

    Note: direction is an approximation based on the knee's horizontal
    offset from the expected straight hip-ankle line. Should be reviewed
    against real photos before clinical use.
    """

    hip = landmarks[LEFT_HIP if side == "left" else RIGHT_HIP]
    knee = landmarks[LEFT_KNEE if side == "left" else RIGHT_KNEE]
    ankle = landmarks[LEFT_ANKLE if side == "left" else RIGHT_ANKLE]

    raw_angle = angle_between_points(
        (hip.x, hip.y),
        (knee.x, knee.y),
        (ankle.x, ankle.y),
    )

    deviation = 180.0 - raw_angle

    if ankle.y != hip.y:
        t = (knee.y - hip.y) / (ankle.y - hip.y)
    else:
        t = 0.5

    expected_x = hip.x + t * (ankle.x - hip.x)
    offset = knee.x - expected_x

    if deviation < 0.5:
        direction: Literal["valgus", "varus", "neutral"] = "neutral"
    elif side == "left":
        direction = "valgus" if offset < 0 else "varus"
    else:
        direction = "valgus" if offset > 0 else "varus"

    return deviation, direction


def calc_elbow_carrying_angle(
    landmarks: list[Landmark], side: Literal["left", "right"]
) -> float:
    """
    PT-A08 — Elbow Carrying Angle, anterior view.

    Returns the shoulder-elbow-wrist deviation from a straight line, in
    degrees, signed: positive = valgus (forearm deviates away from the
    body midline), negative = varus.

    Note: sign convention is a geometric approximation based on the
    wrist's horizontal position relative to the body midline (mean of
    both shoulders). Should be reviewed against real photos before
    clinical use.
    """

    shoulder = landmarks[LEFT_SHOULDER if side == "left" else RIGHT_SHOULDER]
    elbow = landmarks[LEFT_ELBOW if side == "left" else RIGHT_ELBOW]
    wrist = landmarks[LEFT_WRIST if side == "left" else RIGHT_WRIST]

    raw_angle = angle_between_points(
        (shoulder.x, shoulder.y),
        (elbow.x, elbow.y),
        (wrist.x, wrist.y),
    )

    deviation = 180.0 - raw_angle

    midline_x = (landmarks[LEFT_SHOULDER].x + landmarks[RIGHT_SHOULDER].x) / 2

    # MediaPipe's LEFT_* landmarks are the patient's own left, which in an
    # anterior photo sits at image-right (larger x). Verified against a
    # known back-camera photograph. Valgus means the forearm deviates away
    # from the midline, so for the patient's left arm that is a larger x,
    # and for the right arm a smaller x. The previous conditions had both
    # of these reversed, which made every normally-standing patient return
    # a negative angle on both arms.
    if side == "left":
        return deviation if wrist.x > midline_x else -deviation

    return deviation if wrist.x < midline_x else -deviation


def estimate_pixels_per_cm(
    landmarks: list[Landmark],
    image_height_px: int,
    patient_height_cm: float,
) -> float | None:
    """
    Rough calibration: estimate pixels-per-cm using the patient's known
    height and the nose-to-ankle pixel span (approx. 97% of total height).
    Used to convert normalised landmark differences into millimetres.
    """

    if not patient_height_cm or patient_height_cm <= 0:
        return None

    # The calibration itself rests on NOSE and both ANKLEs. MediaPipe
    # still returns coordinates for landmarks it cannot actually see, so
    # without this check a hidden ankle produces a wrong scale factor
    # rather than no scale factor -- and every millimetre parameter in
    # the report (PT-A02, PT-A03, PT-A10, PT-P01, PT-P02) is silently
    # rescaled by it. Fail loudly instead: the caller already converts
    # this into a per-parameter "insufficient_data" result.
    failed = [
        idx
        for idx in (NOSE, LEFT_ANKLE, RIGHT_ANKLE)
        if landmarks[idx].visibility < VISIBILITY_THRESHOLD
    ]

    if failed:
        raise InsufficientVisibilityError(failed)

    nose = landmarks[NOSE]
    ankle_mid_y = (landmarks[LEFT_ANKLE].y + landmarks[RIGHT_ANKLE].y) / 2

    body_span_normalised = abs(ankle_mid_y - nose.y)
    body_span_px = body_span_normalised * image_height_px

    if body_span_px <= 0:
        return None

    estimated_height_px = body_span_px / 0.97

    return estimated_height_px / patient_height_cm


def calc_shoulder_asymmetry_mm(
    landmarks: list[Landmark], image_height_px: int, pixels_per_cm: float
) -> float:
    """PT-A02 — Shoulder level asymmetry in millimetres."""

    diff_px = abs(landmarks[LEFT_SHOULDER].y - landmarks[RIGHT_SHOULDER].y) * image_height_px

    return (diff_px / pixels_per_cm) * 10


def calc_ear_level_asymmetry_mm(
    landmarks: list[Landmark], image_height_px: int, pixels_per_cm: float
) -> float:
    """PT-A10 — Ear level asymmetry in millimetres."""

    diff_px = abs(landmarks[LEFT_EAR].y - landmarks[RIGHT_EAR].y) * image_height_px

    return (diff_px / pixels_per_cm) * 10


def calc_trunk_lateral_shift_mm(
    landmarks: list[Landmark], image_width_px: int, pixels_per_cm: float
) -> float:
    """PT-A03 — Trunk lateral shift (shoulder midpoint vs hip midpoint) in millimetres."""

    shoulder_mid_x = (landmarks[LEFT_SHOULDER].x + landmarks[RIGHT_SHOULDER].x) / 2
    hip_mid_x = (landmarks[LEFT_HIP].x + landmarks[RIGHT_HIP].x) / 2

    diff_px = abs(shoulder_mid_x - hip_mid_x) * image_width_px

    return (diff_px / pixels_per_cm) * 10


# ---------------------------------------------------------------------------
# Phase 3 — Posterior (Back) View Calculators
# ---------------------------------------------------------------------------


def calc_scoliosis_screen_mm(
    landmarks: list[Landmark], image_width_px: int, pixels_per_cm: float
) -> float:
    """
    PT-P01 — Scoliosis screen. Lateral deviation of the trunk midline
    (shoulder midpoint) from the pelvic midline (hip midpoint), used as
    a stable proxy for the plumb line. Unit: millimetres. MediaPipe
    approximation only — NOT a Cobb angle, screening purposes only.
    """

    mid_shoulder_x = (landmarks[LEFT_SHOULDER].x + landmarks[RIGHT_SHOULDER].x) / 2
    mid_hip_x = (landmarks[LEFT_HIP].x + landmarks[RIGHT_HIP].x) / 2

    diff_px = abs(mid_shoulder_x - mid_hip_x) * image_width_px

    return (diff_px / pixels_per_cm) * 10


def calc_scapular_height_asymmetry_mm(
    landmarks: list[Landmark], image_height_px: int, pixels_per_cm: float
) -> float:
    """PT-P02 — Scapular height asymmetry (posterior shoulder line). Unit: millimetres."""

    diff_px = abs(landmarks[LEFT_SHOULDER].y - landmarks[RIGHT_SHOULDER].y) * image_height_px

    return (diff_px / pixels_per_cm) * 10


def calc_heel_valgus(landmarks: list[Landmark], side: Literal["left", "right"]) -> float:
    """
    PT-P03 — Heel Valgus / Subtalar Alignment. Deviation of the heel
    from the knee-ankle (lower leg) axis, in degrees. Magnitude only
    (direction not distinguished in this version).
    """

    knee = landmarks[LEFT_KNEE if side == "left" else RIGHT_KNEE]
    ankle = landmarks[LEFT_ANKLE if side == "left" else RIGHT_ANKLE]
    heel = landmarks[LEFT_HEEL if side == "left" else RIGHT_HEEL]

    raw_angle = angle_between_points(
        (knee.x, knee.y),
        (ankle.x, ankle.y),
        (heel.x, heel.y),
    )

    return 180.0 - raw_angle


def calc_pelvic_rotation(landmarks: list[Landmark]) -> float:
    """
    PT-P04 — Pelvic Rotation (Axial). Angular difference between the
    shoulder-line orientation and hip-line orientation, in degrees.
    A larger difference indicates the pelvis is rotated relative to
    the shoulder girdle.
    """

    shoulder_dx = landmarks[RIGHT_SHOULDER].x - landmarks[LEFT_SHOULDER].x
    shoulder_dy = landmarks[RIGHT_SHOULDER].y - landmarks[LEFT_SHOULDER].y
    shoulder_angle = math.degrees(math.atan2(shoulder_dy, shoulder_dx))

    hip_dx = landmarks[RIGHT_HIP].x - landmarks[LEFT_HIP].x
    hip_dy = landmarks[RIGHT_HIP].y - landmarks[LEFT_HIP].y
    hip_angle = math.degrees(math.atan2(hip_dy, hip_dx))

    diff = abs(shoulder_angle - hip_angle)

    # A line and its 180-degree-reversed direction represent the same
    # orientation, so fold the difference into [0, 90].
    if diff > 90:
        diff = 180.0 - diff

    return diff


def calc_foot_axis_angle(landmarks: list[Landmark], side: Literal["left", "right"]) -> float:
    """
    Helper for PT-P05 — angle of the heel-to-foot-index line from
    vertical, in degrees. Used to compare left vs right foot
    orientation from a posterior photo.
    """

    heel = landmarks[LEFT_HEEL if side == "left" else RIGHT_HEEL]
    foot_index = landmarks[LEFT_FOOT_INDEX if side == "left" else RIGHT_FOOT_INDEX]

    dx = foot_index.x - heel.x
    dy = foot_index.y - heel.y

    # Signed, and normalised so that positive always means toe-out for both
    # feet. In image coordinates an out-turned left foot and an out-turned
    # right foot have opposite dx, so a plain abs() folded them together and
    # a plain signed value made a normal symmetric stance look like a large
    # asymmetry. Mirroring the left foot puts both on one convention.
    outward = -dx if side == "left" else dx

    return math.degrees(math.atan2(outward, abs(dy)))


def calc_bilateral_toe_asymmetry(landmarks: list[Landmark]) -> float:
    """
    PT-P05 — Bilateral Toe Angle Asymmetry. Absolute difference between
    the left and right foot-axis angles (see calc_foot_axis_angle), in
    degrees.
    """

    left_angle = calc_foot_axis_angle(landmarks, "left")
    right_angle = calc_foot_axis_angle(landmarks, "right")

    # Both angles use the same toe-out-positive convention, so this compares
    # like with like: a patient standing with both feet turned out by the
    # same amount now reads as symmetric, which is what it is.
    return abs(left_angle - right_angle)


def calc_detection_confidence(landmarks: list[Landmark]) -> float:
    """
    Rough per-view detection confidence: the average MediaPipe visibility
    score across all landmarks, rounded to 2 decimals. Used as the
    "Landmark visibility" figure on the report. This is how clearly
    MediaPipe could see the landmarks, not how accurate the resulting
    measurements are: a landmark can be fully visible and still be
    measured with substantial error.
    """

    if not landmarks:
        return 0.0

    return sum(lm.visibility for lm in landmarks) / len(landmarks)
