# Posture Tool, current state

Written 2 October 2026, updated 3 October, by reading and running,
not from memory.

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

dev is pushed and origin is in step as of 3 October.

work/capture-flow-03Oct is the branch the 3 October work was done on and
is merged into dev by fast-forward. fix/posture-gsi-and-labels still
exists at 097595b and is behind dev. Neither needs anything doing.

Test suite: 34 passed, run 3 October in the real clone. Verified here, not
carried over. The two new ones are in test_report_builder.py, which did
not exist before 3 October.

Recent commits, subjects as they actually read:

    1e18ee3  posture: close the PT-L06 facing direction review, use the shared reference
    c9a2d43  posture: record whether each photograph was captured in-app or uploaded
    b6daa1d  capture: write PNG, not JPEG at quality 95
    ac32619  docs: re-measure the 1 October figures, correct three that do not reproduce
    519be8f  docs: the two withdrawals are done, not pending
    a944514  posture: withdraw PT-A08 from the report
    16ae06d  posture: withdraw PT-P04 from the report
    3260edc  docs: current state file, read this one first
    591ecab  docs: millimetre parameters have no sourceable bands, and the unit is why

---

## 2. The three documents that matter

- docs/decisions.md, decisions actually taken, with the reason.
  18 September and 1 October sections, ending with a "Not decided, still
  blocked" list.
- docs/open_questions_research.md, new on 2 October. Four entries:
  PT-A08, PT-P04, PT-A05/A06, and the millimetre parameters. Each records
  the question, what the code does today, and what the evidence says.
  A question goes here before it goes to the founders.
- docs/known_limitations.md, parameters blocked or withdrawn, with the
  anatomical or measurement reason for each.

---

## 3. Blocked on the founders

AV_Posture_Tool_Decisions_Required_02Oct2026.pdf went to Daman and
Shivank on 2 October. It supersedes the 13 September review request and
Section D of the 15 September status document. Six questions, each with
options and a recommendation:

1. Severity tiers or a normal range presentation. Answer first, it
   changes the shape of 3, 4 and 5.
2. CVA bands, 50/45/40 or 50/30, and the ear-to-shoulder substitution.
3. Knee valgus and varus band asymmetry and the female allowance. The
   neutral gate width rides along with this.
4. The millimetre parameters: convert to angles, set ranges from our own
   patients, or leave as is.
5. Global Stability Index: remove, reweight, or keep.
6. Clinician landmark review step, plumb line and grid, height and age
   and gender on the report, and the stronger disclaimer.

Twelve questions became six because the rest were researched, measured,
or had stopped existing. The working is in open_questions_research.md.

Nothing here should be started before its question is answered, and an
answer means the exact option named, not a paraphrase of something said
verbally.

---

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

## 5. Not started

- PDF report content and design pass.
- Report UI pass. The capture half of the frontend was worked on
  3 October, see section 4b; the report half was not.
- One "Should be reviewed against real photographs" note is still live, in
  calc_elbow_carrying_angle around line 568. It is moot, since PT-A08 was
  withdrawn on 2 October. Left in place deliberately. The facing-direction
  note at line 373 was closed on 3 October.
- The upload path has no check of any kind. A clinician can choose any
  file, including a screenshot or a photo of a screen, and it is measured
  as if it were a guided capture. 3 October added wording to the upload
  card and recorded the source in the report, but nothing gates it. A
  capture-time check was scoped and not built: see section 4b.
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

/Users/onkardureja/Downloads/Posture-test/, folders po-1 to po-7, each
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
