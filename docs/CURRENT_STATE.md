# Posture Tool, current state

Written 2 October 2026, updated 3, 10, 11 and 12 October, by reading and
running, not from memory.

This file replaces posture_tool_FULL_STORY_17Sep2026.md and
posture_tool_handoff_01Oct2026.md as the thing to read first. Both are
now stale in ways that cost real time, described at the bottom. If
something else contradicts this file, this one is newer.

---

## 0. There are two clones of this repo on the laptop. Read this first.

    /Users/onkardureja/av-suite            <- the real one. Work here.
    /Users/onkardureja/Desktop/av-suite    <- an old clone, was stuck at 17 Sept.

The real one is the path in av_suite_repo_env_reference.md. It has
backend/.env, it has the fix/posture-gsi-and-labels branch, and its
untracked paths are backend/.python-version, backend/data/ and
frontend/crm/.

The Desktop clone has no backend/.env as of 2 October, so the test suite
and the API cannot run there. They fail with pydantic complaining that
JWT_SECRET_KEY is missing. Scripts that import calculator.py or
detector.py directly still work there, which is what makes it easy to
miss.

On 2 October a session's work was done in the Desktop clone before anyone
noticed. Nothing was lost, because the commits were pushed and then
pulled into the real clone, but half that session went on diagnosing a
problem that did not exist. Check pwd against the path above before
starting.

---

## 1. Where the code is

Branch dev. Do not trust a commit hash written in this file, including
in the list below: this file is itself committed, so any hash it names is
one commit behind the moment it is written. That is how the previous
version of this section came to name a HEAD three commits stale. Run
`git log --oneline -5` instead.

dev is pushed and origin is in step as of 11 October (checked with
git status against origin/dev after the last push that day).

work/capture-flow-03Oct is the branch the 3 October work was done on and
is merged into dev by fast-forward. fix/posture-gsi-and-labels still
exists at 097595b and is behind dev. Neither needs anything doing.

Full suite: 123 passed on 11 October after commit 4315196, run on the
Mac in the real clone (posture tests plus tests/test_clinic_isolation.py). In the Mac's
Linux VM that one CRM test errors on SQLite; the Mac run is the one to
trust.

Run `git log --oneline -15` for recent commits. The list that used to
sit here stopped at 2 October and is removed.

---

## 2. The three documents that matter

- docs/decisions.md, decisions actually taken, with the reason.
  Dated sections from 18 September to 11 October. The "Not decided,
  still blocked" list sits between 10 and 11 October and every item on
  it is now settled; each says where.
- docs/open_questions_research.md, new on 2 October. Four entries:
  PT-A08, PT-P04, PT-A05/A06, and the millimetre parameters. Each records
  the question, what the code does today, and what the evidence says.
  A question goes here before it goes to the founders.
- docs/known_limitations.md, parameters blocked or withdrawn, with the
  anatomical or measurement reason for each.

---

## 3. Founder answers

Four rounds, all recorded in decisions.md with which of their evidence
holds up:

- 10 October, the seven questions of the 2 October document. All applied
  except Q3 (answered with the Q-angle, which needs landmarks the model
  does not return) and Q5's regional profile (built 11 October, see section 4d).
- 11 October, first reply: knee bands 5/9/13 for both directions with no
  female allowance, rows renamed "Knee Alignment (Hip-Knee-Ankle)", ear
  level (PT-A10) withdrawn. This settles Q3.
- 11 October, second reply: head tilt 5/8/12, pelvic obliquity 3/6/10,
  trunk shift 10/20/30 mm, trunk lean 4/7/10, and a bent knee now grades
  on 5/10/15 like hyperextension.

Every graded parameter on the report now has founder-approved bands.

- 11 October, third reply (1b, 2a, 3a, 4a, 5a, 6a): exercise column removed
  from the report, regional profile and thoracic "No parameter" kept,
  tripod required (no auto-capture), no stickers for now, saved files no
  longer keep photographs. Details in decisions.md.

Nothing is owed by the founders now. Open from that reply:
- Lawyer's view on consent and how long to keep data (their answer 6a).
- Whether the patient name should also leave saved files (6a named photos only).
- Old files in backend/data/reports from before 11 October still contain
  photographs; delete them by hand if they are not needed.

## 4. Done on 2 October, after the founder document went out

PT-A08 (elbow carrying angle) and PT-P04 (pelvic rotation) are withdrawn
from the report, on the same terms as PT-P03 and PT-P05: calculations
and bands left in the source with nothing calling them, muscle and
exercise mappings removed. Commits 16ae06d and a944514.

Two live patient-facing defects went with PT-A08, the rule grading any
varus elbow as SEVERE regardless of size and the cliff at minus 1.5
degrees. Both had been waiting on founder bands and now need none. The
only TODO in the posture code went with them.

The synthesizer mapping table is down to 12 parameters, and a guard test
now pins that none of the four withdrawn parameters maps anything.

The posterior view is left with two rows, PT-P01 and PT-P02, and PT-P02
is the same calculation as PT-A02 on the front view. Whether a back
photograph still earns its place is raised in the founder document with
no tick box, as a product question.

Nothing else is unblocked. The remaining code work in section 5 either
depends on question 1 or has not been scoped.

## 4b. Done on 3 October

Four commits, all engineering, none touching a clinical decision. Full
reasoning in the 3 October section of decisions.md.

**The 1 October figures were re-measured and three do not reproduce.**
po-1's back view was never collapsed; that evidence was wrong and the
photograph predates the commit describing it. PT-P05's pixel ranges and
PT-P03's varus counts are both off. Every conclusion from that day
survives, including both withdrawals. Only the counts under them were
wrong. The calibration constant 0.8134 could not be verified either way,
because reproducing it needs the crown of the head and the floor and no
landmark gives either. Treat it as unconfirmed, not as wrong.

**Capture now writes PNG, not JPEG at quality 95.** Measured: a single
re-encode at q95 changed direction or severity on 4 of 14 legs, mean shift
0.396 degrees. q100 gave 3 of 14 for double the size. PNG gave 0 of 14.
Cost is upload, about 26 MB for three views against 4.3.

**Every view records captureSource**, camera, upload or unknown, defaulting
to unknown. The capture screen applies a protocol and the file input
beside it applies none, and until now the two were indistinguishable once
the file reached the server. The field is recorded, not printed; putting
it on the report is presentation and belongs with question 6.

**PT-L06's facing-direction note is closed.** It was deciding facing from
its own ear-shoulder offset while PT-L01 and PT-L05 use
facing_direction(), which uses the nose for a documented reason. The two
agreed on all seven subjects, so no behaviour change, but the ear offset
sits about twice as close to flipping. PT-L06 now calls the shared
function.

**What was scoped and deliberately not built: a capture-time photograph
check.** Backend-side, reusing detect_pose_full, so one model and one
truth; in-browser MediaPipe was rejected because it would be a different
measurement from the pipeline's model_complexity=1. Detection costs 0.03
to 0.05 seconds on this laptop, so compute is not the constraint; upload
is. The reason it was not built: of the two known bad photographs, the
existing guards already catch po-7's side view and nothing catches the
other, so the check would ship at half coverage. Whether it should warn or
block is answered by precedent, the tilt check warns.

## 4c. Done on 10 October

Eight commits, see the 10 October section of decisions.md. Suite 40
passed on the real clone. analysisVersion is now 2026-10-10.

Two findings that change how far the report can be trusted, both in
known_limitations.md or decisions.md: front and back photographs name
opposite shoulders as higher on six of seven subjects, and Pose's face
points are too coarse for angles (PT-A01 now uses Face Mesh for that
reason).

## 4d. Done on 11 October

See the 11 October section of decisions.md, and git log for the commits. analysisVersion
is now 2026-10-11.2.

- Both founder replies applied, with every new boundary pinned in tests.
- Landmark review screen redesigned after the first phone test: one view
  at a time, tap a point for its controls, zoom, skeleton lines, a confirm
  summary. The side and back views now say where each point belongs.
- Synthesis only receives the direction each mapping was written for.
- The view summary restates the rows; "within acceptable limits" is gone.
- The PDF names whether each photograph was a guided capture or an upload.
- Q5 Biomechanical Signature built: regional profile on the web report and
  the PDF, a radar drawn on the server, and a per-row vector in the report.
- Capture locked until pitch and roll are both within 1.5 degrees, per the
  founders' guidelines; it previously read pitch only and only warned.
  Phone check still owed: on one Android phone it read 0.6 and 0.6 held by
  hand, which shows it runs, not that it is right. Three physical tests
  settle it: upright against a door frame (both near 0), flat on a table
  (forward tilt near 90), landscape against the frame (side tilt near 90).
  Holding 1.5 degrees by hand is possible but hard; the founders chose a
  tripod as part of the clinic setup, so no auto-capture.
- Intake screen redesigned: labelled fields, name, age and height
  required, compact photo slots with Captured or Uploaded badges, errors
  shown on the screen. Capture screen redesigned: the level check starts
  by itself from the "Use camera" tap, tilt shown as two pills, round
  shutter, setup sheet names the tripod.
- Side and back shoulder and hip points are always marked for checking on
  the review screen, because those are the joint-centre points.
- Founders' third reply applied (commit 4315196): no exercises anywhere in
  the report, saved files keep no photographs. See section 3.
- Saved report files are uniquely named; a "../" in the case reference
  could previously write outside data/reports, and equal case references
  overwrote each other.

The day's most important finding, in known_limitations.md under PT-L05:
the model places joint centres, not bony landmarks, and on one subject
moving a single back-view shoulder point to the bony tip took a MODERATE
trunk shift, and the whole synthesis built on it, to NORMAL. The review
step is what stands between that error and the report.

## 4e. Done on 11 and 12 October, the report (commits 844dda0, 9774805)

Details and reasons in decisions.md, end of the 11 October section.

- Branding from the founders' references: Aarogya Virohan logo top left on
  every PDF page, the logo mark as a 2.5 percent watermark, footer as Onkar
  gave it ("(c) POWERED BY AAROGYA VIROHAN . AV SUITE . (A CLINICAL
  EXERCISE PRESCRIPTION TOOL)"). Colours from the logo, held in constants
  in pdf_service.py, because the founders have not settled a colour scheme.
- Annotated photo redrawn in the review screen's style: white lines, teal
  points, only the reviewed points. No measurement reads annotator.py.
- PDF: two views per page with 90 mm photos; capture source as a plain
  detail and one upload note in the disclaimer box (no amber warnings on a
  report the patient also gets); report ID printed, dated from the
  assessment date; values always two decimals; sign-off and disclaimer one
  block. Two pages for every test report so far, including a worst-case
  sample; a longer one goes to three with sign-off and disclaimer together.
- Web report rebuilt to the same layout; stacked rows on phones; Download
  PDF and New assessment in a sticky bottom bar.
- Phone-tested over tunnels on 12 October with uploads and with guided
  camera capture on all three views.

Direction for later (Onkar): once joined to the marketplace, the clinic's
own logo and details take the header and Aarogya Virohan stays only in the
footer. Not built: clinic data belongs to the marketplace and CRM work.

## 5. Not started

- Back-view millimetre calibration without the nose. Measured 11 October:
  the guessed nose makes back-view millimetres read about 3 percent small,
  at worst 5.7. Deferred on purpose, since point placement errors are
  around thirty times larger (known_limitations.md).
- Founder batch, drafted 11 October, not yet sent as far as this file
  knows: Q1 allow uploads at all (recommend camera only), Q3 keep the
  "likely hypertonic / inhibited" columns (recommend remove), Q4 keep the
  patient name in saved files (recommend case reference only). Also for
  them: value precision (two decimals today) and a negative value beside a
  direction label ("Backward Trunk Lean -3.23"); the footer tagline says
  "exercise prescription" on a report that prescribes none; the exact
  registered company name if a legal line is wanted; the upload note's
  wording, which is ours.
- Report colour scheme (founders said it is still to be discussed) and
  clinic co-branding (after the marketplace).
- Phone checks owed by Onkar: tilt in landscape (side tilt near 90), and a
  real capture on a tripod.
- Lawyer's view on consent and data retention (founders' answer 6a).
- Inter-rater test: two physios placing points on the same photographs.
  Needs people, not code.
- Deployment. The tool runs from the laptop over quick tunnels; no plan
  for hosting it or joining it to AV Suite has been written down.
- One "Should be reviewed against real photographs" note is still live, in
  calc_elbow_carrying_angle around line 568. It is moot, since PT-A08 was
  withdrawn on 2 October. Left in place deliberately. The facing-direction
  note at line 373 was closed on 3 October.
- The upload path has no check of any kind. A clinician can choose any
  file, including a screenshot or a photo of a screen, and it is measured
  as if it were a guided capture. The report names the source on every
  view. On 11 October we concluded that checks cannot catch what matters
  (tilt, distance, camera height), so the real question is whether uploads
  are allowed at all: founder Q1, above.
- detector.py runs MediaPipe at model_complexity=1. Measured on
  2 October: complexity 2 costs 0.11 seconds more per assessment and
  places landmarks better, but it also reports honest visibility on
  occluded points, so 33 landmarks across the seven subjects stop
  passing the 0.65 guard and whole posterior lower bodies go to not
  measured. The model choice is clear; the consequence is tied to
  question 1. Written up in open_questions_research.md, held until
  that is answered.

---

## 6. Test photographs

/Users/onkardureja/Downloads/Posture-test/ (on the Mac; po-6 and po-7
use .jpeg), folders po-1 to po-7, each
with front, side and back, plus subjects.csv. Heights were tape measured
to the top of the skull. po-3 is bow-legged, po-5 wore slippers, and
po-7's side view detection is visibly wrong, with the right ankle placed
above its own knee.

This file previously said po-1's back view has its lower-limb landmarks
collapsed onto the floor. It does not, and never did. Re-measured and the
annotated image inspected on 3 October: the landmarks are correctly
placed. See the 3 October section of decisions.md.

These are the basis for the calibration constant, the knee direction
review, the PT-P03 and PT-P05 withdrawals, and the PT-A05/A06 noise
measurement. They live outside the repo, so they survived the clone
mixup.

---

## 7. Working rules that have earned their place

- Never claim a code behaviour without running it. Never claim a
  document's status without reading it.
- Clinical decisions are Daman and Shivank's. An engineering fact, such
  as a landmark that is not observed or a published error larger than the
  whole band range, is not a founder question. Decide it, record the
  evidence, move on.
- Look at the annotated image. Every real diagnosis in the last two
  sessions came from drawing landmarks on the photo, not from more
  numbers.
- Heredoc scripts to /tmp, then run them. Never long python3 -c strings.
- Never suppress stderr. Two scripts once died silently behind
  2>/dev/null.
- Use detect_pose_full, never a fresh mp.solutions.pose. The pipeline
  runs at model_complexity=1 and a different setting is a different
  measurement.
- JPEG re-encoding alone moves landmark positions enough to change a
  grade. On 2 October, re-saving one photograph at quality 95 with no
  resize moved a knee deviation from 0.356 to 1.358 degrees and flipped
  its direction from neutral to varus. Use PNG for any repeatability
  test.
- Every real decision goes into docs/decisions.md.
- CRM is out of scope. Do not touch.

---

## 8. Why the two older files are retired

posture_tool_FULL_STORY_17Sep2026.md describes the state before the
1 October work. Its open question list runs to twelve items; six of those
are now settled.

posture_tool_handoff_01Oct2026.md names PT-L05 and analysisVersion as the
two places to pick up. Both were finished in commit 097595b, which is one
commit past where that handoff stops. Its branch state is also out of
date, since the merge has happened.

Neither file is deleted, because their account of the Gemini audit
episode is still the only full record of it. Neither should be used to
decide what to do next.
