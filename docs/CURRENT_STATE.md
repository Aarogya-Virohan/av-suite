# Posture Tool, current state

Written 2 October 2026, updated 3, 10, 11, 12, 13 and 15 October and
17 November, by reading and running, not from memory.

17 November in one paragraph: the posture tool is in production behind
the AV Suite login (PR #67, release/posture-nov, checked live on 17 Nov
at 01:44 IST). The report now uses the shared clinic letterhead with the
signed-in clinic and an IST date (D-039), and every row carries a Normal
range read from the grading bands, with a basis and sources section on
page 3 (D-040). The branding round (PR #68, feat/posture-branding) is
merged into dev; its production live check is still owed. D-039 and
D-040 live in docs/crm/Decisions.md, not in docs/decisions.md. Sections
4i to 4m below say what changed after 15 October; section 5 is the open
list as of 17 November.

This file replaces posture_tool_FULL_STORY_17Sep2026.md and
posture_tool_handoff_01Oct2026.md as the thing to read first. Both are
now stale in ways that cost real time, described at the bottom. If
something else contradicts this file, this one is newer.

---

## 0. There are two clones of this repo on the laptop. Read this first.

(Written 2 October. Not re-checked on 17 November; the Desktop clone may
be gone. Since November, rounds are also worked in worktrees such as
~/wt-branding, whose upstream can be origin/dev: never plain `git push`
from one, always `git push origin <branch>`.)

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

Branch dev. Do not trust a commit hash written in this file: this file is
itself committed, so any hash it names is one commit behind the moment it
is written. Run `git log --oneline -5` instead.

Branch flow since 10 November (docs/decisions.md): every change goes on a
feature branch, which merges into that round's release branch; dev only
takes a release branch. Commits are authored and committed by OnkarDureja
only, with no tool credit in messages or PR descriptions. Work reaches
Onkar as an mbox, checked by `git am` on a fresh clone of origin/dev with
an identical tree; nothing goes to dev without him.

Posture work on dev since 15 October, in order (git log for the hashes):
bigger photos and chart, three pages (19 Oct); tilt correction instead of
the level lock, then the phone-test fixes (27 Oct); next 16.4.6 for the
CI audit (10 Nov); login, posture.create and the posture-tool product on
the API, sign-in in the app (14 Nov); optional gender (14 Nov); release
posture-nov to production (PR #67, 17 Nov); the branding round (PR #68,
17 Nov).

Tests on 17 November, dev 47bf710, in a Linux VM (Python 3.11,
SQLite, DATABASE_URL unset): full suite 575 passed, 2 skipped, 24 failed.
The 24 failures are CRM tests and the same set as dev f02118a
(appointments_permissions 3, billing_payment_invoice_guards 4,
bucket_rbac 3, exercise_templates 1, invoice_pdf 4, invoice_percentages
2, patients_api 2, permissions 1, review_regressions 3,
treatments_permissions 1). Not investigated; they are not posture tests.
Posture tests (tests/services/posture, tests/test_posture_auth.py,
tests/test_posture_pdf_clinic.py): 200 passed.

---

## 2. The three documents that matter

- docs/decisions.md, decisions actually taken, with the reason.
  Dated sections from 18 September to 14 November. From 17 November the
  posture decisions that touch shared report code are numbered entries
  in docs/crm/Decisions.md (D-039, D-040), because the letterhead and
  brand modules are shared with the prescription and invoice PDFs. The "Not decided,
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

- 13 October, Q4 b (one decimal) and Q5 b (no minus sign beside a
  direction word), relayed by Onkar as a screenshot. Built, section 4f.
  The other questions of the 12 October batch were not answered as of
  15 October (section 5).

- 27 October: the 1.5 degree level lock (10 October guideline) and the
  tripod requirement (11 October answer 4a) are replaced by tilt
  correction on the capture screen, on founders' feedback and Onkar's
  own tests (section 4j).
- 12 and 17 November: Shivank sir's rule for every patient-facing
  document, "the clinic is the hero, Aarogya Virohan is the backend
  partner" (D-034, D-036); the posture report follows it since D-039.
  Founders asked for a range next to every value, like a blood report;
  built as the Normal range column (D-040).

Open from the third reply:
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

## 4e. Done on 11 and 12 October, the report (commits 844dda0, 9774805, 378538d, d4f771c)

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
- Four report components left unused by the rebuild were removed
  (d4f771c). 378538d's message claims that removal but only changed this
  file; d4f771c did the removal and says so.
- analysisVersion not bumped: no value or grade changed, only how they
  are drawn and printed. It is still 2026-10-11.2.
- frontend/posture-tool/.env.local still points NEXT_PUBLIC_API_URL at the
  12 October quick tunnel, which is dead once the tunnel closes. Set it to
  http://localhost:8000 (or a fresh tunnel) and rebuild before running.

Direction for later (Onkar): once joined to the marketplace, the clinic's
own logo and details take the header and Aarogya Virohan stays only in the
footer. Not built: clinic data belongs to the marketplace and CRM work.

## 4f. Done on 13 October, founders' Q4 and Q5

Details and reasons in decisions.md, 13 October.

- Every value prints with one decimal on the PDF and the web report. Rounding
  happens once, in report_builder.display_value; the two surfaces only pad.
- PT-L05 and PT-L06 print the size without a minus sign. They are the only
  rows that ever go negative, and their label already carries the direction.
- No grade moved (classify runs on the unrounded signed value). A value can
  print as 4.0 with a grade decided on 4.04; the borderline flag covers it.
- analysisVersion is now 2026-10-13.1 (it was 2026-10-11.2 when 4e was written).
- Saved report files now hold one-decimal values.

## 4g. Done on 13 October, report letterhead (PDF)

Details in decisions.md, 13 October. Brand direction B on the PDF: clinic
letterhead from report["branding"] with an Aarogya Virohan fallback (what
every report shows today), a patient box with every intake field, cream
page, embedded fonts, footer with patient and report ID on every page.
heightCm now saved in the patient record. The web report and the app
screens follow the same brand since the same night (see decisions.md).

Second pass the same night (Onkar's review): photographs row, title
subline, landmark visibility, "Viewed from" captions and the footer
tagline removed from the PDF; footer is the AV mark plus "POWERED BY
AAROGYA VIROHAN . AV SUITE". Email fixed to aarogyavirohan@gmail.com.

## 4h. Done on 13 October, web app and intake (commits abea49a, 45f2fa8, eade86f)

- App bar: Midnight band, white logo, lime "Posture Tool" chip, three
  steps. Cream pages, logo teal main buttons, Midnight selected states,
  Grove landmark points. Fonts via next/font/local (src/app/fonts).
- Web report mirrors the PDF: letterhead (lib/branding.ts mirrors
  AV_FALLBACK), patient box, title, Grove dot headings, zebra rows, footer
  mark. Watermark tiled over the report body at 3 percent; PDF watermark
  5.5 percent.
- Intake: heading "Patient details & photographs"; red asterisk on name,
  age, height and the three photos; "<field> is required" under each
  missing one after Continue, page scrolls to it; "Still needed" line
  gone; height hint "Must be accurate. Every mm value depends on it."
- Tested by Onkar in the laptop browser on 13 October (reports for himself
  and Ayush Gupta, both two pages, layout correct).

## 4i. Done on 19 October, bigger photographs and chart

Founders asked for larger photographs and a larger signature chart. The
report went from two pages to three: side plane alone on page 1, front
and back on page 2, signature, synthesis and closing on page 3. Details in
decisions.md, 19 October. The sizes changed again on 17 November (4m).

## 4j. Done on 27 October, tilt correction

The capture button no longer waits for 1.5 degrees of level. It needs the
phone steady and within 10 degrees of upright; the side tilt at capture is
sent with the photo and the backend turns the reviewed points back by it
before measuring (services/posture/level.py). Optional one-time
calibration per phone and browser. The report says "levelled by x
degrees" or "tilt not measured". ANALYSIS_VERSION is 2026-10-27.1 and is
still that on 17 November. Phone-test fixes the same day: steadiness
threshold, camera screen closing, calibration guard, case reference
optional, "NA", "N/A", "Nil", "None", "-" treated as empty
(`_PLACEHOLDERS` in api/v1/posture.py), red "points to check". Still
owed from that day: the door-frame sign check on a real Android phone and
on an iPhone (decisions.md, 27 October, "Not yet verified").

## 4k. Done on 10 and 14 November, security and login (U1)

- posture-tool on next 16.4.6 for the CI security audit (10 Nov).
- The posture API moved from /posture (no authentication) to
  /api/v1/posture. Every call needs a valid token, the posture-tool
  product enabled for the workspace and posture.create. Role templates
  are unchanged, so therapists and front desk need "Run Posture
  Analysis" granted (founders' question, see section 5).
- posture-tool signs in with the AV Suite account, with the clinic picker
  for accounts in more than one clinic. A session that ends mid-assessment
  asks for the password and resends, so photos and checked points are
  kept. /analyze serves the same page (the CRM links there).
- Gender is optional on the report route, like case_ref.

## 4l. Done on 17 November, production (PR #67)

release/posture-nov merged into dev and deployed. Live check on
17 November at 01:44 IST passed: sign-in, clinic header, a three-view
run, the three-page PDF. That check is what found the problems D-039
fixes (placeholder clinic name, patient name in the footer, UTC date).
posture-tool has a vercel.json; backend settings such as
JWT_EXPIRE_MINUTES are on Railway.

## 4m. Done on 16 and 17 November, branding round (PR #68)

feat/posture-branding, five commits, merged into dev. Production live
check still owed. Details in docs/crm/Decisions.md, D-039 and D-040,
with two review notes under D-040.

- Shared letterhead (D-039): the PDF uses report_letterhead.py unchanged.
  The clinic is the signed-in clinic, read from the clinics row on every
  export (app/services/posture/clinic_letterhead.py); report["branding"]
  sent by the client is ignored. The web report gets the same clinic as
  text. Footer "Report PT-... . Page x of y", no patient name. Assessed-on
  date and report ID date are IST. The "AV Clinic" placeholder is gone;
  frontend lib/branding.ts keeps AV_FALLBACK only for the AV phone and
  email when there is no clinic. The app bar shows the logo on every step.
- Normal range (D-040): every row shows value, Normal range and grade.
  The range is the band the grade already treats as Normal, read from
  classifier.THRESHOLDS by app/services/posture/reference_ranges.py, so it
  cannot drift from the grading. No band changed. Format: >= 50 deg,
  +- 4 deg, <= 5 deg, <= 10 mm (real symbols on the report; the embedded
  Inter subset lacks them, so they are set in Liberation Sans / Arial).
- PT-L01 is shown as "Head Position (ear-shoulder angle)": calc_cva
  measures ear to shoulder point, not the C7 to tragus CVA. PT-L01 and
  calc_cva keep their names.
- "Normal ranges: basis and sources" on page 3, above the sign-off, one
  line per measure at 8 pt: the published basis where the classifier
  comments name one, otherwise "AV clinical team, Oct 2026". Pelvic
  obliquity also carries Moharrami et al. 2023 (0 to 5.6 deg,
  radiographs, not directly comparable).
- One name per measure (coordinator review of v4): the radar axes and the
  sources lines print the row's own label, same text and case as the
  table, including the knee and trunk names that follow the sign.
  reference_ranges.row_labels() reads them off the report rows; there is
  no second list of names. The region list names regions only.
- Layout: one fixed column grid on all three plane tables; radar chart
  102 mm wide (was 128), SVG 540 x 400, axis names 8.0 pt and ring names
  7.2 pt on paper. Ring names: Normal on the centre, Mild, Moderate and
  Severe in their own bands in the gap between two axes that keeps them
  off every point and the outline. Still three pages; page 3 has little
  room left.

## 5. Open on 17 November

Checked against dev 47bf710 on 17 November unless it says otherwise.

Release
- Production live check of PR #68 (branding round). Owed.

Founders (Shivank sir; one message going out, no action here until he
answers)
- Head Position band. Normal is 50 degrees or more, taken from CVA
  literature, but our ear-shoulder angle read 68 to 78 degrees on five
  subjects (po-1 78.2, po-2 73.2, po-3 68.0, po-4 68.0, po-5 74.4), so
  every patient grades Normal and the row screens nothing.
- Therapist access: whether therapists get posture.create and posture.view
  (own or all) by default. A grant script is ready and has not been run.
- Shoulder Level Asymmetry band (0 to 5 mm) has no recorded basis.
- From the 12 October batch, no answer recorded after 15 October: Q2
  "likely hypertonic / inhibited" columns (still on the report), Q3
  patient name in saved files, Q7 registered company name, Q9 colours
  sign-off, Q10 lawyer on consent and retention, Q11 inter-rater test.
  Settled since: Q6 (tagline removed), Q12 (it runs in production), Q13
  (clinic logo via the signed-in clinic, D-039). Q1 and Q8: see uploads.

Engineering, planned and not built
- Uploads: camera only for clinics, upload behind a new capability
  "posture test upload", default off, granted to Onkar's AV test
  account. Named in D-039 as the next part of the round. Nothing for it
  is on dev yet. Until then the upload path still has no check of any
  kind.
- Security advisories (pip-audit, 12 November), still on dev: Pillow
  10.4.0 (fix 13.0.0), pillow-heif 0.18.0 (fix 1.3.0), protobuf 4.25.9
  (fix 5.29.6 or 6.33.5).
- JWT_EXPIRE_MINUTES on Railway: value to come from Onkar.
- MediaPipe: detector.py is at model_complexity=1. Complexity 2 places
  points better but marks more of them not visible; not re-checked with
  the review step (open_questions_research.md). No mediapipe upgrade
  without an old vs new landmark comparison and Onkar's OK.
- Back-view millimetre calibration without the nose. Deferred on purpose
  (known_limitations.md).
- Page 3 is nearly full; a longer synthesis or more measures could push
  the closing block to a fourth page.

Small, Onkar's call (unchanged since 13 October)
- Intake says "Gender", the report says "Age / Sex".
- Logo teal #4E888F buttons with white text are about 4.1:1, under AA
  4.5:1; #3B6A70 (already the hover colour) would pass.

People, not code
- Lawyer's view on consent and data retention (founders' answer 6a).
- Inter-rater test: two physios placing points on the same photographs.
- Tilt correction on real phones: door-frame sign check on Android and on
  an iPhone (4j).

Housekeeping (Onkar, laptop; not re-checked on 17 November)
- backend/data/reports: older files still hold photographs.
- Downloads/Posture-test/_render: old renders.

Closed since 15 October, for the record: "NA" placeholders (27 Oct),
the clinic letterhead data (D-039), the "AV Clinic" placeholder (D-039),
the moot elbow note in calc_elbow_carrying_angle (no longer in the code),
the dead .env.local tunnel note (production now).

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
- Every real decision goes into docs/decisions.md, or into
  docs/crm/Decisions.md when it changes shared report code (D-039, D-040).
- CRM is out of scope. Do not touch. The posture report uses the shared
  report_letterhead.py and brand.py unchanged (D-039).

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
