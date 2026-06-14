# Posture Tool — Permanently Blocked Parameters

These parameters from `AV_Suite_Clinical_Reference_v2.xlsx`
(`Posture_Static` sheet) are **not implemented and are not planned**,
because they cannot be reliably computed from a single 2D static photo
using MediaPipe Pose (33 body landmarks). This is a documented design
limitation, not missing work — do not file these as bugs or open
tickets against the Posture Tool.

| Param ID | Name | Reason blocked |
|---|---|---|
| PT-A07 | Foot Progression Angle (Anterior) | Requires the angle of the foot's long axis relative to the direction of walking/progression. A single static anterior photo has no "direction of progression" — this is inherently a gait parameter, only measurable from video or a marked walkway. |
| PT-A09 | Wrist Alignment at Rest | Distinguishing radial/ulnar deviation from flexion/extension requires the orientation of the hand itself (knuckle/finger landmarks), not just the elbow-wrist line. MediaPipe Pose's 33 landmarks include the wrist point but no hand landmarks — that requires the separate MediaPipe **Hands** model (21 landmarks/hand), which is a distinct, unbuilt pipeline (see `hand_detector.py` note in the clinical reference). |
| PT-L02 | Thoracic Kyphosis Angle | The clinical reference itself notes MediaPipe cannot directly measure a Cobb-equivalent angle — it requires spinal curvature landmarks between the shoulders and hips that do not exist in the 33-point Pose model. Any approximation using only shoulder/hip points would not reflect actual thoracic curvature. |
| PT-L03 | Lumbar Lordosis Angle | Same root cause as PT-L02 — requires lumbar spine landmarks. The clinical reference recommends an inclinometer / modified Schober test as the real-world measurement; no photo-based proxy is clinically defensible. |
| PT-L04 | Anterior Pelvic Tilt | Requires the ASIS-PSIS line (anterior/posterior superior iliac spine points) to compute pelvic tilt in the sagittal plane. MediaPipe Pose only provides a single hip-center landmark (23/24) per side — not the two distinct bony landmarks needed for this angle. |
| PT-L07 | Diaphragmatic Breathing Pattern | Explicitly defined in the clinical reference as "VISUAL ONLY — not MediaPipe calculated", requiring observation of 3 full breath cycles. This is a **video** requirement (multi-frame, time-series), fundamentally incompatible with the Posture Tool's single-static-photo model. |

## If priorities change

- **PT-A09** becomes feasible if/when the MediaPipe Hands pipeline
  (`hand_detector.py`, Phase 2 per the clinical reference) is built —
  at that point it would move to a "future work" list, not this one.
- **PT-L07** would require a short video-upload feature, a different
  product surface than the current photo-based flow.
- **PT-A07, PT-L02, PT-L03, PT-L04** have no realistic path with the
  current single-photo, Pose-only architecture. These would need
  either a different camera setup (e.g. multiple angles with
  triangulation) or manual clinician input (goniometer/inclinometer
  readings entered directly into the CDSS intake form, which is already
  the documented path in `Clinical_ROM`).
