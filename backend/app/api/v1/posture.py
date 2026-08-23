from fastapi import APIRouter, HTTPException
from fastapi import Body
from fastapi import File
from fastapi import Form
from fastapi import UploadFile
from fastapi.responses import Response

import base64
import json
from datetime import date
from pathlib import Path

from app.services.posture.detector import (
    detect_pose_full,
    check_visibility,
    get_image_dimensions,
)
from app.services.posture.exceptions import InsufficientVisibilityError
from app.services.posture.pdf_service import generate_posture_pdf

from app.services.posture.calculator import (
    calc_cva,
    calc_forward_trunk_lean,
    get_lateral_side,
    calc_head_lateral_tilt,
    calc_pelvic_obliquity,
    calc_knee_frontal_deviation,
    calc_knee_hyperextension,
    calc_elbow_carrying_angle,
    estimate_pixels_per_cm,
    calc_shoulder_asymmetry_mm,
    calc_ear_level_asymmetry_mm,
    calc_trunk_lateral_shift_mm,
    calc_trunk_lateral_deviation_mm,
    calc_scapular_height_asymmetry_mm,
    calc_heel_valgus,
    calc_pelvic_rotation,
    calc_bilateral_toe_asymmetry,
    calc_detection_confidence,
    NOSE,
    LEFT_EAR,
    RIGHT_EAR,
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_ELBOW,
    RIGHT_ELBOW,
    LEFT_WRIST,
    RIGHT_WRIST,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_KNEE,
    RIGHT_KNEE,
    LEFT_ANKLE,
    RIGHT_ANKLE,
    LEFT_HEEL,
    RIGHT_HEEL,
    LEFT_FOOT_INDEX,
    RIGHT_FOOT_INDEX,
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


def _annotate_or_blank(image_bytes: bytes, pose_results) -> str:
    try:
        annotated_bytes = annotate_pose(image_bytes, pose_results)
        return "data:image/jpeg;base64," + base64.b64encode(annotated_bytes).decode("utf-8")
    except ValueError:
        return ""


@router.post("/analyze")
async def analyze_posture(
    front_image: UploadFile = File(...),
    side_image: UploadFile = File(...),
    back_image: UploadFile = File(...),
    patient_name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    case_ref: str = Form(...),
    patient_height_cm: float = Form(...),
    clinician_name: str = Form(""),
):

    # ---------------------------------
    # Read Uploaded Images
    # ---------------------------------

    # Height drives the pixel-to-millimetre calibration in
    # estimate_pixels_per_cm. An out-of-range value does not fail loudly --
    # it silently rescales every millimetre parameter in the report, so a
    # typo of 17 for 170 would produce confident readings that are wrong by
    # a factor of ten. Reject it here rather than reporting it.
    if not 50 <= patient_height_cm <= 250:
        raise HTTPException(
            status_code=422,
            detail=(
                "Patient height must be between 50 and 250 cm. "
                f"Received: {patient_height_cm} cm."
            ),
        )

    front_bytes = await front_image.read()
    side_bytes = await side_image.read()
    back_bytes = await back_image.read()

    findings: dict[str, str] = {}

    # =========================================================================
    # SIDE (LATERAL) PLANE
    # =========================================================================

    try:
        side_landmarks, side_results = detect_pose_full(side_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Side image: pose detection failed: {str(e)}")

    lateral_side = get_lateral_side(side_landmarks)

    ear_idx = LEFT_EAR if lateral_side == "left" else RIGHT_EAR
    shoulder_idx_lat = LEFT_SHOULDER if lateral_side == "left" else RIGHT_SHOULDER
    hip_idx_lat = LEFT_HIP if lateral_side == "left" else RIGHT_HIP

    side_measurements = []

    # PT-L01 — Forward Head (CVA)
    try:
        check_visibility(side_landmarks, [ear_idx, shoulder_idx_lat])

        cva = calc_cva(side_landmarks, side=lateral_side)
        severity = classify("PT-L01", cva)
        findings["PT-L01"] = severity

        side_measurements.append(
            measurement("PT-L01", "Forward Head (CVA)", cva, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        side_measurements.append(
            measurement("PT-L01", "Forward Head (CVA)", None, "\u00b0", "insufficient_data")
        )

    # PT-L05 — Forward Trunk Lean
    try:
        check_visibility(side_landmarks, [shoulder_idx_lat, hip_idx_lat])

        trunk_lean = calc_forward_trunk_lean(side_landmarks, side=lateral_side)
        severity = classify("PT-L05", trunk_lean)
        findings["PT-L05"] = severity

        side_measurements.append(
            measurement("PT-L05", "Forward Trunk Lean", trunk_lean, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        side_measurements.append(
            measurement("PT-L05", "Forward Trunk Lean", None, "\u00b0", "insufficient_data")
        )

    # PT-L06 — Knee Hyperextension (Genu Recurvatum)

    knee_idx_lat = LEFT_KNEE if lateral_side == "left" else RIGHT_KNEE
    ankle_idx_lat = LEFT_ANKLE if lateral_side == "left" else RIGHT_ANKLE

    try:
        check_visibility(
            side_landmarks,
            [hip_idx_lat, knee_idx_lat, ankle_idx_lat, ear_idx, shoulder_idx_lat],
        )

        knee_hyperext = calc_knee_hyperextension(side_landmarks, side=lateral_side)
        severity = classify("PT-L06", knee_hyperext)
        findings["PT-L06"] = severity

        side_measurements.append(
            measurement("PT-L06", "Knee Hyperextension", knee_hyperext, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        side_measurements.append(
            measurement("PT-L06", "Knee Hyperextension", None, "\u00b0", "insufficient_data")
        )

    side_photo_url = _annotate_or_blank(side_bytes, side_results)

    side_view = build_side_view_result(
        measurements=side_measurements,
        photo_url=side_photo_url,
        accuracy=calc_detection_confidence(side_landmarks),
    )

    # =========================================================================
    # FRONT (ANTERIOR) PLANE
    # =========================================================================

    try:
        front_landmarks, front_results = detect_pose_full(front_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Front image: pose detection failed: {str(e)}")

    front_measurements = []

    front_width_px, front_height_px = get_image_dimensions(front_bytes)

    # PT-A01 — Head Lateral Tilt
    try:
        check_visibility(front_landmarks, [NOSE, LEFT_SHOULDER, RIGHT_SHOULDER])

        head_tilt = calc_head_lateral_tilt(front_landmarks)
        severity = classify("PT-A01", head_tilt)
        findings["PT-A01"] = severity

        front_measurements.append(
            measurement("PT-A01", "Head Lateral Tilt", head_tilt, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        front_measurements.append(
            measurement("PT-A01", "Head Lateral Tilt", None, "\u00b0", "insufficient_data")
        )

    # PT-A04 — Pelvic Obliquity
    try:
        check_visibility(front_landmarks, [LEFT_HIP, RIGHT_HIP])

        obliquity = calc_pelvic_obliquity(front_landmarks)
        severity = classify("PT-A04", obliquity)
        findings["PT-A04"] = severity

        front_measurements.append(
            measurement("PT-A04", "Pelvic Obliquity", obliquity, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        front_measurements.append(
            measurement("PT-A04", "Pelvic Obliquity", None, "\u00b0", "insufficient_data")
        )

    # PT-A05 / PT-A06 — Knee Valgus / Varus (bilateral)

    direction_labels = {
        "valgus": "Knee Valgus",
        "varus": "Knee Varus",
        "neutral": "Knee Alignment",
    }

    direction_param = {
        "valgus": "PT-A05",
        "varus": "PT-A06",
        "neutral": "PT-A06",
    }

    for side_label, hip_i, knee_i, ankle_i in [
        ("Left", LEFT_HIP, LEFT_KNEE, LEFT_ANKLE),
        ("Right", RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE),
    ]:
        try:
            check_visibility(front_landmarks, [hip_i, knee_i, ankle_i])

            side_key = "left" if side_label == "Left" else "right"
            deviation, direction = calc_knee_frontal_deviation(front_landmarks, side_key)

            param_id = direction_param[direction]
            severity = classify(param_id, deviation, gender=gender)
            findings[f"{param_id}_{side_key}"] = severity

            front_measurements.append(
                measurement(
                    param_id,
                    f"{direction_labels[direction]} ({side_label})",
                    deviation,
                    "\u00b0",
                    severity,
                )
            )

        except InsufficientVisibilityError:
            front_measurements.append(
                measurement(
                    "PT-A05",
                    f"Knee Alignment ({side_label})",
                    None,
                    "\u00b0",
                    "insufficient_data",
                )
            )

    # PT-A08 — Elbow Carrying Angle (bilateral)

    for side_label, shoulder_i, elbow_i, wrist_i, side_key in [
        ("Left", LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST, "left"),
        ("Right", RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST, "right"),
    ]:
        try:
            check_visibility(front_landmarks, [shoulder_i, elbow_i, wrist_i])

            carrying_angle = calc_elbow_carrying_angle(front_landmarks, side_key)

            if abs(carrying_angle) < 1.5:
                # Near-zero deviation is measurement noise on an
                # essentially straight arm, not a clinical finding -
                # same "neutral" treatment as calc_knee_frontal_deviation
                # (PT-A05/A06).
                severity = "none"
            elif carrying_angle < 0:
                # Varus deviation is always severe, regardless of magnitude.
                severity = "severe"
            else:
                severity = classify("PT-A08", carrying_angle, gender=gender)

            findings[f"PT-A08_{side_key}"] = severity

            front_measurements.append(
                measurement(
                    "PT-A08",
                    f"Elbow Carrying Angle ({side_label})",
                    carrying_angle,
                    "\u00b0",
                    severity,
                )
            )

        except InsufficientVisibilityError:
            front_measurements.append(
                measurement(
                    "PT-A08",
                    f"Elbow Carrying Angle ({side_label})",
                    None,
                    "\u00b0",
                    "insufficient_data",
                )
            )

    # PT-A02 / PT-A03 / PT-A10 — millimetre measurements (need patient height for calibration)

    pixels_per_cm = estimate_pixels_per_cm(front_landmarks, front_height_px, patient_height_cm)

    mm_params = [
        ("PT-A02", "Shoulder Level Asymmetry", LEFT_SHOULDER, RIGHT_SHOULDER, "y"),
        ("PT-A10", "Ear Level Asymmetry", LEFT_EAR, RIGHT_EAR, "y"),
    ]

    for param_id, label, left_idx, right_idx, _axis in mm_params:
        try:
            check_visibility(front_landmarks, [left_idx, right_idx])

            if pixels_per_cm is None:
                front_measurements.append(
                    measurement(param_id, label, None, "mm", "not_available")
                )
                continue

            if param_id == "PT-A02":
                value = calc_shoulder_asymmetry_mm(front_landmarks, front_height_px, pixels_per_cm)
            else:
                value = calc_ear_level_asymmetry_mm(front_landmarks, front_height_px, pixels_per_cm)

            severity = classify(param_id, value)
            findings[param_id] = severity

            front_measurements.append(measurement(param_id, label, value, "mm", severity))

        except InsufficientVisibilityError:
            front_measurements.append(
                measurement(param_id, label, None, "mm", "insufficient_data")
            )

    # PT-A03 — Trunk Lateral Shift
    try:
        check_visibility(front_landmarks, [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP])

        if pixels_per_cm is None:
            front_measurements.append(
                measurement("PT-A03", "Trunk Lateral Shift", None, "mm", "not_available")
            )
        else:
            trunk_shift = calc_trunk_lateral_shift_mm(front_landmarks, front_width_px, pixels_per_cm)
            severity = classify("PT-A03", trunk_shift)
            findings["PT-A03"] = severity

            front_measurements.append(
                measurement("PT-A03", "Trunk Lateral Shift", trunk_shift, "mm", severity)
            )

    except InsufficientVisibilityError:
        front_measurements.append(
            measurement("PT-A03", "Trunk Lateral Shift", None, "mm", "insufficient_data")
        )

    front_photo_url = _annotate_or_blank(front_bytes, front_results)

    front_view = build_side_view_result(
        measurements=front_measurements,
        photo_url=front_photo_url,
        accuracy=calc_detection_confidence(front_landmarks),
    )

    # =========================================================================
    # BACK (POSTERIOR) PLANE
    # =========================================================================

    try:
        back_landmarks, back_results = detect_pose_full(back_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Back image: pose detection failed: {str(e)}")

    back_measurements = []

    back_width_px, back_height_px = get_image_dimensions(back_bytes)

    back_pixels_per_cm = estimate_pixels_per_cm(back_landmarks, back_height_px, patient_height_cm)

    # PT-P01 — Trunk Lateral Deviation
    try:
        check_visibility(back_landmarks, [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ANKLE, RIGHT_ANKLE])

        if back_pixels_per_cm is None:
            back_measurements.append(
                measurement("PT-P01", "Trunk Lateral Deviation", None, "mm", "not_available")
            )
        else:
            trunk_deviation = calc_trunk_lateral_deviation_mm(back_landmarks, back_width_px, back_pixels_per_cm)
            severity = classify("PT-P01", trunk_deviation)
            findings["PT-P01"] = severity

            back_measurements.append(
                measurement("PT-P01", "Trunk Lateral Deviation", trunk_deviation, "mm", severity)
            )

    except InsufficientVisibilityError:
        back_measurements.append(
            measurement("PT-P01", "Trunk Lateral Deviation", None, "mm", "insufficient_data")
        )

    # PT-P02 — Scapular Height Asymmetry
    try:
        check_visibility(back_landmarks, [LEFT_SHOULDER, RIGHT_SHOULDER])

        if back_pixels_per_cm is None:
            back_measurements.append(
                measurement("PT-P02", "Scapular Height Asymmetry", None, "mm", "not_available")
            )
        else:
            scapular = calc_scapular_height_asymmetry_mm(back_landmarks, back_height_px, back_pixels_per_cm)
            severity = classify("PT-P02", scapular)
            findings["PT-P02"] = severity

            back_measurements.append(
                measurement("PT-P02", "Scapular Height Asymmetry", scapular, "mm", severity)
            )

    except InsufficientVisibilityError:
        back_measurements.append(
            measurement("PT-P02", "Scapular Height Asymmetry", None, "mm", "insufficient_data")
        )

    # PT-P03 — Heel Valgus (bilateral)
    for side_label, knee_i, ankle_i, heel_i, side_key in [
        ("Left", LEFT_KNEE, LEFT_ANKLE, LEFT_HEEL, "left"),
        ("Right", RIGHT_KNEE, RIGHT_ANKLE, RIGHT_HEEL, "right"),
    ]:
        try:
            check_visibility(back_landmarks, [knee_i, ankle_i, heel_i])

            heel_valgus = calc_heel_valgus(back_landmarks, side_key)
            severity = classify("PT-P03", heel_valgus)
            findings[f"PT-P03_{side_key}"] = severity

            back_measurements.append(
                measurement("PT-P03", f"Heel Valgus ({side_label})", heel_valgus, "\u00b0", severity)
            )

        except InsufficientVisibilityError:
            back_measurements.append(
                measurement("PT-P03", f"Heel Valgus ({side_label})", None, "\u00b0", "insufficient_data")
            )

    # PT-P04 — Pelvic Rotation
    try:
        check_visibility(back_landmarks, [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP])

        pelvic_rotation = calc_pelvic_rotation(back_landmarks)
        severity = classify("PT-P04", pelvic_rotation)
        findings["PT-P04"] = severity

        back_measurements.append(
            measurement("PT-P04", "Pelvic Rotation", pelvic_rotation, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        back_measurements.append(
            measurement("PT-P04", "Pelvic Rotation", None, "\u00b0", "insufficient_data")
        )

    # PT-P05 — Bilateral Toe Angle Asymmetry
    try:
        check_visibility(back_landmarks, [LEFT_HEEL, RIGHT_HEEL, LEFT_FOOT_INDEX, RIGHT_FOOT_INDEX])

        toe_asymmetry = calc_bilateral_toe_asymmetry(back_landmarks)
        severity = classify("PT-P05", toe_asymmetry)
        findings["PT-P05"] = severity

        back_measurements.append(
            measurement("PT-P05", "Bilateral Toe Angle Asymmetry", toe_asymmetry, "\u00b0", severity)
        )

    except InsufficientVisibilityError:
        back_measurements.append(
            measurement("PT-P05", "Bilateral Toe Angle Asymmetry", None, "\u00b0", "insufficient_data")
        )

    back_photo_url = _annotate_or_blank(back_bytes, back_results)

    back_view = build_side_view_result(
        measurements=back_measurements,
        photo_url=back_photo_url,
        accuracy=calc_detection_confidence(back_landmarks),
    )

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
        "assessmentDate": date.today().isoformat(),
        "clinician": clinician_name,
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


# =============================================================================
# PDF EXPORT
# =============================================================================
# The frontend previously "exported" the report with window.print(), which
# printed the on-screen dashboard: browser URL and timestamp on every page,
# interactive buttons in the patient's copy, and measurements landing on a
# different page from the image they came from. This endpoint renders the same
# report data as a document designed for paper instead.


@router.post("/report/pdf")
async def export_posture_pdf(report: dict = Body(...)):
    """
    Render an already-computed posture report to a clinical PDF.

    Takes the report payload the frontend already holds, so the MediaPipe
    analysis is not re-run just to produce a document.
    """

    try:
        pdf_bytes = generate_posture_pdf(report)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}",
        )

    patient_name = ""
    if isinstance(report.get("patient"), dict):
        patient_name = str(report["patient"].get("name") or "")

    safe_name = "".join(
        c for c in patient_name if c.isalnum() or c in ("-", "_")
    ) or "report"

    filename = f"posture-assessment-{safe_name}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
