# Open Questions, Research Findings

Working file. Each question that was previously headed to Daman and Shivank
gets researched here first. Three parts per entry: what the question is,
what the code does today, and what the evidence says.

Nothing in this file is implemented. When every question has an entry, the
implementable ones get done in one pass and move to decisions.md. Anything
that research cannot settle stays here and goes to the founders as a short
list rather than a long one.

---

## PT-A08 Elbow Carrying Angle

Researched 2 October 2026.

### The question

The tool measures a shoulder to elbow to wrist angle from the standing
front photograph and grades it. Two problems were already known. The code
grades any negative value as SEVERE regardless of magnitude, with a cliff
at exactly minus 1.5 degrees, and that rule sits outside THRESHOLDS so no
threshold review reaches it. Separately, the carrying angle is defined with
the elbow fully extended and the forearm fully supinated, which a standing
posture photograph does not reproduce.

This was D2 in the 15 September document and A1 in the 13 September one,
both unanswered. The question asked was whether to remove it, add a
separate capture step, or keep it as tracking only.

### What the code does today

Not re-verified in this session. Per decisions.md and the 15 September
verification, the hardcoded rule at posture.py lines 365 to 380 still
stands, the sign inversion was fixed on 10 September, and the borderline
flag now lists the out-of-table boundaries explicitly but does not fix the
cliff itself.

### What the research found

Definition. Every source checked defines the carrying angle in full elbow
extension and full forearm supination. All three Indian normative studies
we already cite measured it that way and say so explicitly. Anatomy texts
state the angle is masked by pronation of the extended forearm and
disappears in full flexion. A standing photograph with palms toward the
thighs is the pronated working position in which the angle is described as
masked.

The positional bias cannot be corrected away. No peer-reviewed study
measures the surface carrying angle in supination, neutral and pronation
on the same subjects. The figure that circulates, a 5 to 10 degree
reduction in pronation, traces to a yoga anatomy website with no study
behind it. Worse, the direction is unsettled: an in vivo 3D CT study of 12
elbows found the ulna rotates into valgus with pronation, while the
anatomy texts describe the visible angle as reduced. Our wrist landmark
tracks a surface point, not the ulnar shaft, so neither the sign nor the
size of the error is established.

Flexion adds more. Cadaver and in vivo work shows the angle moves toward
varus as the elbow flexes, around 3.9 degrees at 60 degrees of flexion and
8.9 at 120, with no significant change below 30 degrees. Residual flexion
in a relaxed stance is small, but in a 2D frontal photograph an internally
rotated humerus projects any flexion as apparent varus.

Error is the size of the band. A universal goniometer in the correct
position carries a maximal error of plus or minus 6.5 degrees 95 percent
of the time. The only photograph-based validation found, 14 children in
the correct position, reported a mean absolute error of 4.8 degrees
against goniometry. General MediaPipe joint angle error is reported around
7 to 9 degrees, and no pose estimation study validates carrying angle at
all. The normal band that separates varus from valgus is 5 to 10 degrees
wide, so the error budget is as large as the thing being graded.

The thresholds we were going to grade against do not fit our patients. The
5 to 10 male and 10 to 15 female scheme is a textbook convention from
Magee, not a figure derived from data. All three verified Indian studies
put male dominant-side means at 10.2 to 12.6 degrees, at or above the top
of that male band, so it would flag a large share of normal Indian men.
Note also that the Central India radiographic study's standard deviations
of 0.6 to 1.2 degrees are implausibly narrow against every other study's 2
to 5, so that dataset should not be used to set band widths.

It is not a postural parameter. The carrying angle is a bony alignment
trait used after supracondylar and lateral condyle fractures, in planning
corrective osteotomy, in throwing athletes, and in anthropometric sex
estimation. It does not change with postural correction or exercise.
Validated photogrammetric posture protocols do not include it. One of them
positions the elbows at 20 to 30 degrees of flexion for the photograph,
which is the opposite of the carrying angle position.

### Conclusion

This is the same class as PT-P05, an engineering fact rather than a
clinical preference. The capture position does not match the defined
measurement position, the bias has no published magnitude and no agreed
sign, and the total error is as large as the band. Retuning the bands
would make a measurement of the wrong thing look normal.

Proposed: withdraw PT-A08 from the report the same way PT-P03 and PT-P05
were withdrawn, function and bands left in the source with nothing calling
them, muscle and exercise mappings removed. That also retires the minus
1.5 cliff and the varus-is-always-severe rule without needing founder
bands for either.

Not proposed: renaming it and keeping it with bands. A frontal shoulder to
elbow to wrist angle on a posture report will be read as a carrying angle
whatever it is called.

If the parameter is ever wanted, it needs its own capture step with palms
forward and elbows locked, gated by a check that the palm actually faces
the camera, and even then it should report only side-to-side asymmetry
above roughly 6 to 7 degrees or frank varus below 0, with bands taken from
the Indian goniometric studies rather than from Magee.

### Still a founder call

Nothing here, if the withdrawal is accepted on the same basis as PT-P05.
If Daman or Shivank want the parameter kept on the report, then the bands
become theirs to set and the capture step becomes a product decision.

---

## PT-P04 Pelvic Rotation

Checked against the code and against the seven test photographs,
2 October 2026. No literature search was needed. The question is settled
by what the function computes, not by a reference range.

### The question

The 20 August note describes PT-P04 as hip width asymmetry used as a
rotation proxy. The code computes something else. The name claims axial
rotation, which nothing in a single 2D photograph can see. Whether to
rename it, and whether it should exist separately from PT-A04 at all, was
left as a founder decision in the 15 September document, Section B2 item
12, and repeated in decisions.md under "Not decided, still blocked".

### What the code does today

Read at calculator.py:759. The function takes the shoulder line angle and
the hip line angle, subtracts them, takes the absolute value, and folds
the result into 0 to 90 degrees. Both it and PT-A04 run on geometric-space
coordinates, so the aspect ratio fix does apply to them; that was checked
and is not a problem here.

PT-A04 at calculator.py:215 takes the hip line angle from horizontal with
abs on both components, so it is always positive.

Bands differ. PT-A04 is 3 / 5 / 10 degrees. PT-P04 is 5 / 8 / 12.

### What the evidence shows

Three things, all executed on the seven subjects' back photographs using
the pipeline's own functions, not a fresh MediaPipe instance.

One. With the shoulder line forced level, PT-P04 returns exactly PT-A04,
on all seven subjects, to within 0.01 degrees. The duplication is not an
approximation, it is an identity.

Two. Whatever the shoulders are doing enters the pelvic finding degree for
degree. The recomputed shoulder-minus-hip difference matched the
function's output exactly on all seven. po-5 is the clearest case: hip
line at 1.89 degrees, which is normal, shoulder line at 3.30, and PT-P04
reports 5.19, which its own bands grade MILD. The pelvis is fine. The
grade came entirely from the shoulders. This is the same error as the
PT-A01 one, where head tilt and lateral neck shift were mixed into one
number.

Three. The two parameters disagree on the same number, confirmed by
running the real classifier. A hip value of 3.5 or 4.2 degrees grades MILD
as PT-A04 and NONE as PT-P04. At 5.25 it is MODERATE against MILD, at 11
it is SEVERE against MODERATE. PT-P04 is one tier softer across the whole
range. One patient, one session, two contradictory statements about the
pelvis. This is the same defect that C4 fixed for the front and back trunk
shift parameters, which nobody checked for the pelvis.

### Conclusion

PT-P04 measures no quantity of its own. When the shoulders are level it is
PT-A04 exactly, and when they are not, the difference is shoulder tilt
written onto a pelvic row under a name that claims axial rotation.

Proposed: withdraw PT-P04 from the report on the same basis as PT-P05, an
engineering fact rather than a clinical preference. Nothing is lost,
because the pelvic quantity it reduces to is already reported as PT-A04 on
the front view, with tighter bands.

The alternative, keeping it and harmonising the bands with PT-A04, is
worse than it sounds. Harmonised bands would still leave shoulder tilt
contaminating the pelvic row, which is the part that actually misleads a
reader.

### Still a founder call

Not the withdrawal itself. But removing it leaves the posterior view with
two rows, PT-P01 and PT-P02, and PT-P02 is already byte-identical to
PT-A02 on the front view. Whether a back photograph should still be
captured and printed at all is a product question, not a measurement one,
and it should be asked once rather than parameter by parameter.

### Noted, not a defect claim

po-1's back photograph returns a shoulder line angle of 178.58 degrees
where every other subject is near 0, meaning the left and right shoulder
landmarks are reversed on that image. The folding into 0 to 90 hides this,
so the reported number still looks ordinary. po-1 is the same subject
whose lower-limb landmarks collapsed onto the floor on the back view,
already recorded in known_limitations.md, so this is most likely part of
that bad detection rather than a separate fault. Not confirmed, because
the annotated image has not been looked at. Worth doing before anyone
treats it as new.

---

## PT-A05 and PT-A06 Knee Valgus and Varus

Measured on the seven test photographs and checked against published
error figures, 2 October 2026.

### The question

Two things were left open in decisions.md. The neutral gate of 0.5 degrees
fired on very few legs, so a straight leg is nearly always labelled valgus
or varus on a tiny offset, and which way it falls decides which band set
grades it. Separately the bands are asymmetric, valgus normal to 5 degrees
with a 7 degree female allowance, varus normal to only 3 with no female
allowance, and on one subject a smaller deviation on one leg carried a
worse grade than a larger deviation on the other.

The underlying question behind both: is this measurement good enough to
carry severity bands at all, or is it the rearfoot case again.

### What was measured

Front view, seven subjects, fourteen legs, using the pipeline's own
functions.

The neutral gate fires on 3 of 14 legs, not the 2 recorded in
decisions.md. The difference was not chased down. Deviations run 0.19 to
9.55 degrees, with most legs between 1 and 3.

Repeatability was tested by rescaling each photograph losslessly to 85 and
70 percent, which changes nothing about the subject. Scale-only spread is
0.84 degrees mean and 2.21 degrees worst. Two legs moved more than 2
degrees, po-3 right from 2.87 to 0.72 and po-6 left from 3.18 to 0.97.
po-4 right crossed the gate outright, 0.19 at full size and 1.49 at 85
percent, so a leg called neutral becomes valgus or varus on nothing.

A method note that cost one wrong result first. The initial test saved
each scale as JPEG at quality 95, and the re-encode alone moved po-1 left
from 0.356 to 1.358 and flipped its direction from neutral to varus, with
the image dimensions unchanged. That run was discarded and redone in PNG.
Raw bytes and a lossless PNG round trip give byte-equal results on all 14
legs, so the pipeline itself is deterministic and the first run was
measuring JPEG noise.

### What the published evidence says

This is not the rearfoot case. Against full-length weight-bearing
radiographs, pose estimation of the hip-knee-ankle angle reports an
absolute error of about 1.6 to 1.8 degrees and a random error of about
1.6 to 2.2 degrees, with ICC 0.90 to 0.92. One of those studies notes
marker-based 3D motion analysis did worse on the same measurement, random
error 2.4 and fixed error 3.6 degrees, largely because of hip centre
estimation. So the error here is not larger than the band range the way
rearfoot's 8.2 degrees was.

Limb rotation matters less than expected on an extended knee. Reported
change in HKA is around 0.03 to 0.07 degrees per degree of limb rotation.
It becomes a real problem only in combination with knee flexion, where 15
degrees of internal against 15 of external rotation moves HKA by more
than 2 degrees, and up to about 4.8 degrees in already mal-aligned knees.
Our capture is a standing extended stance, which is the favourable case,
though nothing stops a patient standing with rotated feet.

One contrary result worth keeping in view: a markerless study found its
method read about 5 degrees higher than both radiography and optical
motion capture. That is a systematic offset rather than random error, and
it is the kind of thing that would matter if absolute values were ever
read against published norms.

### Conclusion

Withdrawal is not justified. The measurement is defensible by published
standards and the main confounder is weak in a standing extended stance.
This is a different answer from PT-A08 and PT-P04, which is the point of
checking each one rather than assuming.

What is not defensible is the 0.5 degree gate. Our own scale-only noise
averages 0.84 degrees, so the gate sits inside the measurement error and
a straight leg is pushed to one side or the other by noise. The gate
should be widened, but how far depends on the band structure, so it is
not a standalone fix.

Also worth recording: the 2 degree swings on po-3 and po-6 under nothing
but rescaling mean that a single photograph should not be trusted to
separate, say, 3 degrees from 5. That is an argument about band width,
not about the parameter's existence.

### Still a founder call

The asymmetry. Valgus normal to 5 with a female allowance of 7, varus
normal to only 3 with no female allowance. Research can describe the
population distribution but it cannot say why these particular numbers
are in our code, and decisions.md already notes the asymmetry looks
deliberate rather than accidental. Whether valgus and varus should share
a ceiling, and whether a sex allowance belongs on one side only, stays
with Daman and Shivank.

The gate width goes with it, since a sensible gate depends on where the
first band boundary sits.
