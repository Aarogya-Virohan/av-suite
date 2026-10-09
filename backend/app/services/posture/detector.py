import cv2
import mediapipe as mp
from mediapipe import solutions as mp_solutions

from .decoder import decode_image_bytes
from .schemas import Landmark
from .exceptions import (
    ImplausibleLandmarkError,
    InsufficientVisibilityError,
    VISIBILITY_THRESHOLD,
)

mp_pose = mp_solutions.pose  # type: ignore

# initialize a Pose estimator
pose = mp_pose.Pose(static_image_mode=True, model_complexity=1)

# Face Mesh with iris refinement, for PT-A01 only. Pose's own eye and ear
# points are too coarse for a head tilt angle: on one test subject the
# pose "right eye" sat on the lower eyelid and both "ears" on the cheeks,
# turning a near-level head into 8 degrees. The iris centres from this
# model landed on the pupils on all seven test subjects, including the
# low-resolution one. Added 10 October 2026.
face_mesh = mp_solutions.face_mesh.FaceMesh(  # type: ignore
    static_image_mode=True, refine_landmarks=True, max_num_faces=1
)

# Pose indices used to find the head: nose, both eyes, both ears.
_HEAD_POINTS = (0, 2, 5, 7, 8)
# Face Mesh iris centre indices, available only with refine_landmarks.
_IRIS_CENTRES = (468, 473)

def get_image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Returns (width_px, height_px) for an encoded image."""

    image = decode_image_bytes(image_bytes)

    height, width = image.shape[:2]

    return width, height



def detect_pose_full(image_bytes: bytes):
    """
    Like detect_pose, but also returns the raw MediaPipe `results` object
    (needed by annotator.annotate_pose to draw the skeleton overlay).

    Returns
    -------
    tuple[list[Landmark], Any]
        (parsed landmarks, raw mediapipe pose results)
    """

    image = decode_image_bytes(image_bytes)

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    results = pose.process(rgb)

    if not results.pose_landmarks:
        raise ValueError("No person detected")

    landmarks = []

    for idx, landmark in enumerate(results.pose_landmarks.landmark):

        landmarks.append(
            Landmark(
                index=idx,
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=landmark.visibility,
            )
        )

    return landmarks, results


def detect_iris_centres(
    image_bytes: bytes, pose_landmarks: list[Landmark]
) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Pixel positions of the two pupil centres, ordered image-left first.

    Ordered by image position rather than returned as left and right eyes,
    so no caller depends on how either model labels sides. Face Mesh is run
    on a crop around the head found by Pose, since the face is a small part
    of a full-body photograph.

    Raises InsufficientVisibilityError if the head points are not visible
    or Face Mesh finds no face.
    """

    check_visibility(pose_landmarks, list(_HEAD_POINTS))

    image = decode_image_bytes(image_bytes)
    height, width = image.shape[:2]

    xs = [pose_landmarks[i].x * width for i in _HEAD_POINTS]
    ys = [pose_landmarks[i].y * height for i in _HEAD_POINTS]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    half = max(2 * (max(xs) - min(xs)), 32.0)

    x0, y0 = max(0, int(cx - half)), max(0, int(cy - half))
    x1, y1 = min(width, int(cx + half)), min(height, int(cy + half))
    crop = image[y0:y1, x0:x1]

    results = face_mesh.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    if not results.multi_face_landmarks:
        raise InsufficientVisibilityError("Face not found for iris landmarks")

    mesh = results.multi_face_landmarks[0].landmark
    crop_h, crop_w = crop.shape[:2]
    a, b = (
        (x0 + mesh[i].x * crop_w, y0 + mesh[i].y * crop_h) for i in _IRIS_CENTRES
    )

    return (a, b) if a[0] <= b[0] else (b, a)


def detect_pose(image_bytes: bytes) -> list[Landmark]:

    landmarks, _results = detect_pose_full(image_bytes)

    return landmarks


def check_visibility(landmarks: list[Landmark], required_indices: list[int]) -> None:

    failed = [
        idx
        for idx in required_indices
        if landmarks[idx].visibility < VISIBILITY_THRESHOLD
    ]

    if failed:
        raise InsufficientVisibilityError(failed)


def check_limb_order(
    landmarks: list[Landmark],
    hip_idx: int,
    knee_idx: int,
    ankle_idx: int,
) -> None:
    """
    Reject a leg whose joints are not stacked the way a standing leg is.

    In image coordinates y increases downward, so on anyone standing the
    hip sits above the knee and the knee above the ankle. This is gravity,
    not anatomy, and it holds on the front, side and back views alike.

    The visibility score does not catch this. See ImplausibleLandmarkError
    for the two cases that prompted it. Checked on 42 legs across seven
    subjects and three views: 41 passed, and the one that failed is the
    one that produced a 156 degree knee flexion from an ankle the model
    had placed above the knee.
    """

    hip_y = landmarks[hip_idx].y
    knee_y = landmarks[knee_idx].y
    ankle_y = landmarks[ankle_idx].y

    if not hip_y < knee_y < ankle_y:
        raise ImplausibleLandmarkError(
            f"hip/knee/ankle not in standing order: "
            f"y = {hip_y:.4f}, {knee_y:.4f}, {ankle_y:.4f}"
        )
