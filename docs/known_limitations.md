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
| PT-L08 | Foot Arch Height | **Implemented and then removed during testing (2026-06-14).** The only candidate landmarks for "arch height" in MediaPipe Pose are Ankle (27/28), Heel (29/30), and Foot Index (31/32) — there is no navicular/mid-foot landmark. Perpendicular distance from Ankle to the Heel→Foot-Index line measures **ankle malleolus height above the ground**, not medial longitudinal arch height; on a real test photo this produced ~82mm against a clinical normal range of 8-15mm (5-8x off — not an approximation error, a different anatomical quantity entirely). No MediaPipe-only formula can produce a clinically meaningful arch-height value with the current 33-point Pose model. |

## Withdrawn after testing on real photographs, 1 October 2026

These two were built, shipped, and then measured against seven team
photographs with tape-measured heights. Both are withdrawn from the
report. The calculations and their threshold bands are left in the source
and nothing calls them, so they can return if the landmark problem below
is ever solved.

| Param ID | Name | Reason withdrawn |
|---|---|---|
| PT-P05 | Bilateral Toe Angle Asymmetry | The foot-index landmark is not observed from behind. Across seven subjects, ankle-to-toe distance measured 18 to 133 pixels on the back view against 304 to 395 on the front view of the same person, on all 14 legs. The model places the toe point by inference when the foot is hidden behind the leg, which is every posterior photograph. Google's own issue tracker carries a report of heel and toe keypoints landing in the wrong place on the occluded leg. The parameter was grading an angle between two points, one of which is not seen. On the sample set it returned 21.5 and 14.5 degrees SEVERE on subjects with no foot complaint. |
| PT-P03 | Rearfoot / Calcaneal Alignment | The heel landmark is visible from behind and lands on the heel in most photographs, so this one failed differently. Published error for rearfoot eversion angle from a phone camera is 8.2 degrees mean absolute, against a clinically meaningful threshold of about 3 degrees, because pose models infer eversion from heel position rather than from calcaneal motion and assume a rigid foot. Our entire band range sits inside that error. On our own seven subjects the parameter returned varus on 14 of 14 legs, 12 of them SEVERE, against a published healthy population mean of 6.07 degrees of valgus. A result that is the opposite of the population on every subject is not a band problem. |

### A third finding, which is not parameter-specific

MediaPipe's visibility score does not detect a misplaced landmark. On one
of the seven subjects every lower-limb landmark on the back view collapsed
onto the floor between the feet, several hundred pixels from any foot, and
the ankle and heel still reported visibility of 0.80 and 0.83, above our
0.65 threshold. The score expresses confidence that a point is within the
frame, not that it is in the right place, so no threshold on it would have
caught this.

A geometric check was attempted and does not work. The ankle-to-heel
distance as a fraction of knee-to-ankle distance was measured on all 42
legs in the sample. The collapsed photograph scored 0.068 while two
correct photographs scored 0.073 and 0.077, so there is no line to draw
between them. This is recorded here because the obvious fix has already
been tried and failed, and because it affects every parameter, not only
the two above.

## Withdrawn because it measures nothing of its own, 2 October 2026

| Param ID | Name | Reason withdrawn |
|---|---|---|
| PT-P04 | Pelvic Rotation | It has no quantity of its own. The function takes the shoulder line angle and subtracts the hip line angle. With the shoulder line forced level it returns exactly PT-A04 (Pelvic Obliquity), verified to within 0.01 degrees on all seven test subjects. When the shoulders are not level the difference is shoulder tilt added into a row about the pelvis: on one subject the hip line was 1.89 degrees, which is normal, the shoulder line was 3.30, and the parameter reported 5.19 and would have graded it MILD on a normal pelvis. The two parameters also disagreed with each other, because their bands were never harmonised: the same hip value of 4.2 degrees grades MILD as PT-A04 and NONE as PT-P04, and PT-P04 is one tier softer across the whole range. Nothing is lost by removing it, since the quantity it reduces to is already reported from the front view on tighter bands. The name also claimed axial rotation, which no single 2D photograph can see. |

Withdrawn, not deleted, on the same terms as PT-P03 and PT-P05. The
calculation and its bands stay in the source with nothing calling them.
Its muscle and exercise mapping is removed.

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
- **PT-L08** would need either a manual clinician input (footprint/
  Wet Test or arch-height caliper measurement entered directly, same
  CDSS-intake path as above), or a fundamentally different vision
  approach (e.g. a foot-only photo from below/behind with a navicular
  marker) — not a fix to the existing whole-body Pose pipeline.

## Measured but not comparable to published norms

### PT-L05 Forward Trunk Lean, 1 October 2026

The parameter stays on the report. It is repeatable: the same photograph
re-encoded at 100, 85 and 70 percent scale moves the reported angle by
0.43 degrees on average and 0.72 at worst, against reported values of 0.9
to 3.5 degrees on the same six subjects. The measurement is not noise.

What the absolute number cannot do is be read against a published normal.
All seven subjects returned a backward lean and none returned forward.
MediaPipe gives joint centres, not bony landmarks. On a lateral view the
shoulder centre falls toward the back of the shoulder, and the hip
landmark sits at roughly waistband height rather than on the greater
trochanter, which is visible in the annotated photographs. Both push the
shoulder posterior to the hip before any real posture is involved.

The shift is not a constant that could be subtracted. Expressed as a
fraction of each subject's own shoulder-to-hip vertical distance the
offset ran 0.0158 to 0.0610, mean 0.0395, cv 0.426 across six subjects.
One subject, po-7, was excluded: its side-view detection is visibly wrong
in the annotated image, with the trunk axis leaving the body and the
shoulder point landing at the neck.

This is the same class of problem as the craniovertebral angle's
ear-to-shoulder substitution, which is already documented. The difference
is that nothing recorded it here, and the report prints a direction and a
severity with no caveat. Within-patient tracking is not established either:
that needs the same person photographed on different days, which we do not
have.
