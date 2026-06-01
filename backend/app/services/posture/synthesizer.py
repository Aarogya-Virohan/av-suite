def generate_synthesis(findings: dict[str, str]):

    hypertonic = set()
    inhibited = set()

    corrective = []

    # Forward head posture

    if findings.get("PT-L01") in [
        "moderate",
        "severe",
    ]:

        hypertonic.update(
            [
                "Upper Trapezius",
                "Levator Scapulae",
                "Sternocleidomastoid",
            ]
        )

        inhibited.update(
            [
                "Deep Neck Flexors",
                "Lower Trapezius",
            ]
        )

        corrective.extend(
            [
                {
                    "exercise": "Chin Tucks",
                    "dosage": "3x12",
                },
                {
                    "exercise": "Wall Slides",
                    "dosage": "3x10",
                },
            ]
        )

    # Shoulder asymmetry

    if findings.get("PT-A02") in [
        "moderate",
        "severe",
    ]:

        hypertonic.update(
            [
                "Upper Trapezius",
            ]
        )

        inhibited.update(
            [
                "Middle Trapezius",
            ]
        )

        corrective.extend(
            [
                {
                    "exercise": "Scapular Retraction",
                    "dosage": "3x15",
                }
            ]
        )

    return {
        "hypertonic": sorted(list(hypertonic)),
        "inhibited": sorted(list(inhibited)),
        "correctiveProtocol": corrective,
    }
