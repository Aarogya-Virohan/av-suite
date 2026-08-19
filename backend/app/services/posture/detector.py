import cv2
import mediapipe as mp
from mediapipe import solutions as mp_solutions

from .decoder import decode_image_bytes
from .schemas import Landmark
from .exceptions import InsufficientVisibilityError

mp_pose = mp_solutions.pose  # type: ignore

# initialize a Pose estimator
pose = mp_pose.Pose(static_image_mode=True, model_complexity=1)

VISIBILITY_THRESHOLD = 0.65


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
