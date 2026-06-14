import math
from typing import Literal

NOSE = 0

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


def calc_shoulder_asymmetry(landmarks: list[Landmark]) -> float:

    left = landmarks[LEFT_SHOULDER]
    right = landmarks[RIGHT_SHOULDER]

    return abs(left.y - right.y) * 100


def calc_ear_level_asymmetry(landmarks: list[Landmark]) -> float:

    left = landmarks[LEFT_EAR]
    right = landmarks[RIGHT_EAR]

    return abs(left.y - right.y) * 100


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


def calc_trunk_lateral_shift(landmarks: list[Landmark]) -> float:

    left_shoulder = landmarks[LEFT_SHOULDER]
    right_shoulder = landmarks[RIGHT_SHOULDER]

    left_hip = landmarks[LEFT_HIP]
    right_hip = landmarks[RIGHT_HIP]

    shoulder_mid = (left_shoulder.x + right_shoulder.x) / 2

    hip_mid = (left_hip.x + right_hip.x) / 2

    return abs(shoulder_mid - hip_mid) * 100


def midpoint(
    a: tuple[float, float],
    b: tuple[float, float],
) -> tuple[float, float]:

    return (
        (a[0] + b[0]) / 2,
        (a[1] + b[1]) / 2,
    )


def calc_knee_alignment(landmarks: list[Landmark]) -> float:

    left_knee = landmarks[LEFT_KNEE]
    right_knee = landmarks[RIGHT_KNEE]

    return abs(left_knee.y - right_knee.y) * 100


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


def calc_anterior_pelvic_tilt(landmarks: list[Landmark]) -> float:

    hip = landmarks[LEFT_HIP]
    knee = landmarks[LEFT_KNEE]

    vertical_ref = (
        hip.x,
        hip.y - 1.0,
    )

    return angle_between_points(
        (knee.x, knee.y),
        (hip.x, hip.y),
        vertical_ref,
    )


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
    (shoulder midpoint) from the plumb line dropped through the ankle
    midpoint. Unit: millimetres. MediaPipe approximation only — NOT a
    Cobb angle, screening purposes only.
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

    return math.degrees(math.atan2(abs(dx), abs(dy)))


def calc_bilateral_toe_asymmetry(landmarks: list[Landmark]) -> float:
    """
    PT-P05 — Bilateral Toe Angle Asymmetry. Absolute difference between
    the left and right foot-axis angles (see calc_foot_axis_angle), in
    degrees.
    """

    left_angle = calc_foot_axis_angle(landmarks, "left")
    right_angle = calc_foot_axis_angle(landmarks, "right")

    return abs(left_angle - right_angle)


def calc_detection_confidence(landmarks: list[Landmark]) -> float:
    """
    Rough per-view detection confidence: the average MediaPipe visibility
    score across all landmarks, rounded to 2 decimals. Used as the
    "Accuracy" badge instead of a hardcoded constant.
    """

    if not landmarks:
        return 0.0

    return sum(lm.visibility for lm in landmarks) / len(landmarks)
