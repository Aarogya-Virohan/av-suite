from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

from app.services.posture.detector import detect_pose
from app.services.posture.calculator import calc_cva
from app.services.posture.classifier import classify

from app.services.posture.synthesizer import generate_synthesis

from app.services.posture.report_builder import (
    build_side_view_result,
    build_report_response,
)

router = APIRouter(prefix="/posture", tags=["posture"])


@router.post("/analyze")
async def analyze_posture(side_image: UploadFile = File(...)):

    image_bytes = await side_image.read()

    landmarks = detect_pose(image_bytes)

    cva = calc_cva(landmarks)

    severity = classify("PT-L01", cva)

    side_view = build_side_view_result(cva, severity)

    synthesis = generate_synthesis(severity)

    report = build_report_response(side_view, synthesis)

    return report
