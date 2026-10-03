import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.python.solutions import drawing_utils, pose
    mp_drawing = drawing_utils
    mp_pose = pose
except Exception:
    mp_drawing = None
    mp_pose = None


def annotate_pose(image_bytes: bytes, results) -> bytes:
    if mp_drawing is None or mp_pose is None:
        raise RuntimeError(
            "MediaPipe Pose drawing utilities are not available in the current environment."
        )

    np_arr = np.frombuffer(image_bytes, np.uint8)

    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Image decoding failed")

    annotated = image.copy()

    # mediapipe's POSE_CONNECTIONS is a frozenset; draw_landmarks expects a list (or None)
    connections = (
        list(mp_pose.POSE_CONNECTIONS) if mp_pose.POSE_CONNECTIONS is not None else None
    )
    mp_drawing.draw_landmarks(annotated, results.pose_landmarks, connections)

    success, buffer = cv2.imencode(".jpg", annotated)

    if not success:
        raise ValueError("Image encoding failed")

    return buffer.tobytes()
