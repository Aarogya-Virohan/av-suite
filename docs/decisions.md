# Decisions

Decisions that have actually been made, with the reason and who made them.
Newest at the bottom. A suggestion under consideration does not go here.
Clinical decisions belong to Daman and Shivank; anything recorded here as a
technical decision changed no clinical claim, or is flagged for them to
overturn.

---

## 18 September 2026

Posture tool, branch `fix/posture-gsi-and-labels`. Taken by Onkar during
the threshold and sign-convention pass. Items marked FOR REVIEW moved a
number a patient sees and should be overturned if the founders disagree.

### PT-A03 and PT-P01 now use one threshold set
FOR REVIEW. The two calculation functions are byte-identical once comments
are stripped, but carried different bands, 10/20/30 mm on the front view
and 5/15/25 mm on the back. One patient could get two contradictory grades
for the same number on the same report. Both now use 5/15/25 mm. Neither
set had a published source. The tighter one was kept as the more
conservative of two unsourced options.

### PT-P03 graded against the population mean, not against zero
FOR REVIEW. In 88 healthy adults the mean relaxed calcaneal stance position
was 6.07 degrees of valgus, SD 2.71, with 95 percent between 3 and 9
degrees. The same study found the assumed 0 plus or minus 2 normal held for
under 2 percent of adults. The previous 0 to 5 normal band graded the
population mean as MILD. New bands are the study's own 95 percent range for
normal, then one SD per tier in both directions.

Known consequence worth a clinician's eye: a heel measuring exactly 0
degrees now grades MODERATE. That follows from the evidence, since a truly
neutral rearfoot is statistically unusual, but it is the first thing a
physiotherapist will challenge on a report.

### PT-P03 is signed, and its label follows the sign
The function returned magnitude only, so a varus heel printed under a label
that said valgus, which points an orthotic and an exercise the wrong way.
Positive is now valgus, negative varus. Direction is taken from the ankle
midline rather than from left/right landmark labels, so a label swap on a
posterior photograph does not flip lateral and medial.

Still open: the PT-P03 muscle mapping (peroneals hypertonic, tibialis
posterior inhibited) is correct for valgus and backwards for varus. Now
that the value is signed, that mapping needs to be direction-aware. Not
changed, because which muscles belong to which direction is a clinical
call.

### PT-P01 renamed, Schroth mapping removed
FOR REVIEW, though this was already raised on 20 August and 13 September
and remains unanswered. The row printed "Scoliosis Screen" with a severity
grade on clinic letterhead above a physiotherapist signature line. The
number is a shoulder-midpoint to hip-midpoint horizontal offset; no spinal
landmark is involved, because MediaPipe returns none. Renamed to Trunk
Lateral Deviation (Posterior). No patient's number changes and no existing
report becomes invalid.

The Schroth Method Breathing prescription attached to it was removed with
no replacement. Schroth is curve-pattern specific, the classification is
meant to be applied by certified Schroth therapists, and this parameter
produces no curve classification and no spinal measurement at all. Nothing
was substituted because no automatic exercise can be justified from a
shoulder-to-hip offset alone.

A previous rename of this parameter was reverted at commit 6ac72e4. If it
is to be reverted again, that should be a stated decision rather than a
merge artefact.

### PT-L05 is signed, PT-L01 reports head position instead
The trunk lean function returned an unsigned vertex angle, so a backward
lean produced the same number as a forward one under a row labelled Forward
Trunk Lean. Now signed, positive forward and negative backward, with the
label following the sign. Facing direction comes from the nose against the
shoulder rather than the ear, because the ear is itself one of the points
whose anterior position the tool measures elsewhere, and forward head
posture moves it.

PT-L05 moved to mirrored bands with the same boundaries as before, since
the old one-sided rule would have graded any backward lean as NONE.

The craniovertebral angle was deliberately left unsigned. A negative CVA is
not a clinical quantity. What the magnitude alone could not say is whether
the ear sits anterior or posterior to the shoulder, and only the anterior
case is forward head posture, so that is now reported separately as a head
position on the PT-L01 row. No grade changes.

### PT-A01 normal ceiling moved above the measurement noise floor
FOR REVIEW. The normal ceiling was 2 degrees against a reported 2D frontal
angle error of roughly 1.5 to 2 degrees for this method, so a perfectly
level head could grade MILD on noise alone. Moved to 3 degrees, with
mild_max from 5 to 7 to keep a similar band width. This is a noise-floor
correction, not a clinical reference range.

### Borderline flag now sees PT-A08's hidden cliff, PT-L01 margin widened
`is_borderline` only scanned the THRESHOLDS table, so PT-A08's hardcoded
-1.5 degree cliff in `posture.py`, the most noise-sensitive decision point
in the tool, was never flagged. Boundaries that live outside THRESHOLDS are
now listed explicitly. This moves no grade and does not fix the cliff
itself, which still needs founder bands.

The flat 2.0 degree borderline margin also did not fit PT-L01: a validated
smartphone CVA application reports a minimum detectable change of 4.96
degrees within-rater and 5.52 between-rater, wider than PT-L01's own 5
degree bands. PT-L01 now uses 5.52. No other parameter has a reported MDC,
so no other override was added.

### The Global Stability Index now states how many parameters it used
The index has been computable from a different number of parameters for
every patient, so two patients with identical severe findings could receive
very different scores. The report now prints "Based on N of M parameters"
under the score. The weighting itself is untouched and remains unsourced;
that is still an open question for the founders.

### Every report carries an analysis version
Grades move when thresholds, sign conventions or calibration change, and
several moved today. Reports now carry `analysisVersion`, with a PDF footer
line saying values are only comparable with reports of the same version.
Reports made before today carry none, and that absence is the signal that
they predate this work.

Chosen over a database column and migration: `PostureSession` has no
version field, adding one means a schema change against an environment that
cannot currently be reached, and no reports are persisted there yet. The
field is in the payload now and can be stored whenever sessions actually
start being written.

### Test dependencies pinned
`pytest.ini` declared `asyncio_mode` but `pytest-asyncio` was not in
`requirements.txt`, so async tests were not running as async. `httpx` and
`aiosqlite` were also imported by tests and missing, and
`test_clinic_isolation.py` was erroring on collection. All three pinned.
`httpx` is held at 0.27.2 because `ASGITransport` changed in 0.28, and the
installed 0.28.1 was downgraded to match.

Suite went from 26 passed with one collection error and three config
warnings to 27 passed clean.

---

## 1 October 2026

Posture tool, same branch. Taken by Onkar after measuring the calibration
constant on our own photographs. This moves a number every patient sees, so
it is FOR REVIEW, but it corrects an error rather than choosing a band.

### Millimetre calibration constant measured, 0.97 replaced with 0.8134
FOR REVIEW. `estimate_pixels_per_cm` divided the nose-to-ankle pixel span
by 0.97 to estimate full stature, on the assumption that the span is 97
percent of height. It is not. Measured on seven team members photographed
front, side and back, with heights taken by tape to the top of the skull,
the front-view figure is 0.8134, n=6, sd 0.0100, se 0.0041. One front photo
was dropped because the feet touched the frame edge.

The old value inflated every millimetre reading by 19 percent. A reading
that printed 14.31 mm now prints 12.00 mm.

Front view because that is the view the visibility guard actually lets
through. Across the same seven subjects every side view and two of the
seven back views fail the guard on ankle visibility, so in practice
calibration runs on the front photograph.

The back view measured 0.8349, about 2.6 percent higher. Three separate
explanations for that gap were tested against the data and none held up, so
it is recorded rather than corrected. A per-view constant was considered and
rejected: the gap between any defensible candidate here is under 1.5
percent, against the 19 percent error being removed, and splitting the
constant would bake an unexplained difference into the code.

Two things this number is not. Stature was measured from the pose
segmentation mask, whose top edge sits at the top of the hair rather than
the skull, so 0.8134 is likely half a percent low; it is not adjusted,
because that correction would be an estimate and this is a measurement.
And the subjects are seven young adults from one team, not a clinic
population.

Three things were considered and left alone. The landmark choice: nose was
tested against shoulder and hip, and nose is the most stable of the three
across subjects, coefficient of variation 1.2 percent versus 2.1 and 8.3.
The visibility guard, which behaved correctly throughout. And the call
sites, which need no change since the constant stays single.

Effect measured end to end on all seven subjects: 8 of 31 millimetre grades
change, roughly one in four, and every one of them moves down a tier. The
earlier estimate of one in five came from a single sample report and is
superseded by this. Reports generated before today overstated every
millimetre finding, which makes flagging them as superseded more urgent,
not less.

### Knee direction logic reviewed against real photographs, and left alone
The source carried a note asking for `calc_knee_frontal_deviation` to be
checked against real photographs before clinical use. Done, on the same
seven subjects, front view, fourteen legs.

The direction the function returns was compared against the knee's position
relative to the body midline, a quantity the function does not use. The two
agreed on all fourteen legs. The one subject with visibly bow legs came out
varus on both sides. MediaPipe's anatomical left appeared on the image right
in every photograph, which is the same confusion that caused the elbow sign
bug, so it was worth confirming separately.

No code change beyond replacing that note with what the review found. The
direction convention stands.

### PT-P03 and PT-P05 withdrawn from the report
Running the full pipeline on all seven subjects produced two results that
cannot be true of seven healthy young adults. Rearfoot alignment returned
varus on 14 of 14 legs, 12 of them SEVERE, against a published healthy
population mean of 6.07 degrees of valgus. Toe angle asymmetry returned
SEVERE on two subjects with no foot complaint.

Looking at the annotated photographs rather than the numbers showed why.
On the back view the foot index landmark sits almost on top of the ankle:
18 to 133 pixels apart against 304 to 395 on the front view of the same
person, on every leg. The toe is hidden behind the leg from behind, so the
model places it by inference. PT-P05 was grading an angle between two
points, one of which the camera never sees.

PT-P03 failed differently. Its heel landmark is real and lands on the heel
in most photographs. The problem is the method: published mean absolute
error for rearfoot eversion from a phone camera is 8.2 degrees against a
clinically meaningful threshold near 3, because pose models infer eversion
from heel position rather than calcaneal motion. Our whole band range sits
inside that error, which is consistent with getting the opposite of the
population on every subject.

Both are withdrawn rather than deleted. The functions and bands stay in
the source with nothing calling them, so they can return if we ever train
our own landmark model. Their muscle and exercise mappings are removed
with them, since a mapping fires on a grade that will no longer exist.

This is not recorded as a founder question. The toe landmark is not
observed, which is an engineering fact and the same reason the seven
parameters in known_limitations.md are blocked and the same reason PT-L08
was removed in June. The rearfoot case rests on published error figures
and our own measurements, not on a clinical preference. If Daman or
Shivank want either back, the evidence is in known_limitations.md.

### MediaPipe visibility does not detect a misplaced landmark
Not a decision, a finding that changes how much the existing guards are
worth. On one subject's back view every lower-limb landmark collapsed onto
the floor between the feet, hundreds of pixels from any foot, and the
ankle and heel still reported 0.80 and 0.83 against our 0.65 threshold.
The score means the model thinks the point is in frame, not that it is in
the right place.

A geometric check was tried: ankle-to-heel distance over knee-to-ankle
distance, measured on all 42 legs. The collapsed photograph scored 0.068
and two correct photographs scored 0.073 and 0.077. There is no line
between them, so no check was added. Recorded in known_limitations.md so
the next person does not spend the same afternoon on it.

### A leg whose joints are not stacked like a standing leg is now rejected
One subject's side view reported Knee Flexion of 156.77 degrees, graded
NONE. A standing person cannot bend a knee that far, and the grade was
NONE because the bands only cover the hyperextension side, so the report
printed an impossible number and called it normal.

The landmarks were not collapsed and the photograph was fine. The model
had placed that ankle higher in the frame than its own knee, with
visibility 0.84, well above our 0.65 threshold. That makes the
hip-knee-ankle angle about 23 degrees, and 180 minus 23 is the number
that reached the report.

Unlike the ankle-to-heel ratio tried earlier the same day, a check here
does separate good from bad. In image coordinates y increases downward,
so on anyone standing the hip sits above the knee and the knee above the
ankle. Measured across 42 legs, seven subjects, three views each: 41
passed and the one that failed is the one that produced the 156 degrees.
No false positives.

This is gravity, not clinical judgement. There is no threshold in it, no
reference range, and nothing for a clinician to sign off. `check_limb_order`
sits beside `check_visibility` in detector.py and raises a new
`ImplausibleLandmarkError`, wired into PT-L06 on the side view and
PT-A05/PT-A06 on the front. A rejected leg reports as not measured, the
same as a missing landmark, because to the reader both mean the same
thing. Five tests pin it, including one asserting that visibility is not
consulted either way.

Scope is deliberately narrow. It catches this failure, not every
misplaced landmark, and the general problem recorded above stands.

One incidental finding, not acted on. `detector.py` runs MediaPipe at
`model_complexity=1`. At complexity 2 the same photograph returns a
correctly placed ankle. Raising it would cost analysis time on every
request and has not been measured, so it is noted rather than changed.

---

## Not decided, still blocked

These were looked at today and deliberately left alone.

- **PT-A08 elbow carrying angle.** The cliff at -1.5 degrees and the rule
  grading any varus as SEVERE regardless of magnitude both still stand.
  Needs founder bands. Separately, the carrying angle is defined with the
  elbow extended and the forearm supinated, which a standing posture
  photograph cannot reproduce, so retuning the bands would make a
  measurement of the wrong thing look normal.
- **PT-L06 flexion bands.** The label now follows the sign, but any
  non-negative value still grades NONE, so a 40 degree flexion contracture
  reads as normal. Needs clinician-supplied flexion bands.
- **PT-P04 naming.** The docstring was corrected to stop claiming axial
  rotation, which the calculation cannot produce. The function name and the
  report label still say rotation. Whether to rename it, and whether it
  should exist separately from PT-A04 at all given it reduces to the same
  quantity when the shoulders are level, is a founder decision.
- **PT-A05 and PT-A06 knee bands.** The direction logic is now verified,
  see 1 October above. Two things remain, both clinical. The bands are
  asymmetric, normal up to 5 degrees of valgus against 3 of varus, with a
  female allowance on valgus and none on varus. On one of the seven
  subjects this produced a smaller deviation on the right leg carrying a
  worse grade than the larger deviation on the left, 3.15 degrees MILD
  against 3.77 degrees NONE. Separately the neutral gate of 0.5 degrees
  fired on only two of fourteen legs, so a straight leg is almost always
  pushed into valgus or varus on an offset of a few thousandths of a unit,
  and which side it lands on then decides which band grades it. Whether
  valgus and varus should share a ceiling is a clinical question, not an
  engineering one: the asymmetry looks deliberate rather than accidental,
  given the female allowance exists on one and not the other.
- **Severity tiers themselves.** Whether the product should assign
  none/mild/moderate/severe at all, or move to a normal-range presentation,
  is the question that dissolves roughly half of the above. Unanswered
  since 13 September.
