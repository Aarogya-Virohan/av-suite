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
worth. On po-7's side view the model placed the right ankle above its own
knee and the leg still passed the 0.65 visibility threshold, producing a
156 degree knee flexion. The score means the model thinks the point is in
frame, not that it is in the right place.

A geometric check was tried: ankle-to-heel distance over knee-to-ankle
distance, measured on all 42 legs. No threshold separates a misplaced
landmark from a correct one, so no check was added. Recorded in
known_limitations.md so the next person does not spend the same afternoon
on it.

Corrected 3 October 2026. This entry originally said that on one subject's
back view every lower-limb landmark collapsed onto the floor between the
feet with ankle and heel visibility of 0.80 and 0.83, and that the
geometric check scored 0.068 against 0.073 and 0.077 on two correct
photographs. Neither reproduces. po-1's back view, the photograph meant,
returns correctly placed landmarks with heel visibility 0.68 and 0.66, and
the annotated image confirms it; the file predates this entry by ninety
minutes and the detection path has not changed since. On the geometric
check the lowest ratio in the set is 0.031 on a correct detection and the
next values are 0.070 and 0.071, also correct, which is why no line can be
drawn. Both conclusions above are unchanged. Only the evidence under them
was wrong, and the real evidence for the first one is po-7's side view.

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

### PT-L05 kept, with its limits recorded
The open question from the last session was whether every subject reading
backward meant the parameter was broken. It does not.

Two things were measured. First, stability: the same photograph re-encoded
at three scales moved the angle by 0.43 degrees mean, 0.72 worst, against
reported values of 0.9 to 3.5. Second, whether the backward reading is one
constant offset that could be corrected away: it is not, the offset as a
fraction of each subject's trunk length ran 0.0158 to 0.0610 across six
subjects.

So the parameter measures something real and repeatable, and the absolute
value carries a systematic shift that cannot be subtracted out. It stays on
the report; the limit is written into known_limitations.md.

A verdict was reached earlier in this session that PT-L05 should be
withdrawn like PT-P03 and PT-P05. That was wrong and is recorded here so
it is not repeated. It compared the left-right shoulder gap against the
lean offset and called the gap measurement error, without ever measuring
the error. When the error was actually measured it was small. The two
withdrawn parameters had a landmark that is not observed and a published
error larger than the whole band range; neither applies here.

po-7 is excluded from the six. Its side-view detection is visibly wrong in
the annotated photograph, the same subject whose ankle landed above its own
knee and triggered check_limb_order.

### analysisVersion moved to 2026-10-01
Mechanical. The stamp exists so reports from different versions are not
compared. The calibration constant changed today and two parameters left
the report today, so the old 2026-09-18 stamp would have let a pre-change
report sit beside a post-change one as if they matched.

---

## 2 October 2026

Posture tool, branch `dev`. Taken by Onkar while going back through every
open founder question to work out which ones did not need a founder.

### PT-P04 withdrawn from the report
It measures no quantity of its own. The function takes the shoulder line
angle and subtracts the hip line angle. With the shoulder line forced
level it returns exactly PT-A04, verified to within 0.01 degrees on all
seven test subjects. When the shoulders are not level, the difference is
shoulder tilt written onto a row about the pelvis: on one subject the hip
line was 1.89 degrees, the shoulder line 3.30, and the parameter reported
5.19, which its own bands grade MILD on a pelvis that is fine.

The two also contradicted each other, because their bands were never
harmonised. A hip value of 4.2 degrees grades MILD as PT-A04 and NONE as
PT-P04, and PT-P04 is one tier softer across the whole range. That is the
same defect C4 fixed for the front and back trunk shift parameters, which
nobody had checked for the pelvis.

Not recorded as a founder question, on the same basis as PT-P03 and
PT-P05. The quantity it reduces to is already on the report from the
front view, so nothing is lost by removing it, and the name claimed axial
rotation, which no single 2D photograph can produce.

Withdrawn, not deleted. The calculation and its bands stay in the source
with nothing calling them. The muscle and exercise mapping is removed.
Verified after the change: route imports clean, no live call to the
calculation or its classifier entry, mapping table down to 13 parameters
with PT-P03, PT-P04 and PT-P05 all absent, suite 32 passed.

One consequence worth naming. The posterior view now has two rows,
PT-P01 and PT-P02, and PT-P02 is the same calculation as PT-A02 on the
front view. Whether a back photograph still earns its place is a product
question rather than a measurement one, and it is flagged in the
2 October decisions document rather than decided here.

### PT-A08 withdrawn from the report
The carrying angle is defined with the elbow fully extended and the
forearm fully supinated. Every source checked says so, including all
three Indian normative studies we cite, and anatomy texts add that the
angle is masked by pronation of the extended forearm. A standing posture
photograph has the arms hanging with the forearm neutral or pronated, so
the tool was not measuring the quantity its reference values describe.

The reason this is a withdrawal rather than a recalibration is that no
correction factor exists to apply. No peer-reviewed study measures the
surface carrying angle across forearm positions in the same subjects,
and the sources that touch the question disagree about direction: 3D CT
shows the ulna rotating into valgus with pronation while the anatomy
texts describe the visible angle shrinking. The 5 to 10 degree reduction
that circulates online traces to a yoga anatomy page with no study
behind it. Retuning bands against an unmeasured shift of unknown sign
would make a measurement of the wrong thing look respectable.

The error budget settles it independently. A goniometer in the correct
position carries a maximal error of plus or minus 6.5 degrees, the one
photograph-based validation reports 4.8 degrees mean absolute error, and
general pose-estimation joint angle error runs 7 to 9 degrees, against a
normal band 5 to 10 degrees wide.

It is also not a postural parameter. The carrying angle is a fixed
feature of bone alignment, used after supracondylar and lateral condyle
fractures, in throwing athletes, and in anthropometric sex estimation.
It does not change with postural correction or exercise, so there is
nothing for a physiotherapy report to track.

Not recorded as a founder question, on the same basis as PT-P03, PT-P05
and PT-P04. The 2 October decisions document states plainly that it is
being removed, with the reasoning, so it can be reversed on request.

Two live defects went with it, both of which had been sitting in the
still-blocked list waiting for founder bands. A hardcoded rule in
posture.py graded any negative carrying angle as SEVERE regardless of
magnitude, so a 2 degree and a 20 degree varus read the same. And a
discontinuity at exactly minus 1.5 degrees moved a patient from NONE to
SEVERE on a change of 0.02 degrees, far inside the model's own error.
Both sat outside THRESHOLDS, so no threshold review would have reached
them. The TODO(clinical) comment that marked them is gone with the code.

`_EXTRA_BOUNDARIES` in classifier.py is now empty. It is kept rather
than deleted, with a comment saying why: it exists for severity rules
written outside THRESHOLDS, whose boundaries the borderline scan cannot
otherwise see, and that situation can recur.

The synthesizer test that asserted PT-A08's muscle mapping fires was
rewritten rather than deleted. It now asserts that none of the four
withdrawn parameters maps anything, which also closes a gap from
1 October, when PT-P03 and PT-P05 were withdrawn with no test pinning
it. The guard was checked against a live parameter to make sure it is
not vacuous.

Verified after the change: route imports clean, no live call to the
calculation, no classify call, no TODO, mapping table down to 12
parameters with all four withdrawn ones absent, PT-A08 bands still
present in THRESHOLDS and unused, suite 32 passed.

---

## 3 October 2026

### The 1 October figures were re-measured, and three of them were wrong
Not a decision. A correction, and a note on how it happened.

While working out what a capture-time photograph check could catch, the
documented failure it was meant to catch was re-run: po-1's back view,
recorded on 1 October as having every lower-limb landmark collapsed onto
the floor. It does not. The landmarks sit correctly, the annotated image
confirms it, the photograph's mtime is ninety minutes before the commit
that described it, and the detection path has not changed since. The event
did not happen.

That prompted re-measuring the rest of the 1 October work against the same
seven subjects. Results:

- PT-P05 ankle-to-toe ranges, recorded as 18 to 133 on the back and 304 to
  395 on the front: actual 26.5 to 272.1 and 96.8 to 364.6. The ranges
  overlap because the set spans three resolutions. The within-subject
  finding holds on all 14 legs and the withdrawal stands.
- PT-P03 varus counts, recorded as 14 of 14 legs and 12 SEVERE: actual 13
  of 14 and 10. The withdrawal stands on the published 8.2 degree error and
  on 13 legs reading opposite to the population mean.
- The geometric check figures 0.068, 0.073 and 0.077: do not reproduce. The
  real lowest value is 0.031 on a correct detection. The conclusion, that
  the quantity cannot separate good from bad, is unchanged.
- Knee direction review: holds. Confirmed against knee separation over
  ankle separation, a quantity the function does not use. The bow-legged
  subject grades varus on both sides and MediaPipe's anatomical left sits
  on the image right in 7 of 7 photographs.
- Neutral gate: 3 of 14 on the pipeline path, which matches what the
  2 October re-measurement already records here. No correction needed.
- PT-L05 trunk lean, recorded as 0.9 to 3.5 degrees on six subjects, all
  backward: exact match.
- The calibration constant 0.8134 could not be verified. Reproducing it
  needs the pixel position of the crown of the head and the floor, and no
  landmark gives either. It is neither confirmed nor contradicted here, and
  the method used on 1 October was not recorded.

No withdrawal, threshold or decision changes as a result. Every conclusion
from 1 October survived. What failed were the counts written underneath
them, and one piece of evidence that described something that never
occurred.

The cause is worth recording, because it also caught this session out five
times in a row. A measurement computed alongside the pipeline is not the
pipeline's measurement. Passing raw landmarks to a function that posture.py
feeds from to_geometric_space roughly doubles a trunk lean and halves a
knee deviation; using to_geometric_space output for a pixel distance
returns tenths of a pixel; recovering a constant from the function that
divides by it returns the constant. Each of those produced a confident
wrong number in this session before being caught. The rule that follows:
import and call what posture.py calls, the way it calls it.

Documents corrected: known_limitations.md, three places; this file, the
1 October visibility entry. Correction notes left in place rather than
rewriting history, so the next reader can see what changed.

### In-app capture now writes PNG instead of JPEG at quality 95
The camera component encoded every capture through
`canvas.toBlob(..., "image/jpeg", 0.95)`. JPEG is lossy at every quality
setting, and the loss is big enough to move a grade.

Measured on the seven front views, re-encoding the original once and
running both through the pipeline:

    variant   changed   mean shift   worst   MB/photo   MB/assessment
    q95       4 of 14       0.396    1.187       1.42            4.26
    q100      3 of 14       0.406    1.197       2.71            8.14
    png       0 of 14       0.000    0.000       8.74           26.21

One leg moved from 0.356 to 1.358 degrees and flipped neutral to varus,
which reproduces the observation already in the working rules. Quality 100
buys almost nothing for double the size, so there is no middle option: the
choice is lossless or accept the shift.

PNG, at roughly six times the upload. The cost is real on a clinic
connection and is accepted, because capturing in-app instead of taking a
forwarded photo is only worth doing if we control what reaches the model.

Three of the four changed legs flipped across the 0.5 degree neutral gate,
which is further evidence that the gate sits inside the measurement noise.
That is already recorded under the knee bands and is a founder question.
Nothing was changed about it here.

### The report now records whether each photograph was captured or uploaded
Every view carries a `captureSource` of `camera`, `upload` or `unknown`.

The capture screen applies a protocol: tripod at about half patient height,
a fixed distance held across visits, framing lines for head and feet, a
tilt check, and now lossless encoding. The file input next to it applies
none of that, and once the file reaches the server the two are
indistinguishable. A measurement from an unguided photograph is not
comparable with a guided one of the same patient, and until now nothing
recorded which had happened.

The default is `unknown`, not `camera`. A client that does not send the
field has not told us the photograph was guided, and assuming it was would
overstate provenance on exactly the reports where it is least safe.

Scope kept deliberately narrow. This records the fact; it does not print
it. Putting it on the patient-facing report is presentation and belongs
with founder question 6, so nothing was added to the PDF.

Two tests pin it, including one asserting the default is not `camera`,
because the whole value of the field is lost if a future change makes the
unguided path claim to be guided. report_builder.py had no test file at
all before this.

The upload card also now carries the capture protocol in text, so a
clinician choosing an existing photo can at least see what the measurement
assumes. Wording only, no gate on the upload.

### PT-L06 facing direction reviewed, and moved onto the shared reference
The source carried a note asking for `calc_knee_hyperextension`'s sign
convention to be checked against real photographs before clinical use.
Done, on the seven side views.

The review found the function deciding which way the subject faces from
its own inline `ear.x - shoulder.x`, while PT-L01 and PT-L05 both call
`facing_direction()`, which uses the nose. That function's docstring
already gives the reason to prefer the nose: in forward head posture the
ear translates anteriorly, so an ear-based reference is weakest in exactly
the case these lateral parameters exist to measure.

On our seven subjects the two references agree on the sign for all seven,
including po-4, who faces the other way, so this is not a behaviour change
on our data. Verified: PT-L06 returns identical values before and after.
What the numbers do show is margin. The ear offset ran 0.024 to 0.044
while the nose offset ran 0.073 to 0.092, so the ear-based test sits about
twice as close to flipping on every subject.

`calc_knee_hyperextension` now calls `facing_direction()`. One definition
of facing, and the more robust one.

Three tests in test_calculator.py were asserting against the ear reference
with the nose left blank, so they failed on the change. They were rewritten
onto the nose, not reverted. Flipping a reference back to clear a red suite
is how the elbow sign bug would have returned, and the same reasoning
applies here. Suite 34 passed.

The second such note, on `calc_elbow_carrying_angle` around line 568, is
moot since PT-A08 was withdrawn on 2 October. Left in place, not reviewed.

---

## 10 October 2026

### Founder answers to the 2 October decisions document
Source: "AI Posture Analysis Clinical Guidelines", a conversation the
founders held with Gemini and sent to Onkar on 10 October as their answers.
For each question the founders asked for a "final sequential summary" and
accepted it as their final word, so those summaries are what is recorded
here. Where a summary cites evidence, the evidence was checked separately
on 10 October and some of it does not hold (end of this entry). The
decisions are clinical and stand as given; only the stated reasons are
weaker than they read.

**Q1, severity.** Keep Mild, Moderate, Severe. Show it as a four-colour
scale on the dashboard and the patient PDF: green normal, yellow mild,
orange moderate, red severe. Apply the label to the deviation, not to the
patient: "Severe Biomechanical Deviation", never "Severe Posture".

**Q2, forward head (PT-L01).** Normal above 50, mild 45 to 50, moderate 35
to 44, severe below 35, degrees. A standalone day-one metric, not only for
change over time. The answer defines CVA from C7 and does not address that
the tool measures ear to shoulder; the bands are applied to the substituted
angle and the classifier comment says so.

**Q3, knee.** Answered as the Q-angle with a sex toggle, male 8 to 14
degrees, female 12 to 17. Not implementable. The Q-angle needs the ASIS,
the patella centre and the tibial tuberosity, and MediaPipe returns none of
them; PT-A05 and PT-A06 measure hip-knee-ankle deviation, which is a
different quantity, correlated with the Q-angle but not interchangeable.
Current bands left unchanged. What the answer does settle is that a
sex-specific allowance is wanted. The limits for the quantity we measure
are still owed.

**Q4, shoulder height.** Millimetres, not degrees. 0 to 5 normal, 6 to 10
mild, 11 to 20 moderate, above 20 severe. Given for shoulder height only.
The trunk shift parameters, PT-A03 and PT-P01, received no bands and stay
at 5/15/25 FOR REVIEW.

**Q5, Global Stability Index.** Remove the single score. The answer was
revised once in the same conversation; the final version replaces the
score with a "Biomechanical Signature", a visual profile of regional
values, and stores each scan as a vector of its measurements. A separate
"Wellness Index" is allowed only outside the clinical report.

**Q6, review step and disclaimer.** Landmark verification is mandatory:
draggable points, and no report until the clinician taps "Confirm
Alignment". Disclaimer, verbatim: "This structural screening report is
generated via automated 2D optical tracking. It highlights static
biomechanical asymmetries to predict localized tissue loading. It is not a
standalone clinical diagnosis and must be correlated with patient symptoms
and functional movement by a licensed physiotherapist."

**Q7, one metric, one view.** Never two numbers for one metric. Posterior
only: shoulder height asymmetry, scapular deviation, lateral spinal shift.
Anterior only: knee valgus and varus. Lateral only: CVA. For our
parameters this means PT-A02 and PT-A03 leave the front view and PT-P02 and
PT-P01 stay. Our 2 October recommendation was the front view, because
calibration was measured on front photographs and back photographs fail
the visibility guard more often; the founders chose the back.

**Head tilt (PT-A01).** The view mapping assigns cranial lateral tilt to
the pupillary line on the front view.

**Withdrawals.** No objection was raised to PT-A08 or PT-P04. Both stand.

**Not answered, so not decided.** PT-L06 flexion bands; the PT-P01 rename
and Schroth removal; the PT-A01 noise-floor ceiling; trunk shift bands;
the calibration constant. Silence is not taken as agreement.

**Evidence in the summaries, checked 10 October.** Supported: healthy
adolescents average 7.5 mm shoulder height difference, 72 percent under 10
mm (Akel et al. 2007, Eur Spine J, doi 10.1007/s00586-007-0546-0), and
Kuklo graded radiographic shoulder height in 1 cm steps. Not supported: no
source was found for the 35 degree CVA boundary; Yip et al. 2008 measured
disability with the Northwick Park questionnaire, not the NDI, and found a
moderate correlation; Horton and Hall 1989, cited for the female Q-angle,
found hip width unrelated to it; a 2023 systematic review found the
Q-angle a poor predictor of knee pathology. The regulatory statements
(CDSCO guidance "finalized in 2026", data hosting outside India as a DPDP
violation) do not match the public record and need a regulatory or legal
opinion, not an engineering one.

### PT-L01 bands moved to the founders' values
moderate_min 40 to 35. Readings from 35 to under 40 degrees, previously
SEVERE, now grade MODERATE. Exactly 50.0 still grades normal (the
classifier uses >=); the founders' wording leaves that single point open.
Verified by calling classify() at every boundary. No test pinned the old
value. Suite 34 passed.

### PT-A02 and PT-P02 bands confirmed, no change
The founders' bands are the existing ones, and the classifier's <=
boundaries put 5.0 normal, 10.0 mild, 20.0 moderate, as the answer reads.
Only the "No published source" comments were replaced. Verified at every
boundary.

### Shoulder level and trunk shift now come only from the back view
The founders' Q7 answer, applied. PT-A02 and PT-A03 no longer run on the
front view; PT-P02 and PT-P01 report the same quantities, by the same
calculations, from the back. Calculations and bands stay in the source with
nothing calling them, as with the earlier withdrawals. PT-A10, the other
front millimetre row, is unchanged.

PT-P02 renamed from "Scapular Height Asymmetry" to "Shoulder Level
Asymmetry". It measures the shoulder landmarks; no scapular landmark
exists, and the founders' view table lists shoulder height and scapular
deviation as different things. The number does not change.

Mappings followed the quantity, FOR REVIEW. PT-P02 now carries what PT-A02
carried (upper trapezius, middle trapezius, scapular retraction) in place of
its old serratus anterior and wall slides mapping, which was written for
scapular winging, a finding a 2D photograph cannot detect and the row no
longer claims. PT-P01 now carries what PT-A03 carried (quadratus lumborum,
obliques, gluteus medius, side plank) in place of a mapping written when it
was "Scoliosis Screen". Nothing new was written: each mapping already
existed for exactly this quantity. Without this, trunk shift would have
shipped with no exercise at all.

The PT-P02 side is now read from image position. MediaPipe's labels came out
reversed on po-1's back photograph; with the camera behind the patient, the
image-left shoulder is the patient's left, the same reasoning PT-P01 and
PT-P03 already use. On the seven subjects this changes po-1 only. A test
pins that reversed labels give the same answer, and the old label-based
function fails it.

Also found, not fixed: on six of seven subjects the front and back photos
name opposite shoulders as higher. Recorded in known_limitations.md with
what would address it.

Verified: route imports, full route run on two subjects shows no PT-A02 or
PT-A03 rows and the renamed PT-P02, suite 37 passed. Run in a Linux VM
(opencv 4.11, not the pinned 4.10), so no measured values are quoted here.

### Severity labels name the deviation, not the patient
The founders' Q1 answer, applied. The report now prints NORMAL, MILD
DEVIATION, MODERATE DEVIATION and SEVERE DEVIATION in place of NONE, MILD,
MODERATE and SEVERE. One change in SEVERITY_LABELS, which feeds both the
PDF and the frontend. Grades themselves are unchanged. The founders' own
example was "Severe Biomechanical Deviation"; their colour scale reads
"Mild Deviation", which is what fits a report badge, so that is used.

The four-colour scale they asked for already existed on both surfaces:
green, yellow, orange, red. Nothing changed there.

The longer label wrapped onto two lines in the PDF, so the value column went
from 24 to 16 percent of the table. Checked on a rendered PDF of one test
subject, both pages. Suite 38 passed.

### Global Stability Index removed from the report
The founders' Q5 answer, first half. The score is no longer computed by the
route, no longer in the report payload, and no longer printed on the PDF or
the frontend. Removed from the payload and not only hidden, because a
number still in the payload is one template edit away from a screen, and
the founders said it does not belong on the clinical side. The
GlobalIndex.tsx component is deleted; calculate_global_index stays in
scoring.py with its tests and nothing calling it, the same way withdrawn
parameters keep their calculations. Reports saved before today still carry
globalIndex in their JSON; nothing reads it.

Not built yet: the founders' replacement, a regional profile ("Biomechanical
Signature"). It needs a decision on which parameter belongs to which region,
and the thoracic region they named has no parameter, because no spinal
landmark exists. Held for the report design pass.

Verified: tsc --noEmit clean, rendered PDF page 2 checked, a test pins that
the payload carries no globalIndex, suite 39 passed.

### PT-A01 measures the pupillary line, from Face Mesh iris centres
The founders' view mapping assigns head lateral tilt to the pupillary line
against the horizontal, front view. Until today PT-A01 measured the nose to
mid-shoulder line against the vertical, which is a sideways head shift, not
a tilt: on po-5 the old method read 6.66 degrees and the eye line 1.70.

The obvious build, Pose's own eye landmarks, was measured and rejected. On
po-3, a visibly near-level head, it read 8.00 degrees, because the pose
"right eye" sat on the lower eyelid while the other sat on the pupil.
About 20 pixels of error over a 160 pixel eye separation is 7 degrees.

MediaPipe Face Mesh with iris refinement, run on a crop around the head
that Pose finds, put both iris centres on the pupils on all seven subjects,
checked on annotated crops including the 1200x1600 low-resolution one. po-3
reads 4.17 there, and the photograph agrees that the image-left pupil sits
lower. Same mediapipe package, no new dependency. If no face is found the
row reports insufficient data and the rest of the assessment continues.

Side is read from image position: facing the camera the image-left eye is
the patient's right, and the head tilts toward the lower eye. Neither
model's side labels are used.

Bands left at 3/7/10, FOR REVIEW. They were set as a noise-floor fix for the
old quantity, and no published normal range for a photographic pupillary
line angle was found. Through the full route on the seven subjects: 0.6 to
4.21 degrees, two MILD, five normal.

Two things recorded, not acted on. Six of seven subjects read the image-left
eye lower, while their shoulders read image-left higher; opposite
directions, so not one camera roll, and not explained. And the same check
showed Pose's ear landmarks on the cheeks, not the ears, on po-3. PT-A10,
Ear Level Asymmetry, is built on those points and is on the report today.
It also measures the same head roll as PT-A01, in millimetres. What to do
with it is open.

Verified: annotated crops inspected, route run on all seven, suite 40
passed (one new test for angle and side).

### New disclaimer, on the PDF and the frontend report
The founders' Q6 wording, verbatim, replaces the earlier disclaimer on the
PDF, and is added to the frontend report, which had none; the founders
asked for it on both the dashboard and the patient PDF. The two copies are
checked identical by script. One thing worth their eye: the wording says
the report highlights asymmetries "to predict localized tissue loading".
The tool measures landmark positions and angles; it does not estimate or
validate any tissue load. Kept verbatim because it is their wording.

The landmark review step from the same answer is not built yet.

Verified: rendered PDF page 2 checked, still two pages, tsc clean, suite 40
passed.

### analysisVersion moved to 2026-10-10
Mechanical, same reason as on 1 October. Today's changes move grades and
replace what two rows measure, so a report from today must not sit beside
one from before as if comparable. The bump also covers the 3 October PNG
capture and captureSource, which changed what reaches the model and were
not stamped at the time; the founder prep file of 7 October flagged that
as undecided.

### Landmark review step built; no report without it
The founders' Q6, second half. The clinician now checks the points before any
report exists, and the old one-shot POST /analyze is removed, so there is no
path to a report without review. The flow is POST /detect, the review screen,
then POST /report.

Which points are reviewed was not chosen by reading the code. Every landmark
index the measurement code reads was traced at runtime across all seven
subjects: 11 points on the front (plus the two pupils), 7 on the back, and on
the side the facing side's ear, shoulder, hip, knee and ankle plus the nose.
The far side of a side photograph is hidden behind the body and is not
offered; it keeps the model's values and only scales the grid. A test pins
the list, so a measurement that starts reading a new point fails until that
point is added to review.

Design decisions, each for a stated reason:
- The full photographs are uploaded once, to /detect. /report takes only
  the points, a signed token and a small display copy of each photograph,
  because measurement needs only the points and the original image size.
  Nothing is held on the server between the two calls, so "patient photos
  are not saved" still holds, and it works across server restarts and
  instances, which an in-memory hold would not.
- The token carries the model's own points, signed with the app's JWT
  secret, two hour lifetime. The audit in the report (model position,
  confirmed position, pixels moved, who confirmed, when) cannot have its
  model half altered by the client. Round trip is exact; tampering is
  refused.
- The review screen shows the server's decoded copy of each photograph, not
  the browser's, so the orientation shown is the one measured and HEIC
  uploads, which Chrome cannot display, still work.
- A confirmed point passes the visibility guard: a clinician placing it is a
  stronger check than the model's score, which po-7 showed does not catch a
  misplaced point. A point marked not visible reports insufficient data. The
  limb-order gravity check still runs on confirmed points.
- The landmark visibility figure on the report stays the model's own.
- The server refuses a report that is unconfirmed, has any point unreviewed,
  has a point outside the photograph, an invalid token, or a display image
  whose shape does not match the analysed photograph.

Verified: the route was first split into detection and measurement with no
change, reports byte-identical on all seven subjects including annotated
images. Confirming unchanged points through /report reproduces every row,
image and visibility figure on all seven. Five rejection cases return 422.
Levelling po-3's pupils takes PT-A01 to 0.0. The saved report carries the
audit. Suite 48 passed, tsc clean. The review screen has not yet been tried
on a phone; that is the next check.

---

## Not decided, still blocked

These were looked at today and deliberately left alone.

- **PT-A08 elbow carrying angle.** Settled on 2 October by withdrawing
  the parameter, which was the second half of what this entry said: a
  standing photograph cannot reproduce the position the measurement is
  defined in, so no band would have fixed it. The cliff at -1.5 degrees
  and the varus-is-always-SEVERE rule went with the code, so neither
  needs founder bands any more. See the 2 October section above.
- **PT-L06 flexion bands.** The label now follows the sign, but any
  non-negative value still grades NONE, so a 40 degree flexion contracture
  reads as normal. Needs clinician-supplied flexion bands.
  Settled 11 October, founders' second reply: flexion grades on
  5/10/15. See the 11 October section.
- **PT-P04 naming.** Settled on 2 October, and not by renaming it. The
  parameter was withdrawn from the report, because it reduces to PT-A04
  exactly when the shoulders are level and contaminates the pelvic row
  with shoulder tilt when they are not. See the 2 October section above.
- **PT-A05 and PT-A06 knee bands.** The direction logic is now verified,
  see 1 October above. Two things remain, both clinical. The bands are
  asymmetric, normal up to 5 degrees of valgus against 3 of varus, with a
  female allowance on valgus and none on varus. On one of the seven
  subjects this produced a smaller deviation on the right leg carrying a
  worse grade than the larger deviation on the left, 3.15 degrees MILD
  against 3.77 degrees NONE. Separately the neutral gate of 0.5 degrees
  fired on three of fourteen legs when re-measured on 2 October, and our
  own scale-only noise on that measurement averages 0.84 degrees, so the
  gate sits inside the measurement error and a straight leg is pushed
  to one side or the other by noise, and which side it lands on then
  decides which band grades it. Whether valgus and varus should share a
  ceiling is a clinical question, not an engineering one: the asymmetry
  looks deliberate rather than accidental, given the female allowance
  exists on one and not the other.
  Settled 11 October, founders' first reply: 5/9/13 for both directions,
  no female allowance. See the 11 October section.
- **Severity tiers themselves.** Answered 10 October: keep
  mild/moderate/severe, with a four-colour scale. See the 10 October
  section.

## 11 October 2026

### Founder answers on the knee row and ear level
Source: the founders' reply of 11 October to three questions sent that
morning, given as "1a, 2a, 3a" with a Gemini write-up and three tables.
The decisions are theirs and are applied as given. As on 10 October, some
of the stated reasoning is stronger than the evidence: the write-up says
the 5 degree ceiling "perfectly absorbs" human and machine variance and
"ensures the software only flags true pathological deviations", and that
the eyes "guarantee" reliable detection. Bellemans et al. 2012 measured
radiographs, not photographs, and gives a prevalence (32 percent of
healthy young men, 17 percent of women at 3 degrees of varus or more),
not a cut-off; the 2 degree error figure is from a pose model on knee
osteoarthritis patients (Saiki et al. 2023). The 5 degree line is a
reasonable judgement on that evidence, not a validated threshold.

**1a, knee bands.** PT-A05 and PT-A06 now share one set: 0 to 5 normal,
over 5 to 9 mild, over 9 to 13 moderate, above 13 severe. The founders'
table writes the boundaries as 5.1, 9.1 and 13; the classifier's <=
gives exactly that (5.0 normal, 5.1 mild, 9.0 mild, 13.0 moderate).
PT-A06 moves from 3/7/12. PT-A05 loses its female normal ceiling of 7:
the table has no sex split, so a woman at 6 degrees of knock-knee now
grades MILD where she graded NORMAL. Verified at every boundary in
test_knee_alignment.py.

This also settles the two open knee items from the list above. The bands
are no longer asymmetric, so a smaller deviation can no longer outgrade a
larger one on the other leg. The 0.5 degree neutral gate still sits
inside the measurement noise, but it no longer matters for the grade,
since both directions share one band set, and the direction word is only
printed above NORMAL, at 5.1 degrees and up, far outside the 0.84 degree
noise that could flip it.

**2a, name.** The row is "Left Knee Alignment (Hip-Knee-Ankle)" and
"Right Knee Alignment (Hip-Knee-Ankle)", never "Knee Valgus" or "Knee
Varus". The direction prints underneath as "Knock-knee" or "Bow-leg",
through SIDE_WORDING, so like every other direction it is hidden at
NORMAL. The parameter ids PT-A05 and PT-A06 stay, because the synthesis
maps them to different muscles.

**3a, ear level.** PT-A10 is withdrawn from the report, from the
synthesis and from the front landmark review (the two ear points). The
calculation and bands stay in the source with nothing calling them. The
front calibration and the nose stay: the annotated front image still
draws its reference grid from them. Evidence from the live phone tests:
on 10 October the model put both ear points on the cheeks and the report
said 16 mm, severe; on 11 October, with the ears placed by hand on the
same patient, two runs gave 11.05 mm SEVERE and 8 mm MODERATE while the
pupillary head tilt on the same photograph read 0.94 degrees NORMAL.

ANALYSIS_VERSION to 2026-10-11. Verified: posture suite 65 passed (47
before, 18 new); full detect, confirm, report and PDF route on all seven
test subjects, no PT-A10 row, no "Valgus" or "Varus" label, front review
offers nine points; PDF page one checked visually, the new label fits on
one line with the direction beneath. Run on the Mac's Linux VM, Python
3.10, so no measured values are quoted here as reference figures.

Same session, frontend only: the landmark review screen was redesigned
after the first phone test (one view at a time, tap a point for its
controls, zoom, skeleton lines, a confirm summary). The submission sent
to the server did not change.

### Founders' second reply, 11 October: five more bands
Five bands were running without an approved number. None appeared in the
founders' guidelines document of 10 October (checked: head tilt, trunk
shift and knee hyperextension appear only as view assignments; pelvic
obliquity and trunk lean not at all). Asked once, with research and a
suggestion each; answered "1a, 2a, 3a, 4a, 5a". As before, the write-up
that came with the answer claims more than the sources do (for example
that leg length difference up to 10 mm is present in "up to 70%" of
people, and that a resting flexed knee is "a primary diagnostic
indicator" of osteoarthritis); neither was checked and neither changes
the numbers.

- PT-A01 head tilt: 5 / 8 / 12 (was 3 / 7 / 10).
- PT-A04 pelvic obliquity: 3 / 6 / 10 (was 3 / 5 / 10).
- PT-P01 trunk shift, back view: 10 / 20 / 30 mm (was 5 / 15 / 25).
  PT-A03, withdrawn from the front, moved with it so the two cannot drift.
- PT-L05 trunk lean: within 4 / 7 / 10 either way (was 3 / 6 / 10).
- PT-L06 knee, side view: hyperextension unchanged at 5 / 10 / 15, and a
  bent knee now grades on the same tiers. It used to grade NONE at any
  size. The classifier rule changed from lower_worse to centred.

Sources behind the suggestions: Ferreira et al. 2011 (J Manipulative
Physiol Ther, photogrammetry of 115 healthy young adults: head horizontal
alignment 1.5 +/- 2.4, ASIS 0.2 +/- 1.6, trunk vertical 182.4 +/- 2.1
degrees); Moharrami et al. 2023 (J Exp Orthop, pelvic obliquity on
standing radiographs, 95th percentile 5.6 degrees); coronal balance on
spine radiographs, C7 plumb line within 20 mm of the sacral midline
(Radiopaedia); genu recurvatum defined as more than 5 degrees, more than
15 pathological (as cited in Dierick et al. 2020). All of these use
hand-placed markers or radiographs, not a pose model.

Synthesis kept to the direction each mapping was written for. The PT-L06
mapping (gastrocnemius and soleus tight, terminal knee extension control)
is for hyperextension, and the PT-L05 mapping (hip flexors tight, hip
flexor stretch) is for a forward lean. A bent knee and a backward lean now
grade in their rows but are not passed to the synthesis, so the report
cannot prescribe the opposite correction. This was already wrong for a
backward lean before today; it never fired only because no backward lean
had reached MODERATE. Flexed-knee and backward-lean mappings are a founder
question.

ANALYSIS_VERSION 2026-10-11.2. Verified: posture suite 101 passed (65
before; the PT-L06 test extended to flexion, and every new boundary pinned
in test_founder_bands_11oct.py); full route and PDF on all seven test
subjects. Effects seen there: po-4 and po-6 knees now grade MILD flexion
(8.38 and 5.55 degrees) with no synthesis entry; po-6 and po-7 pelvic
obliquity at 5.25 degrees moves from MODERATE to MILD; head tilt 4.17 and
4.21 on po-3 and po-7 moves from MILD to NORMAL; trunk shift stays MODERATE
on po-3, po-6 and po-7 (22 to 27 mm). Also seen, not acted on: the trunk
lean reads backward on all seven subjects (-0.9 to -6.72 degrees), which
is worth checking against the sign convention before anyone reads it
clinically.

### Saved report files no longer overwrite each other
Every report is written to backend/data/reports, and since 10 October that
copy carries the landmark review audit (model point, confirmed point,
pixels moved). Nothing in the code reads these files back. The file was
named "<case_ref>.json" since 0f32c5a (1 June), which had two faults: two
reports with the same case reference overwrote each other silently (all of
the 10 and 11 October phone tests used "Na", so only the last survives),
and the case reference went into the path unchecked, so a value with "../"
could write outside the folder. Now report_filename() keeps only letters,
digits, "-" and "_" from the case reference, caps it at 60 characters, and
appends a UTC timestamp and a random suffix. The report itself is
unchanged. Verified: five new tests, including the "../" case; full route
on the seven test subjects writes one uniquely named file each.

Open, for the founders, not engineering: these files hold the patient's
name and photographs on the server's disk with no retention period and no
consent step. The audits in them are also the only ground truth we have
for where clinicians actually place landmarks, which would be the data for
any future landmark model.

### The view summary restates the rows instead of judging them
The line under each view listed MODERATE and SEVERE rows, and otherwise
said "Posture appears within acceptable limits." That sentence was ours,
not the founders', and it was wrong twice: it printed beside rows graded
MILD DEVIATION, which the founders define as a deviation (10 October,
answer 1), and beside rows that could not be measured at all. Not asked of
the founders, because it adds no clinical judgement; it only reads back
their grades. summarise_view() now writes, in order: "Moderate or severe
deviation in: ...", or "No moderate or severe deviation." when there is
only mild; "Mild deviation in: ..."; "All measured parameters graded
normal." when nothing deviates; and "Not measured: ..." for rows with
insufficient data. Grades and values are unchanged, so ANALYSIS_VERSION is
not bumped. Verified: five tests, the seven test subjects' summaries
checked against their rows, and the longest case (po-7 side view: mild
plus a row not measured) rendered in the PDF on one line.

### The PDF names how each photograph was taken
The report has carried captureSource ("camera", "upload" or "unknown") on
each view since 3 October, but the PDF never printed it, so a reader could
not tell a guided capture from an uploaded photo, which the upload screen
itself warns is not checked against the capture protocol. The PDF now adds
a line under "Landmark visibility": "Guided camera capture" or "Uploaded
photo, capture protocol not checked". "unknown" and reports saved before
3 October print nothing. The web report is unchanged. Verified: three tests;
a PDF rendered with one view of each kind, still two pages.

### Biomechanical Signature, founders' Q5
The founders removed the global score on 10 October and asked for regional
indices, shown as a visual profile, with each scan kept as a vector of its
measurements. Built 11 October, with one limit set deliberately: no new
number. How a regional index should be calculated was never given, and a
formula of our own would repeat the global score's fault at a smaller
scale. So each parameter keeps the grade its approved bands gave it, and a
region shows the worst of its grades.

Regions, head to toe: Head & Neck (CVA, head tilt), Shoulders (shoulder
level), Thoracic (no parameter; kyphosis needs spinal landmarks the model
does not return), Trunk (trunk shift, trunk lean), Pelvis (pelvic
obliquity), Knees (both knee alignment rows, knee from the side).

The report payload gains "signature": every graded row with its region,
view, severity, tier (0 normal to 3 severe, null when not measured), value
and unit. It goes into the saved report file too, which makes it the
vector the founders asked for. The radar drawing is made on the server
(signature_svg.py): one axis per measurement, each point on the ring of
its grade, normal innermost, and an unmeasured parameter gets a grey label
and no point, so it cannot be read as sitting on any ring. The web report
shows the server's SVG; the PDF redraws from the data and never uses an
SVG sent back by the client.

Grades and values unchanged, ANALYSIS_VERSION unchanged. Verified: seven
tests; on the seven test subjects every one of the nine rows lands in the
signature and each region's worst grade matches its rows; PDFs of all
seven subjects stay at two pages. A constructed worst case, every row
severe with the largest possible synthesis, runs to three pages: the
whole synthesis block moves to page three intact. Without the signature
that case fits two. Accepted rather than shrinking the report for a case
that has not occurred.

Two questions for the founders, collected with the others: is "worst grade
in the region" the regional index they meant, or do they want a formula;
and should the thoracic region show as "No parameter" or be left out.

### Capture locked until the phone is level, pitch and roll within 1.5 degrees
The founders' guidelines (10 October) say three times that the capture
button stays disabled until the device reads pitch and roll within 1.5
degrees of vertical. The capture screen did something weaker: it read
pitch only (deviceorientation beta), never roll, and only warned, at 3 and
10 degrees. Roll is the tilt that matters most for this report, since a
sideways-turned phone tilts the horizon and makes one shoulder or one hip
look higher; the known front-back shoulder disagreement
(known_limitations.md) is consistent with it, though not proven to come
from it. A code comment also said the tilt was recorded with the capture;
it was not, and the comment is gone.

Now: pitch and roll are computed from the gravity vector of devicemotion
(beta and gamma suffer gimbal lock at upright, which is the only position
that matters here), smoothed, and the Capture button is disabled until both
are within 1.5 degrees. Only magnitudes are shown, because iOS and Android
report gravity with opposite signs and an arrow would point the wrong way
on one of them. A device that cannot report tilt, or where motion access is
refused, cannot capture; the upload path stays open and an upload is
already marked on the PDF as not checked against the protocol. The motion
listener is now removed when the camera closes; the old one never was.

Verified: type check; the angle function checked on constructed gravity
vectors for both sign conventions, 1 and 2 degrees of roll, 1.4 and 3 of
pitch, landscape and flat. Not yet verified on a phone; whether 1.5 degrees
can be held by hand without a tripod is the thing that test will show.

### Intake screen redesigned; empty age no longer fails after the review
The report endpoint takes age as an integer form field. Checked on the
project's FastAPI 0.115 on 11 October: an empty age returns 422, while an
empty name, gender or case reference is accepted as an empty string. The
intake screen let the clinician continue with age blank, so the refusal
came only after the whole landmark review, and going back to fix the form
discarded the review. It is a likely cause of the unexplained 422 seen in
the phone test that morning, not a proven one.

The intake screen now has labelled fields; name, age (whole number 1 to
120) and height (50 to 250 cm) are required, gender, case reference and
clinician optional, since no band uses gender since 11 October and an
empty case reference is handled by the report file name. The continue
button stays disabled and says what is still needed. The three photograph
slots show the photo with a "Captured" or "Uploaded, not checked" badge;
the long upload warning moved behind "What makes a good photo?". The
separate preview column is gone. No request, field name or value sent to
the backend changed.

### Capture screen redesigned; the level check starts by itself
After the phone test of 11 October. The "Enable level check" button is
gone: Android needs no motion permission, and iOS grants it only inside a
tap, so the request is now made from the "Use camera" tap that opens the
camera, and the check starts on its own when the camera opens. Both share
one pending request, because a second call outside a tap while the iOS
prompt is open would be refused and wrongly report the level as denied. If
access is refused, the screen offers one "Allow motion access" button.

The screen itself: picture full height with the top bar over it (Cancel,
view name, Guides on or off, setup help), tilt shown as two pills that turn
green inside 1.5 degrees, and a round shutter that lights only when level.
On phones the photo slots on the intake screen are now compact rows instead
of full-width cards, and a failed detection shows on the screen in plain
words ("No person was found in the front photo...") instead of a browser
alert. Verified by type check and lint only; the iOS permission path has
not been run on an iPhone.

### Founders' third reply: exercises out, photographs no longer saved
Answers 1b, 2a, 3a, 4a, 5a, 6a, received 11 October.

1b. The exercise column is removed from the report entirely, web and PDF.
Their reason: a 2D deviation does not tell you the cause, so prescribing
from it moves the tool from flagging into diagnosing; the physio
prescribes. synthesizer.py no longer holds or returns any exercise, and a
test pins that the report prescribes none. The "likely hypertonic" and
"likely inhibited" columns stay, because the answer named only the
exercise column. This also closes the two open items about exercise
mappings for a flexed knee and a backward lean. Whether the muscle
columns themselves are approved was not asked separately; read as kept.

2a. The regional profile keeps "worst grade in the region". No change.

3a. Thoracic stays on the signature as "No parameter", so nobody reads it
as checked and normal. No change.

4a. A tripod is part of the clinic setup. The capture setup sheet now says
so. The proposed auto-capture is not needed and was not built. The 1.5
degree lock stays.

5a. No stickers for now. The review step stays the safeguard, and the
inter-rater test (two physios, same photographs) comes first.

6a. Saved report files no longer contain the photographs: photoUrl is
stripped from every view before the file is written. The points, angles,
grades and the landmark review audit are kept. For po-7 the saved file
went from about 1.8 MB to about 21 KB. The patient name is still saved, since
the answer named photos only; whether it should go is open. Files saved
before this change still hold photographs and are not touched by the
code. A lawyer's view on consent and retention period is owed, per the
same answer.

### PDF branding, first pass (founders' voice note and references)
The founders sent two lab reports as references (Healthians and another)
and a voice note: logo at top left, the logo as a watermark, and a
"powered by" line at the bottom. They called this a basic adoption; the
colour scheme of the report is still to be discussed with them.

Done in pdf_service.py only, layout and content unchanged:
- Aarogya Virohan logo top left on every page, document title and the
  patient's name and date top right, so a loose page still says whose it is.
- The logo mark (house and hands) centred behind every page at 4.5 percent.
  WeasyPrint has no background opacity, so the fade is baked into the PNG.
- Footer, wording as Onkar gave it: "(c) POWERED BY AAROGYA VIROHAN .
  AV SUITE . (A CLINICAL EXERCISE PRESCRIPTION TOOL)", then the page count.
  "Excercise" in his message corrected to "Exercise". Flagged to him: this
  report prescribes no exercise (1b), so the tagline reads as describing AV
  Suite as a whole; to confirm with the founders.
- Brand colours taken from the logo (charcoal #2f3336, teal #4e888f).
  Held in constants because the scheme is not decided. Severity colours
  not touched; they are the four colour scale confirmed on 10 October.
- Gender, already collected at intake, now prints beside age.
- Logo files in app/services/posture/brand/, embedded as data URIs so the
  PDF does not depend on a base URL.

po-6 still renders on 2 pages. Suite 123 passed on the Mac.

Direction for later, from Onkar: once the tool is connected to the
marketplace, the clinic's own logo and details go in the header, and
Aarogya Virohan appears only as the "powered by" co-brand in the footer.
Not built now: clinic data, upload and storage belong to the marketplace
and CRM work, and their shape is not decided. Open: whose logo is the
watermark then, and which clinic details print.

Also: two comments in api/v1/posture.py (PT-L05, PT-L06) said the founders
had asked for backward-lean and flexion mappings and mentioned exercises.
Corrected: no such mapping exists, and 1b closed the question.

### Report design, first round (PDF and web)
Onkar asked for a premium, clinical feel. Design only; no value, grade,
threshold or wording from the founders changed.

Annotated photograph (annotator.py): the MediaPipe default drawing (neon
green skeleton, red dots, all 33 landmarks including hands, feet and face)
replaced with the review screen's language: white lines on a dark halo,
teal points with a white ring, and only the points the clinician reviewed
(review.review_indices), joined as the review screen joins them. Unreviewed
model guesses no longer sit on the page beside confirmed points. The side
view draws only the side facing the camera (lateral_side is now passed in).
Level lines are dashed and teal; JPEG quality 92 so thin lines survive.
Drawing only: nothing measured reads this file.

PDF (pdf_service.py):
- Photograph 78 mm tall at its own proportions; the old fixed box
  letterboxed a portrait photo down to about 25 mm wide.
- Capture source is a chip beside the title, amber for an upload, instead
  of grey small print.
- Empty intake fields are left out of the patient band.
- Dates as "11 Oct 2026" (ISO read as a database value; 11/10 is ambiguous).
- Printed Report ID, "PT-<date>-<suffix>"; the same suffix ends the saved
  file's name, so paper can be traced to the file. Added in posture.py.
- Summary under the table, no second teal bar.
- Separate sign-off block with space to sign, apart from the synthesis.
- Disclaimer in a labelled box, founders' wording unchanged, regular weight.
- Watermark at 2.5 percent; 4.5 crossed the tables.
- Radar outline teal (signature_svg.py; web and PDF share it).
Still 2 pages for the test subjects rendered.

Web report: rebuilt to the same layout (section titles, photo beside a
table, shared severity badge, same chips, patient band, disclaimer box,
footer). Width capped like a document. App bar hides its logo on the report
step, since the document carries it. Synthesis headings now say "Likely
hypertonic / inhibited" as the PDF always has; the web said plain
"Hypertonic", which states as fact what a photo can only suggest.

Not changed, for the founders: value precision (two decimals today) and a
negative value beside a direction label ("Backward Trunk Lean -3").

Second pass, same day, after Onkar's test report:
- PDF: photo 62 mm so all three planes fit page 1 (78 mm left 50 mm empty
  on page 1 and pushed the back view over). Values right aligned; a space
  before "mm" ("12.19 mm"), none before the degree sign. Radar slightly
  larger, more room above the sign-off.
- Web: measurement rows are a real table, so the columns align and the
  "MODERATE DEVIATION" badge no longer spills past the edge; the photo
  column takes the photo's own width (no gap before the table); same unit
  spacing (lib/formatValue.ts); header subtitle is name and date as on the
  PDF; "Download PDF" and "New assessment" sit above the report, styled to
  match, and the PDF button shows it is working.

Third pass, same day, Onkar's feedback:
- Photos are the evidence, so two views per page instead of three: photo
  90 mm tall (62 before). Page 1 side and front, page 2 back, signature,
  synthesis, sign-off and notes. Still two pages for the test report.
  Each view also gets a small caption ("Viewed from the side") and its
  photo details (photograph source, landmark visibility) under the summary.
- Capture source wording for a report that also reaches the patient: the
  amber "Uploaded photo, capture protocol not checked" flag on each view is
  replaced by a plain "Photograph: Uploaded photo" detail, and one calm
  sentence in the notes explains it (UPLOAD_NOTE, only when a view was
  uploaded). The fact is kept, because it decides whether two visits can be
  compared; three amber warnings read to a patient as "this test was done
  wrong". Whether uploads are allowed at all is founder question Q1.
- The "Guided camera capture" Onkar saw on the front view of my preview
  came from my hand-made preview data, not from the code. His own exported
  PDF correctly showed all three views as uploaded.

Fourth pass, after the phone test over the tunnels (report PT-20261011-EDEAA04C):
- Report ID date now comes from the assessment date. It used the UTC date of
  the file, so after 18:30 IST the report read "Assessed 12 Oct" with ID
  "PT-20261011-...". The file name keeps its UTC timestamp.
- Values always print two decimals ("11.90 mm", "-5.70°"). They arrive
  rounded to two places, so a trailing zero vanished and 11.9 sat beside
  2.36. Padding only; the precision itself is still a founder question.
- PDF: the report ID no longer wraps in the patient band.
- Web, phone width: measurements are one row per parameter (name, then
  value and grade), since the three-column table squeezed names to a word a
  line and pushed "MODERATE DEVIATION" past the card. Report ID takes a full
  row; footer segments never split ("AV Suite" stays on one line).
- Radar axis labels 10 instead of 8.5 (about 7 px on a phone before).
- Report actions (Download PDF, New assessment) moved from above the report
  to a bar that stays at the bottom of the screen and settles under the
  report at its end: at the top they asked for a download before the report
  was read, and only at the end a phone user scrolls about ten screens.
- Phone test, guided camera capture on all three views (report
  PT-20261012-11D6E71C): ID date matches the assessed date, views read
  "Guided camera capture", no upload note, PDF two pages.
- Sandeep's report (PT-20261012-5224332B) ran to three pages with the
  disclaimer alone on page 3: page 2 had been fitted to one sample, and an
  extra muscle, a two-line summary and the upload note tipped it over. Now
  the sign-off and notes are one block that moves together, the muscle
  lists run inline with commas, and the signature chart is a little
  shorter. A worst-case sample (three plus two muscles, two-line summary,
  upload note) renders on two pages. A longer report still goes to three,
  but with sign-off and disclaimer together on the last page.

## 13 October 2026

### Founders' answers Q4 and Q5: one decimal, no minus sign beside a direction word
Relayed by Onkar as a screenshot on 13 October, exact selections:
"Q4: b (One decimal)" and "Q5: b (Show the size only, since the label gives
the direction)". The other questions of the batch (uploads, muscle columns,
patient name, footer line, company name, upload note, colours, lawyer,
inter-rater test, hosting, clinic logo) had no answer at the time of this
entry and nothing was built for them.

Q4. Every value on the report prints with one decimal (71.3 degrees,
12.2 mm), web and PDF. The rounding happens once, in
report_builder.display_value, so the two surfaces cannot round a tie
differently (Python rounds half to even, JavaScript toFixed does not). The
PDF and the web only pad to one place. The saved report file now holds the
one-decimal value, where it held two.

Q5. PT-L05 (trunk lean) and PT-L06 (knee) print the size only. Checked on
the 76 saved reports: they are the only two rows that ever come out negative
(PT-L05 74 of 76, PT-L06 34 of 65), and both choose their label from the
sign ("Backward Trunk Lean", "Knee Hyperextension"), so the direction is
still on the row. Every other row keeps its sign, so if one ever goes
negative it will not be hidden.

No grade moved. classify() decides on the unrounded signed value before
display_value runs. The consequence is that a value can print as 4.0 and
carry a grade decided on 4.04, so two reports can read 4.0 with different
grades. The borderline flag (2 degree and 2 mm margin) marks every value
within 0.05 of a boundary, since 0.05 is far inside that margin, so this
case is already shown as provisional. Not changed on purpose: grading on the
rounded value would move grades, which is the founders' call.

ANALYSIS_VERSION moved to 2026-10-13.1, because printed values changed
precision and the report says values are comparable only within a version.

Verified: new tests in test_display_values_13oct.py (ten, covering rounding,
the two rows, other rows keeping their sign, negative zero, a missing value,
the grade on the unrounded value, and the PDF row); the posture test folder
run on its own passes 87 tests with them; tsc 0 errors and eslint 0 errors;
a saved report (PT-20261012-5224332B) rendered with the new code reads
"Backward Trunk Lean 3.4°", "Knee Hyperextension 0.1°", "24.3 mm", on two
pages. The full backend suite is run by Onkar on the Mac.

### Report letterhead, brand B, patient box (PDF only so far)
Onkar, 13 October: brand direction B from the brand canvas (Midnight
letterhead on a cream page, CRM "Midnight & Grove" palette, Plus Jakarta Sans
and Inter), for the report and the app. From his talk with the founders: the
clinic's name, logo, doctor's name and degree, phone and so on at the top,
a rounded box with every intake field under it, the Aarogya Virohan
watermark kept, "powered by" on every page. Layout reference: a Healthians
lab report (brand band, then patient details), not copied.

Decided with Onkar the same night:
- The letterhead names the clinic's head doctor; the assessing
  physiotherapist goes in the patient box as "Assessed by".
- Clinic details will come from the marketplace (AV Suite core). Until then
  the report shows Aarogya Virohan's letterhead, with placeholder contact
  he gave (+91 88680 00760, aarogayavirohan@gmail.com) and "AV Clinic" as
  the clinic name. Email corrected by him the same night to
  aarogyavirohan@gmail.com.
- Patient box carries what the intake form already asks, nothing more.
- Clinic logos: ask for a square logo (PNG or SVG, transparent, at least
  512 px, up to 2 MB), a wide one optional, and the clinic name as text.

Built in pdf_service.py:
- report["branding"] (clinicName, logo, addressLine, phone, email, website,
  doctorName, doctorDegree, doctorRegNo) gives the clinic letterhead; absent
  or without clinicName, the Aarogya Virohan fallback. Nothing sends
  branding yet. The logo is accepted only as an inline PNG or JPEG data
  URI, because the PDF endpoint takes the report from the client; anything
  else shows the clinic's initials, so a report can never make the server
  fetch or read a file.
- Patient box: name, age / sex, height, case ref., report ID, assessed on,
  assessed by (or the clinic, in the fallback), how the photographs were
  taken. Empty fields are left out.
- Height is now kept in the report's patient record (heightCm). It was
  already required at intake but not saved.
- Footer on every page: the powered-by line as before, then patient name,
  report ID and page count, since the letterhead no longer names the
  patient.
- Fonts embedded from brand/fonts (OFL, licences beside them), so the PDF
  does not depend on what the server has installed.
- Photographs 80 mm tall (90 before): the patient box and title take
  space on page 1, and at 88 mm the front view fell to page 2 and the
  report ran to three pages.

Verified in Claude's container: 98 posture tests (11 new in
test_pdf_letterhead_13oct.py), and renders of a real report (po-1 photos,
values from PT-20261012-5224332B) with the fallback, with clinic branding,
and a worst case (all uploads, two-line summaries, five plus three muscles,
a refused remote logo): two pages each. The web report and the app screens
are not changed yet.

Second pass, Onkar's review the same night, removed what carries no
clinical value on the PDF:
- "Photographs: 3 views . guided camera" row in the patient box. Each view
  still says how its photograph was taken (founders, 10 October), so the
  fact is not lost.
- The line under the title. The title itself stays: the letterhead names
  the clinic, and without the title nothing on the page says what the
  document is.
- "Landmark visibility" under each view. It is the model's own visibility
  score, not an accuracy, and on a report the patient also gets "98.5%"
  reads as how accurate the test was. It stays in the report data.
- "Viewed from the side / front / behind" captions: the plane titles
  already say it.
- Footer tagline "(A Clinical Exercise Prescription Tool)" removed on
  Onkar's word (it was Q6 of the 12 October batch). Footer is now the
  Aarogya Virohan mark and "POWERED BY AAROGYA VIROHAN . AV SUITE".
Still two pages for all three renders.

Still open: colour scheme sign-off by the founders (Q9).

### Web app and web report on brand B
Same night, Onkar: the app and the web report follow the PDF.
- Fonts: the same Plus Jakarta Sans and Inter files, via next/font/local
  (src/app/fonts), so a build needs no network.
- Cream page, logo teal for the main action buttons, Midnight for selected
  states and dark photo frames, Grove for landmark points and done steps.
  Severity colours untouched.
- App bar: Midnight band, white logo, lime "Posture Tool" chip, and the
  three steps (Patient & photos, Landmark check, Report). On the report
  step the bar shows the name in text, since the report carries the logo.
- Web report: the same letterhead (clinic or Aarogya Virohan fallback,
  lib/branding.ts mirrors AV_FALLBACK), patient box, centred title, Grove
  dot headings, zebra rows, footer with the mark. Landmark visibility and
  the "Viewed from" captions removed here too.
- Known: logo teal with white button text measures about 4.1:1, a little
  under the 4.5:1 AA level for normal text (it passes for large text). Kept
  because Onkar asked for the logo's own teal; darkening it to #3B6A70
  would pass.
Verified in Claude's container: tsc and eslint clean, next build, and
screenshots of the intake screen (desktop and phone) and of the report
(fallback and clinic letterhead, desktop and phone). The landmark review
and camera screens only changed colours and were not screenshotted.
