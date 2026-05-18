class InsufficientVisibilityError(Exception):
    """Raised when required landmarks have insufficient visibility."""

    def __init__(self, failed_landmarks):
        self.failed_landmarks = failed_landmarks

        super().__init__(f"Low visibility landmarks: {failed_landmarks}")
