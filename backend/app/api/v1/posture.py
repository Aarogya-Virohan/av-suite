from fastapi import APIRouter
from fastapi import File
from fastapi import UploadFile

from app.services.posture.detector import detect_pose
from app.services.posture.calculator import calc_cva
from app.services.posture.classifier import classify
from app.services.posture.synthesizer import generate_synthesis
from app.services.posture.scoring import calculate_global_index

from app.services.posture.report_builder import (
    build_side_view_result,
    build_report_response,
)

router = APIRouter(
    prefix="/posture",
    tags=["posture"],
)


@router.post("/analyze")
async def analyze_posture(side_image: UploadFile = File(...)):
    """
    Analyze a side-view posture image and generate
    a clinical posture report.
    """

    image_bytes = await side_image.read()

    # Landmark Detection
    landmarks = detect_pose(image_bytes)

    # Calculations
    cva = calc_cva(landmarks)

    # Classification
    cva_severity = classify(
        "PT-L01",
        cva,
    )

    findings = {
        "PT-L01": cva_severity,
    }

    # View Results
    side_view = build_side_view_result(
        cva=cva,
        severity=cva_severity,
        photo_url="/mock/side_annotated.jpg",
    )

    # Placeholder views until
    # front/back calculations are implemented

    front_view = {
        "photoUrl": "",
        "accuracy": 0.0,
        "measurements": [],
        "interpretation": "Front view not implemented yet.",
    }

    back_view = {
        "photoUrl": "",
        "accuracy": 0.0,
        "measurements": [],
        "interpretation": "Back view not implemented yet.",
    }

    # Clinical Synthesis
    synthesis = generate_synthesis(findings)

    # Global Stability Index
    global_index = calculate_global_index(findings.values())

    # Placeholder patient
    # Will be replaced by intake flow
    patient = {
        "name": "",
        "age": None,
        "gender": "",
        "caseRef": "",
    }

    # Final Report
    report = build_report_response(
        patient=patient,
        side_view=side_view,
        front_view=front_view,
        back_view=back_view,
        synthesis=synthesis,
        global_index=global_index,
    )

    return report
