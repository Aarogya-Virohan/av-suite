from fastapi import APIRouter, HTTPException
from fastapi import Body
from fastapi import File
from fastapi import Form
from fastapi import UploadFile
from fastapi.responses import Response

import base64
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from mediapipe.framework.formats import landmark_pb2

from app.services.posture.schemas import Landmark

from app.services.posture.detector import (
    detect_pose_full,
    check_visibility,
    check_limb_order,
    detect_iris_centres,
    get_image_dimensions,
)
from app.services.posture.exceptions import (
    ImplausibleLandmarkError,
    InsufficientVisibilityError,
)
from app.services.posture.pdf_service import generate_posture_pdf

from app.services.posture.calculator import (
    calc_cva,
    cva_head_position,
    to_geometric_space,
    calc_forward_trunk_lean,
    get_lateral_side,
    calc_head_tilt_eye_line,
    head_tilt_eye_side,
    pelvic_obliquity_side,
    posterior_shoulder_higher_side,
    ear_asymmetry_side,
    trunk_shift_side,
    calc_pelvic_obliquity,
    calc_knee_frontal_deviation,
    calc_knee_hyperextension,
    estimate_pixels_per_cm,
    calc_ear_level_asymmetry_mm,
    calc_trunk_lateral_deviation_mm,
    calc_scapular_height_asymmetry_mm,
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
)

from app.services.posture.classifier import classify

from app.services.posture.annotator import annotate_pose

from app.services.posture.synthesizer import generate_synthesis


from app.services.posture.report_builder import (
    build_side_view_result,
    build_report_response,
    measurement,
)


# PT-L06 returns a signed value: negative is hyperextension, positive is a
# flexed knee. The row label was fixed text reading "Knee Hyperextension",
# so a flexed knee printed under a hyperextension heading and the sample
# report's 5.25 degrees was flexion described as its opposite. The label
# now follows the sign. The severity bands are deliberately untouched here:
# they still grade only the hyperextension side, which needs clinical input.
KNEE_SAGITTAL_LABEL = "Knee Sagittal Alignment"

# PT-L05 is signed since 18 Sept: positive is forward, negative is
# backward. The row label previously said "Forward Trunk Lean"
# unconditionally, so a backward lean would have printed under a name
# that says the opposite of what was measured.
def _trunk_lean_label(value: float) -> str:
    if value < 0:
        return "Backward Trunk Lean"
    if value > 0:
        return "Forward Trunk Lean"
    return "Trunk Lean"


def _knee_sagittal_label(value: float) -> str:
    if value < 0:
        return "Knee Hyperextension"
    if value > 0:
        return "Knee Flexion"
    return KNEE_SAGITTAL_LABEL


# PT-P01 measures the horizontal offset between the shoulder midpoint and
# the hip midpoint. No spinal landmark is involved, because MediaPipe
# returns none, so the row cannot carry the word scoliosis on a clinic
# report above a physiotherapist signature line. Renamed 18 Sept. An
# earlier rename was reverted at 6ac72e4; this one is deliberate.
P01_LABEL = "Trunk Lateral Deviation (Posterior)"

# PT-P02 measures the two shoulder landmarks, not the scapulae.
P02_LABEL = "Shoulder Level Asymmetry"


def _rearfoot_label(value: float, side_label: str) -> str:
    """
    PT-P03 is signed, so the row name follows the direction.

    Unused since PT-P03 was withdrawn from the report on 1 October 2026.
    Kept with the calculation it labels.
    """

    if value < 0:
        return f"Rearfoot Varus ({side_label})"
    if value > 0:
        return f"Rearfoot Valgus ({side_label})"
    return f"Rearfoot Alignment ({side_label})"


router = APIRouter(prefix="/posture", tags=["posture"])



@dataclass
class DetectedView:
    """One photograph after detection, before any measurement."""

    landmarks: list[Landmark]
    width_px: int
    height_px: int
    image_bytes: bytes
    # Pupil centres in pixels, image-left first. Front view only; None when
    # Face Mesh found no face, which PT-A01 reports as insufficient data.
    iris: tuple[tuple[float, float], tuple[float, float]] | None = None


def _detect_view(name: str, image_bytes: bytes, with_iris: bool = False) -> DetectedView:
    try:
        landmarks, _results = detect_pose_full(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{name} image: pose detection failed: {str(e)}")

    width_px, height_px = get_image_dimensions(image_bytes)

    iris = None
    if with_iris:
        try:
            iris = detect_iris_centres(image_bytes, landmarks)
        except InsufficientVisibilityError:
            iris = None

    return DetectedView(landmarks, width_px, height_px, image_bytes, iris)


def _results_from_landmarks(landmarks: list[Landmark]):
    """
    A stand-in for MediaPipe's results object, built from our own points,
    so the annotator draws whatever points it is given rather than only
    what the model returned.
    """

    proto = landmark_pb2.NormalizedLandmarkList()
    for lm in landmarks:
        proto.landmark.add(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)

    return SimpleNamespace(pose_landmarks=proto)


def _annotate_or_blank(
    image_bytes: bytes,
    pose_results,
    landmarks=None,
    pixels_per_cm: float | None = None,
    view: str = "front",
) -> str:
    try:
        annotated_bytes = annotate_pose(
            image_bytes,
            pose_results,
            landmarks=landmarks,
            pixels_per_cm=pixels_per_cm,
            view=view,
        )
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
    # Whether each photograph came from the in-app capture screen or from
    # an existing file. Defaulted rather than required so an older client
    # keeps working; "unknown" is honest about not knowing.
    front_source: str = Form("unknown"),
    side_source: str = Form("unknown"),
    back_source: str = Form("unknown"),
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

    side = _detect_view("Side", side_bytes)
    front = _detect_view("Front", front_bytes, with_iris=True)
    back = _detect_view("Back", back_bytes)

    return _report_from_points(
        side=side,
        front=front,
        back=back,
        patient_name=patient_name,
        age=age,
        gender=gender,
        case_ref=case_ref,
        patient_height_cm=patient_height_cm,
        clinician_name=clinician_name,
        front_source=front_source,
        side_source=side_source,
        back_source=back_source,
    )


def _report_from_points(
    *,
    side: "DetectedView",
    front: "DetectedView",
    back: "DetectedView",
    patient_name: str,
    age: int,
    gender: str,
    case_ref: str,
    patient_height_cm: float,
    clinician_name: str,
    front_source: str,
    side_source: str,
    back_source: str,
) -> dict:
    """
    Everything after detection: measurements, grades, synthesis, report.

    Takes landmarks that have already been detected, so the same code can
    run on the model's points or on points a clinician has reviewed. Split
    out of analyze_posture on 10 October 2026 with no change in behaviour,
    verified by byte-identical reports on all seven test subjects.
    """

    findings: dict[str, str] = {}

    # =========================================================================
    # SIDE (LATERAL) PLANE
    # =========================================================================

    side_landmarks = side.landmarks
    side_results = _results_from_landmarks(side_landmarks)

    lateral_side = get_lateral_side(side_landmarks)

    side_width_px, side_height_px = side.width_px, side.height_px
    side_geo = to_geometric_space(side_landmarks, side_width_px, side_height_px)

    ear_idx = LEFT_EAR if lateral_side == "left" else RIGHT_EAR
    shoulder_idx_lat = LEFT_SHOULDER if lateral_side == "left" else RIGHT_SHOULDER
    hip_idx_lat = LEFT_HIP if lateral_side == "left" else RIGHT_HIP

    side_measurements = []

    # PT-L01 — Forward Head (CVA)
    try:
        check_visibility(side_landmarks, [NOSE, ear_idx, shoulder_idx_lat])

        cva = calc_cva(side_geo, side=lateral_side)
        severity = classify("PT-L01", cva)
        findings["PT-L01"] = severity

        head_position = cva_head_position(side_geo, side=lateral_side)

        side_measurements.append(
            measurement(
                "PT-L01",
                "Forward Head (CVA)",
                cva,
                "\u00b0",
                severity,
                side=head_position if head_position != "neutral" else None,
            )
        )

    except InsufficientVisibilityError:
        side_measurements.append(
            measurement("PT-L01", "Forward Head (CVA)", None, "\u00b0", "insufficient_data")
        )

    # PT-L05 — Forward Trunk Lean
    try:
        check_visibility(side_landmarks, [NOSE, shoulder_idx_lat, hip_idx_lat])

        trunk_lean = calc_forward_trunk_lean(side_geo, side=lateral_side)
        severity = classify("PT-L05", trunk_lean)
        findings["PT-L05"] = severity

        side_measurements.append(
            measurement(
                "PT-L05",
                _trunk_lean_label(trunk_lean),
                trunk_lean,
                "\u00b0",
                severity,
            )
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
        check_limb_order(side_landmarks, hip_idx_lat, knee_idx_lat, ankle_idx_lat)

        knee_sagittal = calc_knee_hyperextension(side_geo, side=lateral_side)
        severity = classify("PT-L06", knee_sagittal)
        findings["PT-L06"] = severity

        side_measurements.append(
            measurement(
                "PT-L06",
                _knee_sagittal_label(knee_sagittal),
                knee_sagittal,
                "\u00b0",
                severity,
            )
        )

    except (InsufficientVisibilityError, ImplausibleLandmarkError):
        # Implausible geometry reports the same way as a missing
        # landmark, because to the clinician both mean the same thing:
        # this was not measured. A 156 degree knee flexion printed as
        # NONE is worse than a blank row.
        side_measurements.append(
            measurement(
                "PT-L06", KNEE_SAGITTAL_LABEL, None, "\u00b0", "insufficient_data"
            )
        )

    # Calibration is not otherwise needed on the sagittal view, since it
    # produces no millimetre parameter. It is computed here only to scale
    # the reference grid, and a failure degrades to no grid, not an error.
    try:
        side_pixels_per_cm = estimate_pixels_per_cm(
            side_landmarks, side_height_px, patient_height_cm
        )
    except InsufficientVisibilityError:
        side_pixels_per_cm = None

    side_photo_url = _annotate_or_blank(
        side.image_bytes,
        side_results,
        landmarks=side_landmarks,
        pixels_per_cm=side_pixels_per_cm,
        view="side",
    )

    side_view = build_side_view_result(
        measurements=side_measurements,
        photo_url=side_photo_url,
        accuracy=calc_detection_confidence(side_landmarks),
        capture_source=side_source,
    )

    # =========================================================================
    # FRONT (ANTERIOR) PLANE
    # =========================================================================

    front_landmarks = front.landmarks
    front_results = _results_from_landmarks(front_landmarks)

    front_measurements = []

    front_width_px, front_height_px = front.width_px, front.height_px
    front_geo = to_geometric_space(front_landmarks, front_width_px, front_height_px)

    # PT-A01 — Head Lateral Tilt. Since 10 October 2026 the pupillary line
    # against the horizontal, per the founders' view mapping, from Face Mesh
    # iris centres. Until then it was the nose to mid-shoulder line against
    # the vertical, which is a head shift, not a tilt; calc_head_lateral_tilt
    # is left in calculator.py with nothing calling it.
    try:
        if front.iris is None:
            raise InsufficientVisibilityError("Face not found for iris landmarks")
        image_left_eye, image_right_eye = front.iris

        head_tilt = calc_head_tilt_eye_line(image_left_eye, image_right_eye)
        severity = classify("PT-A01", head_tilt)
        findings["PT-A01"] = severity

        front_measurements.append(
            measurement(
                "PT-A01",
                "Head Lateral Tilt",
                head_tilt,
                "\u00b0",
                severity,
                side=head_tilt_eye_side(image_left_eye, image_right_eye),
            )
        )

    except InsufficientVisibilityError:
        front_measurements.append(
            measurement("PT-A01", "Head Lateral Tilt", None, "\u00b0", "insufficient_data")
        )

    # PT-A04 — Pelvic Obliquity
    try:
        check_visibility(front_landmarks, [LEFT_HIP, RIGHT_HIP])

        obliquity = calc_pelvic_obliquity(front_geo)
        severity = classify("PT-A04", obliquity)
        findings["PT-A04"] = severity

        front_measurements.append(
            measurement(
                "PT-A04",
                "Pelvic Obliquity",
                obliquity,
                "\u00b0",
                severity,
                side=pelvic_obliquity_side(front_landmarks),
            )
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
            check_limb_order(front_landmarks, hip_i, knee_i, ankle_i)

            side_key = "left" if side_label == "Left" else "right"
            deviation, direction = calc_knee_frontal_deviation(front_geo, side_key)

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

        except (InsufficientVisibilityError, ImplausibleLandmarkError):
            front_measurements.append(
                measurement(
                    "PT-A05",
                    f"Knee Alignment ({side_label})",
                    None,
                    "\u00b0",
                    "insufficient_data",
                )
            )

    # PT-A08 — Elbow Carrying Angle. Withdrawn from the report on
    # 2 October 2026. The carrying angle is defined with the elbow fully
    # extended and the forearm fully supinated, which a standing posture
    # photograph does not reproduce, and no published study measures how
    # far the surface angle shifts between that position and a hanging
    # arm. The calculation and its bands are left in place; nothing calls
    # them. Removing this also retires the hardcoded varus-is-severe rule
    # and its discontinuity at -1.5 degrees, which used to live here.
    # See docs/known_limitations.md for the evidence.

    # PT-A10 — millimetre measurement (needs patient height for calibration).
    # PT-A02 (shoulder level) and PT-A03 (trunk lateral shift) left the front
    # view on 10 October 2026: the founders ruled one metric, one view, and
    # assigned both quantities to the posterior view, where PT-P02 and PT-P01
    # measure them with the same calculation. Calculations and bands are left
    # in place; nothing calls them. See docs/decisions.md, 10 October.

    # Calibration rests on NOSE and both ANKLEs. If those are not visible we
    # get no scale factor, and the millimetre parameters below cannot be
    # computed -- but the angle parameters do not depend on it and must keep
    # working, so this is caught here rather than failing the whole request.
    # The reason is carried forward so the report can say which it was.
    try:
        pixels_per_cm = estimate_pixels_per_cm(front_landmarks, front_height_px, patient_height_cm)
        calibration_status = "not_available"
    except InsufficientVisibilityError:
        pixels_per_cm = None
        calibration_status = "insufficient_data"

    mm_params = [
        ("PT-A10", "Ear Level Asymmetry", LEFT_EAR, RIGHT_EAR, "y"),
    ]

    for param_id, label, left_idx, right_idx, _axis in mm_params:
        try:
            check_visibility(front_landmarks, [left_idx, right_idx])

            if pixels_per_cm is None:
                front_measurements.append(
                    measurement(param_id, label, None, "mm", calibration_status)
                )
                continue

            value = calc_ear_level_asymmetry_mm(front_landmarks, front_height_px, pixels_per_cm)

            severity = classify(param_id, value)
            findings[param_id] = severity

            side_value = ear_asymmetry_side(front_landmarks)

            front_measurements.append(
                measurement(param_id, label, value, "mm", severity, side=side_value)
            )

        except InsufficientVisibilityError:
            front_measurements.append(
                measurement(param_id, label, None, "mm", "insufficient_data")
            )

    # PT-A03 — Trunk Lateral Shift. Moved to the posterior view on
    # 10 October 2026, see the PT-A10 comment above; PT-P01 reports it.

    front_photo_url = _annotate_or_blank(
        front.image_bytes,
        front_results,
        landmarks=front_landmarks,
        pixels_per_cm=pixels_per_cm,
        view="front",
    )

    front_view = build_side_view_result(
        measurements=front_measurements,
        photo_url=front_photo_url,
        accuracy=calc_detection_confidence(front_landmarks),
        capture_source=front_source,
    )

    # =========================================================================
    # BACK (POSTERIOR) PLANE
    # =========================================================================

    back_landmarks = back.landmarks
    back_results = _results_from_landmarks(back_landmarks)

    back_measurements = []

    back_width_px, back_height_px = back.width_px, back.height_px
    back_geo = to_geometric_space(back_landmarks, back_width_px, back_height_px)

    try:
        back_pixels_per_cm = estimate_pixels_per_cm(back_landmarks, back_height_px, patient_height_cm)
        back_calibration_status = "not_available"
    except InsufficientVisibilityError:
        back_pixels_per_cm = None
        back_calibration_status = "insufficient_data"

    # PT-P01 — Trunk Lateral Deviation (Posterior)
    try:
        check_visibility(back_landmarks, [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP])

        if back_pixels_per_cm is None:
            back_measurements.append(
                measurement("PT-P01", P01_LABEL, None, "mm", back_calibration_status)
            )
        else:
            trunk_dev = calc_trunk_lateral_deviation_mm(back_landmarks, back_width_px, back_pixels_per_cm)
            severity = classify("PT-P01", trunk_dev)
            findings["PT-P01"] = severity

            back_measurements.append(
                measurement(
                    "PT-P01",
                    P01_LABEL,
                    trunk_dev,
                    "mm",
                    severity,
                    side=trunk_shift_side(back_landmarks, "posterior"),
                )
            )

    except InsufficientVisibilityError:
        back_measurements.append(
            measurement("PT-P01", P01_LABEL, None, "mm", "insufficient_data")
        )

    # PT-P02 — Shoulder Level Asymmetry. Renamed from "Scapular Height
    # Asymmetry" on 10 October 2026: it measures the shoulder landmarks, the
    # same calculation PT-A02 used, and no scapular landmark exists. Since
    # 10 October it is the only shoulder level row on the report. The higher
    # side is read from image position, not from MediaPipe's left/right
    # labels, which were found reversed on one of seven back photographs.
    try:
        check_visibility(back_landmarks, [LEFT_SHOULDER, RIGHT_SHOULDER])

        if back_pixels_per_cm is None:
            back_measurements.append(
                measurement("PT-P02", P02_LABEL, None, "mm", back_calibration_status)
            )
        else:
            scapular = calc_scapular_height_asymmetry_mm(back_landmarks, back_height_px, back_pixels_per_cm)
            severity = classify("PT-P02", scapular)
            findings["PT-P02"] = severity

            back_measurements.append(
                measurement(
                    "PT-P02",
                    P02_LABEL,
                    scapular,
                    "mm",
                    severity,
                    side=posterior_shoulder_higher_side(back_landmarks),
                )
            )

    except InsufficientVisibilityError:
        back_measurements.append(
            measurement("PT-P02", P02_LABEL, None, "mm", "insufficient_data")
        )

    # PT-P03 — Rearfoot / calcaneal alignment. Withdrawn from the report
    # on 1 October 2026 after testing against real photographs. The
    # calculation and its bands are left in place; nothing calls them.
    # See docs/known_limitations.md for the evidence.

    # PT-P04 — Pelvic Rotation. Withdrawn from the report on 2 October
    # 2026. With the shoulder line level it returns exactly PT-A04,
    # verified on all seven test subjects; when the shoulders are not
    # level it adds shoulder tilt into a pelvic row. The calculation and
    # its bands are left in place; nothing calls them.
    # See docs/known_limitations.md for the evidence.

    # PT-P05 — Bilateral Toe Angle Asymmetry. Withdrawn from the report
    # on 1 October 2026. The foot-index landmark it rests on is not
    # observed from behind; on seven subjects the ankle-to-toe distance
    # measured 18 to 133 pixels on the back view against 304 to 395 on
    # the front. See docs/known_limitations.md.

    back_photo_url = _annotate_or_blank(
        back.image_bytes,
        back_results,
        landmarks=back_landmarks,
        pixels_per_cm=back_pixels_per_cm,
        view="back",
    )

    back_view = build_side_view_result(
        measurements=back_measurements,
        photo_url=back_photo_url,
        accuracy=calc_detection_confidence(back_landmarks),
        capture_source=back_source,
    )

    # ---------------------------------
    # Clinical Synthesis
    # ---------------------------------

    synthesis = generate_synthesis(findings)

    # Global Stability Index removed from the report on 10 October 2026 by the founders (Q5): a single
    # score masks a localised finding behind an average, and its weights were
    # never sourced. calculate_global_index stays in scoring.py with nothing
    # calling it. The founders' replacement, a regional profile, is not built
    # yet. See docs/decisions.md, 10 October.

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
