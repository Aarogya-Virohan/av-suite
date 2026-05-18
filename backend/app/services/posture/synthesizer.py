def generate_synthesis(cva_severity: str):

    hypertonic = []
    inhibited = []
    corrective = []

    if cva_severity in ["moderate", "severe"]:

        hypertonic.extend(
            ["Upper Trapezius", "Levator Scapulae", "Sternocleidomastoid"]
        )

        inhibited.extend(["Deep Neck Flexors", "Lower Trapezius"])

        corrective.extend(
            [
                {"exercise": "Chin Tucks", "dosage": "3x12"},
                {"exercise": "Wall Slides", "dosage": "3x10"},
            ]
        )

    return {
        "hypertonic": hypertonic,
        "inhibited": inhibited,
        "correctiveProtocol": corrective,
    }
