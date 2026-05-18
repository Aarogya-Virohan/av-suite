import math


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

    cosine = dot / (mag_ba * mag_bc)

    cosine = max(-1.0, min(1.0, cosine))

    angle = math.degrees(math.acos(cosine))

    return angle


from .schemas import Landmark


def calc_cva(landmarks: list[Landmark]) -> float:

    # MediaPipe:
    # LEFT_EAR = 7
    # LEFT_SHOULDER = 11

    ear = landmarks[7]
    shoulder = landmarks[11]

    dx = ear.x - shoulder.x
    dy = ear.y - shoulder.y

    angle = math.degrees(math.atan2(dy, dx))

    return abs(angle)
