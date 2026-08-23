from typing import Any

from app.services.posture.classifier import SEVERITY_LABELS, is_borderline


def measurement(
    param_id: str,
    label: str,
    value: float,
    unit: str,
    severity: str,
) -> dict[str, Any]:

    # A grade sitting within measurement noise of a boundary is reported as
    # provisional rather than as a settled tier. Checked here because every
    # parameter in the report passes through this function.
    borderline = severity in ("none", "mild", "moderate", "severe") and is_borderline(
        param_id, value, unit
    )

    return {
        "paramId": param_id,
        "label": label,
        "value": round(value, 2) if isinstance(value, (int, float)) else value,
        "unit": unit,
        "severityLabel": SEVERITY_LABELS.get(severity, severity.upper()),
        "severity": severity,
        "borderline": borderline,
    }


def build_side_view_result(
    measurements: list[dict[str, Any]],
    photo_url: str,
    accuracy: float = 0.0,
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
        "accuracy": round(accuracy, 4),
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
