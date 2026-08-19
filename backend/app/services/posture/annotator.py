import cv2
from mediapipe.python.solutions import drawing_utils, pose

from .decoder import decode_image_bytes

mp_drawing = drawing_utils
mp_pose = pose


def annotate_pose(image_bytes: bytes, results) -> bytes:

    image = decode_image_bytes(image_bytes)

    annotated = image.copy()

    # mediapipe's POSE_CONNECTIONS is a frozenset; draw_landmarks expects a list (or None)
    connections = (
        list(mp_pose.POSE_CONNECTIONS) if mp_pose.POSE_CONNECTIONS is not None else None
    )

    # Neon green, slightly thicker than the default (2px) for better
    # visibility against varied backgrounds. Landmark dots keep the
    # library default (red).
    connection_drawing_spec = mp_drawing.DrawingSpec(
        color=(20, 255, 57),  # BGR for neon green (#39FF14)
        thickness=3,
    )

    mp_drawing.draw_landmarks(
        annotated,
        results.pose_landmarks,
        connections,
        connection_drawing_spec=connection_drawing_spec,
    )

    success, buffer = cv2.imencode(".jpg", annotated)

    if not success:
        raise ValueError("Image encoding failed")

    return buffer.tobytes()
