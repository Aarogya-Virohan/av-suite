import cv2
import numpy as np

from .schemas import Landmark
from .exceptions import InsufficientVisibilityError

try:
    import mediapipe as mp
    from mediapipe import solutions as mp_solutions
    mp_pose = mp_solutions.pose  # type: ignore
    # initialize a Pose estimator
    pose = mp_pose.Pose(static_image_mode=True, model_complexity=1)
except Exception:
    mp_pose = None
    pose = None

VISIBILITY_THRESHOLD = 0.65


def detect_pose(image_bytes: bytes) -> list[Landmark]:
    if pose is None:
        raise RuntimeError(
            "MediaPipe Pose solution is not available in the current environment."
        )

    np_arr = np.frombuffer(image_bytes, np.uint8)

    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Failed to decode image")

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    results = pose.process(rgb)

    if not results.pose_landmarks:
        raise ValueError("No person detected")

    output = []

    for idx, landmark in enumerate(results.pose_landmarks.landmark):

        output.append(
            Landmark(
                index=idx,
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=landmark.visibility,
            )
        )

    return output


def check_visibility(landmarks: list[Landmark], required_indices: list[int]) -> None:

    failed = [
        idx
        for idx in required_indices
        if landmarks[idx].visibility < VISIBILITY_THRESHOLD
    ]

    if failed:
        raise InsufficientVisibilityError(failed)
