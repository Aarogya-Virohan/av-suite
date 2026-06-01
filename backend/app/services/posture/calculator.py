import math

LEFT_EAR = 7
RIGHT_EAR = 8

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12

LEFT_HIP = 23
RIGHT_HIP = 24

LEFT_KNEE = 25
RIGHT_KNEE = 26


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


def calc_cva(landmarks: list[Landmark]) -> float:

    ear = landmarks[LEFT_EAR]
    shoulder = landmarks[LEFT_SHOULDER]

    horizontal_ref = (
        shoulder.x + 1.0,
        shoulder.y,
    )

    return angle_between_points(
        (ear.x, ear.y),
        (shoulder.x, shoulder.y),
        horizontal_ref,
    )


def calc_shoulder_asymmetry(landmarks: list[Landmark]) -> float:

    left = landmarks[LEFT_SHOULDER]
    right = landmarks[RIGHT_SHOULDER]

    return abs(left.y - right.y) * 100


def calc_ear_level_asymmetry(landmarks: list[Landmark]) -> float:

    left = landmarks[LEFT_EAR]
    right = landmarks[RIGHT_EAR]

    return abs(left.y - right.y) * 100


def calc_pelvic_obliquity(landmarks: list[Landmark]) -> float:

    left = landmarks[LEFT_HIP]
    right = landmarks[RIGHT_HIP]

    return abs(left.y - right.y) * 100


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
