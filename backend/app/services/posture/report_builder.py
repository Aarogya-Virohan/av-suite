from typing import Any


def measurement(
    param_id: str,
    label: str,
    value: float,
    unit: str,
    severity: str,
) -> dict[str, Any]:

    return {
        "paramId": param_id,
        "label": label,
        "value": round(value, 2),
        "unit": unit,
        "severityLabel": severity.upper(),
        "severity": severity,
    }


def build_side_view_result(
    measurements: list[dict[str, Any]],
    photo_url: str,
) -> dict[str, Any]:

    severe_findings = [
        m["label"] for m in measurements if m["severity"] in ["moderate", "severe"]
    ]

    if severe_findings:
        interpretation = "Postural deviations detected in: " + ", ".join(
            severe_findings
        )
    else:
        interpretation = "Posture appears within acceptable limits."

    return {
        "photoUrl": photo_url,
        "accuracy": 0.98,
        "measurements": measurements,
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
