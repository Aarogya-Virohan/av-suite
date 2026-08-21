from fastapi import APIRouter
from fastapi import File
from fastapi import Form
from fastapi import UploadFile

from app.services.posture.detector import detect_pose

from app.services.posture.calculator import (
    calc_cva,
    calc_shoulder_asymmetry,
    calc_trunk_lateral_shift,
    calc_pelvic_obliquity,
    calc_ear_level_asymmetry,
)

from app.services.posture.classifier import classify

from app.services.posture.synthesizer import generate_synthesis

from app.services.posture.scoring import calculate_global_index

from app.services.posture.report_builder import (
    build_side_view_result,
    build_report_response,
    measurement,
)

import json
from pathlib import Path

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
    # Landmark Detection
    # ---------------------------------

    # For now use side image as primary analysis
    # Front/back processing can be added later
    landmarks = detect_pose(side_bytes)

    # ---------------------------------
    # Calculations
    # ---------------------------------

    cva = calc_cva(landmarks)

    shoulder_asymmetry = calc_shoulder_asymmetry(landmarks)
    trunk_shift = calc_trunk_lateral_shift(landmarks)
    pelvic_obliquity = calc_pelvic_obliquity(landmarks)
    ear_asymmetry = calc_ear_level_asymmetry(landmarks)

    # ---------------------------------
    # Classification
    # ---------------------------------

    findings = {
        "PT-L01": classify("PT-L01", cva),
        "PT-A02": classify("PT-A02", shoulder_asymmetry),
        "PT-A03": classify("PT-A03", trunk_shift),
        "PT-A04": classify("PT-A04", pelvic_obliquity),
        "PT-A10": classify("PT-A10", ear_asymmetry),
    }

    # ---------------------------------
    # Measurements
    # ---------------------------------

    measurements = [
        measurement("PT-L01", "Forward Head (CVA)", cva, "°", findings["PT-L01"]),
        measurement(
            "PT-A02", "Shoulder Asymmetry", shoulder_asymmetry, "mm", findings["PT-A02"]
        ),
        measurement(
            "PT-A03", "Trunk Lateral Shift", trunk_shift, "mm", findings["PT-A03"]
        ),
        measurement(
            "PT-A04", "Pelvic Obliquity", pelvic_obliquity, "mm", findings["PT-A04"]
        ),
        measurement(
            "PT-A10", "Ear Level Asymmetry", ear_asymmetry, "mm", findings["PT-A10"]
        ),
    ]

    # ---------------------------------
    # Views
    # ---------------------------------

    side_view = build_side_view_result(
        measurements=measurements, photo_url="/mock/side_annotated.jpg"
    )

    front_view = {
        "photoUrl": "",
        "accuracy": 0.95,
        "measurements": [],
        "interpretation": "Front view uploaded successfully. Analysis pipeline pending.",
    }

    back_view = {
        "photoUrl": "",
        "accuracy": 0.95,
        "measurements": [],
        "interpretation": "Back view uploaded successfully. Analysis pipeline pending.",
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
