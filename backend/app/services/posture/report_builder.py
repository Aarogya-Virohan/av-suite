from typing import Any


def build_side_view_result(
    cva: float,
    severity: str,
    photo_url: str,
) -> dict[str, Any]:

    interpretation = (
        "Forward head posture detected."
        if severity in ["moderate", "severe"]
        else "Cervical posture within acceptable range."
    )

    return {
        "photoUrl": photo_url,
        "accuracy": 0.98,
        "measurements": [
            {
                "paramId": "PT-L01",
                "label": "Forward Head (CVA)",
                "value": round(cva, 2),
                "unit": "°",
                "severityLabel": severity.upper(),
                "severity": severity,
            }
        ],
        "interpretation": interpretation,
    }


def build_report_response(
    patient: dict[str, Any],
    side_view: dict[str, Any],
    front_view: dict[str, Any],
    back_view: dict[str, Any],
    synthesis: dict[str, Any],
    global_index: dict[str, Any],
) -> dict[str, Any]:

    return {
        "patient": patient,
        "views": {
            "side": side_view,
            "front": front_view,
            "back": back_view,
        },
        "synthesis": synthesis,
        "globalIndex": global_index,
    }
