from fastapi import APIRouter, HTTPException
from fastapi import File
from fastapi import Form
from fastapi import UploadFile

import base64
import json
from pathlib import Path

from app.services.posture.detector import detect_pose_full, check_visibility
from app.services.posture.exceptions import InsufficientVisibilityError

from app.services.posture.calculator import (
    calc_cva,
    calc_forward_trunk_lean,
    get_lateral_side,
    LEFT_EAR,
    RIGHT_EAR,
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_HIP,
    RIGHT_HIP,
)

from app.services.posture.classifier import classify

from app.services.posture.annotator import annotate_pose

from app.services.posture.synthesizer import generate_synthesis

from app.services.posture.scoring import calculate_global_index

from app.services.posture.report_builder import (
    build_side_view_result,
    build_report_response,
    measurement,
)

router = APIRouter(prefix="/posture", tags=["posture"])


@router.post("/analyze")
async def analyze_posture(
    front_image: UploadFile = File(...),
    side_image: UploadFile = File(...),
    back_image: UploadFile = File(...),
    patient_name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    case_ref: str = Form(...),
):

    # ---------------------------------
    # Read Uploaded Images
    # ---------------------------------

    front_bytes = await front_image.read()
    side_bytes = await side_image.read()
    back_bytes = await back_image.read()

    # ---------------------------------
    # Landmark Detection (Side / Lateral Plane)
    # ---------------------------------

    try:
        landmarks, pose_results = detect_pose_full(side_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Pose detection failed: {str(e)}")

    # Pick whichever side (left/right) is actually facing the camera
    lateral_side = get_lateral_side(landmarks)

    ear_idx = LEFT_EAR if lateral_side == "left" else RIGHT_EAR
    shoulder_idx = LEFT_SHOULDER if lateral_side == "left" else RIGHT_SHOULDER
    hip_idx = LEFT_HIP if lateral_side == "left" else RIGHT_HIP

    measurements = []
    findings: dict[str, str] = {}

    # ---------------------------------
    # PT-L01 — Craniovertebral Angle (Forward Head)
    # ---------------------------------

    try:
        check_visibility(landmarks, [ear_idx, shoulder_idx])

        cva = calc_cva(landmarks, side=lateral_side)
        severity = classify("PT-L01", cva)
        findings["PT-L01"] = severity

        measurements.append(
            measurement("PT-L01", "Forward Head (CVA)", cva, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        measurements.append(
            measurement("PT-L01", "Forward Head (CVA)", None, "\u00b0", "insufficient_data")
        )

    # ---------------------------------
    # PT-L05 — Forward Trunk Lean
    # ---------------------------------

    try:
        check_visibility(landmarks, [shoulder_idx, hip_idx])

        trunk_lean = calc_forward_trunk_lean(landmarks, side=lateral_side)
        severity = classify("PT-L05", trunk_lean)
        findings["PT-L05"] = severity

        measurements.append(
            measurement("PT-L05", "Forward Trunk Lean", trunk_lean, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        measurements.append(
            measurement("PT-L05", "Forward Trunk Lean", None, "\u00b0", "insufficient_data")
        )

    # ---------------------------------
    # Annotated Side Image (skeleton overlay)
    # ---------------------------------

    try:
        annotated_bytes = annotate_pose(side_bytes, pose_results)
        side_photo_url = (
            "data:image/jpeg;base64," + base64.b64encode(annotated_bytes).decode("utf-8")
        )
    except ValueError:
        side_photo_url = ""

    # ---------------------------------
    # Views
    # ---------------------------------

    side_view = build_side_view_result(
        measurements=measurements, photo_url=side_photo_url
    )

    front_view = {
        "photoUrl": "",
        "accuracy": 0.95,
        "measurements": [],
        "interpretation": (
            "Front view uploaded successfully. Anterior-plane analysis "
            "(shoulder, pelvic, and knee alignment) is part of the next "
            "update to this tool."
        ),
    }

    back_view = {
        "photoUrl": "",
        "accuracy": 0.95,
        "measurements": [],
        "interpretation": (
            "Back view uploaded successfully. Posterior-plane analysis "
            "(spinal alignment, scapular symmetry) is part of the next "
            "update to this tool."
        ),
    }

    # ---------------------------------
    # Clinical Synthesis
    # ---------------------------------

    synthesis = generate_synthesis(findings)

    # ---------------------------------
    # Global Stability Index
    # ---------------------------------

    global_index = calculate_global_index(findings.values())

    # ---------------------------------
    # Patient
    # ---------------------------------

    patient = {
        "name": patient_name,
        "age": age,
        "gender": gender,
        "caseRef": case_ref,
    }

    # ---------------------------------
    # Final Report
    # ---------------------------------

    report = build_report_response(
        patient=patient,
        side_view=side_view,
        front_view=front_view,
        back_view=back_view,
        synthesis=synthesis,
        global_index=global_index,
    )

    reports_dir = Path("data/reports")

    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        reports_dir / f"{case_ref}.json",
        "w",
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
        )

    return report
