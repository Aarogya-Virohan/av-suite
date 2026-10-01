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
