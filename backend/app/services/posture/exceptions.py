# Minimum MediaPipe landmark visibility score required before a landmark
# is trusted in a clinical calculation. Landmarks below this are treated
# as not observed rather than as low-confidence observations, because a
# landmark the model is guessing at still comes back with coordinates
# and would otherwise flow into the report silently.
#
# Defined here, not in detector.py, so that calculator.py can apply the
# same threshold without importing cv2/mediapipe.
VISIBILITY_THRESHOLD = 0.65


class InsufficientVisibilityError(Exception):
    """Raised when required landmarks have insufficient visibility."""

    def __init__(self, failed_landmarks):
        self.failed_landmarks = failed_landmarks

        super().__init__(f"Low visibility landmarks: {failed_landmarks}")
