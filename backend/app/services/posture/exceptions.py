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


class ImplausibleLandmarkError(Exception):
    """
    Raised when landmarks are positioned in a way a standing body cannot
    produce, regardless of what their visibility scores say.

    This exists because the visibility score does not detect a misplaced
    landmark. It expresses the model's confidence that a point is inside
    the frame, not that it is on the right piece of anatomy. On 1 October
    2026 a back view returned every lower-limb landmark collapsed onto the
    floor between the feet with visibility of 0.80 and above, and a side
    view returned an ankle sitting higher in the frame than its own knee,
    visibility 0.84, which produced a reported knee flexion of 156 degrees
    graded as normal.

    The checks that raise this are anatomical impossibilities, not
    clinical thresholds. A standing patient's ankle is below their knee
    and their knee is below their hip. Nothing here needs a reference
    range or a founder decision.
    """

    def __init__(self, reason: str):
        self.reason = reason

        super().__init__(f"Implausible landmark geometry: {reason}")
