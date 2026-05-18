from .schemas import Measurement


def build_side_view_result(cva: float, severity: str):

    interpretation = (
        "Forward head posture detected."
        if severity in ["moderate", "severe"]
        else "Cervical posture within acceptable range."
    )

    return {
        "photoUrl": "/mock/side_annotated.jpg",
        "accuracy": 0.98,
        "measurements": [
            {
                "label": "Forward Head (CVA)",
                "value": round(cva, 2),
                "unit": "°",
                "severityLabel": severity.upper(),
                "severity": severity,
            }
        ],
        "interpretation": interpretation,
    }


def build_report_response(side_view, synthesis):

    return {
        "patient": {
            "name": "Demo Patient",
            "age": 28,
            "caseRef": "PT-2026-001",
            "assessmentDate": "2026-05-16",
            "clinician": "Automated System",
        },
        "views": {
            "side": side_view,
            "front": {
                "photoUrl": "/mock/front_annotated.jpg",
                "accuracy": 0.97,
                "measurements": [],
                "interpretation": "Front plane pending implementation.",
            },
            "back": {
                "photoUrl": "/mock/back_annotated.jpg",
                "accuracy": 0.96,
                "measurements": [],
                "interpretation": "Back plane pending implementation.",
            },
        },
        "synthesis": synthesis,
        "globalIndex": {"score": 75, "descriptor": "Compensatory Pattern"},
    }
