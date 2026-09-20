def _is_actionable(severity: str) -> bool:
    return severity in ("moderate", "severe")


def generate_synthesis(findings: dict[str, str]):

    hypertonic: set[str] = set()
    inhibited: set[str] = set()
    corrective: list[dict] = []

    # ------------------------------------------------------------------ #
    # Helper: look up a key with an optional bilateral suffix
    # e.g. "PT-A05_left" → base_id="PT-A05", "PT-L06" → base_id="PT-L06"
    # ------------------------------------------------------------------ #

    def _lookup(base_id: str) -> str:
        """Return the worst severity found for base_id or any side-suffixed variant."""
        order = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}
        best = "none"
        for key, sev in findings.items():
            # key matches exactly OR key == base_id + "_left" / "_right"
            if key == base_id or key.startswith(base_id + "_"):
                if order.get(sev, 0) > order.get(best, 0):
                    best = sev
        return best

    # ------------------------------------------------------------------ #
    # PT-L01  Forward head posture
    # ------------------------------------------------------------------ #

    if _is_actionable(_lookup("PT-L01")):

        hypertonic.update(["Upper Trapezius", "Levator Scapulae", "Sternocleidomastoid"])
        inhibited.update(["Deep Neck Flexors", "Lower Trapezius"])
        corrective.extend(
            [
                {"exercise": "Chin Tucks", "dosage": "3x12"},
                {"exercise": "Wall Slides", "dosage": "3x10"},
            ]
        )

    # ------------------------------------------------------------------ #
    # PT-A02  Shoulder asymmetry
    # ------------------------------------------------------------------ #

    if _is_actionable(_lookup("PT-A02")):

        hypertonic.update(["Upper Trapezius"])
        inhibited.update(["Middle Trapezius"])
        corrective.extend([{"exercise": "Scapular Retraction", "dosage": "3x15"}])

    # ------------------------------------------------------------------ #
    # PT-A05  Pelvic obliquity (bilateral)
    # ------------------------------------------------------------------ #

    if _is_actionable(_lookup("PT-A05")):

        hypertonic.update(["Hip Flexors", "Quadratus Lumborum"])
        inhibited.update(["Gluteus Medius", "Core Stabilizers"])
        corrective.extend(
            [
                {"exercise": "Clamshells", "dosage": "3x15"},
                {"exercise": "Side-Lying Hip Abduction", "dosage": "3x12"},
            ]
        )

    # ------------------------------------------------------------------ #
    # PT-L06  Knee hyperextension (bilateral)
    # ------------------------------------------------------------------ #

    if _is_actionable(_lookup("PT-L06")):

        hypertonic.update(["Gastrocnemius", "Soleus", "Hip Flexors"])
        inhibited.update(["Quadriceps", "Hamstrings"])
        corrective.extend(
            [
                {"exercise": "Terminal Knee Extension Control", "dosage": "3x15"},
                {"exercise": "Mini Squat", "dosage": "3x12"},
            ]
        )

    # ------------------------------------------------------------------ #
    # PT-A08  Elbow carrying angle (bilateral)
    # ------------------------------------------------------------------ #

    if _is_actionable(_lookup("PT-A08")):

        hypertonic.update(["Forearm Flexors", "Biceps Brachii"])
        inhibited.update(["Forearm Extensors", "Triceps Brachii"])
        corrective.extend(
            [
                {"exercise": "Wrist Extensor Stretch", "dosage": "3x30s"},
                {"exercise": "Elbow Alignment Drill", "dosage": "2x10"},
            ]
        )

    return {
        "hypertonic": sorted(list(hypertonic)),
        "inhibited": sorted(list(inhibited)),
        "correctiveProtocol": corrective,
    }
