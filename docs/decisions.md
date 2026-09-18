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

## Not decided, still blocked

These were looked at today and deliberately left alone.

- **Millimetre calibration constant.** `calculator.py` divides the
  nose-to-ankle span by 0.97 to estimate stature. Standard anthropometry
  puts that span nearer 0.84, which would mean every millimetre value is
  roughly 15 percent too high. The corrected figure is itself an estimate
  from general tables and must be measured on our own photographs before
  the constant is touched. Swapping one guess for another is not a fix.
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
- **PT-A05 and PT-A06 knee bands.** Asymmetric with each other, no female
  band on varus, and the direction logic has never been checked against
  real photographs. Needs photos before anything is changed.
- **Severity tiers themselves.** Whether the product should assign
  none/mild/moderate/severe at all, or move to a normal-range presentation,
  is the question that dissolves roughly half of the above. Unanswered
  since 13 September.
