# Exercise Library: Decisions and Known Limitations

Decisions and limitations for `frontend/exercise-library` and the prescription backend (exercises, prescriptions, prescription PDF). Kept apart from `docs/crm/Decisions.md` so the two products never clash on numbering or merges. IDs here: `EL-D-NNN` and `EL-L-NN`.

Earlier history in `docs/crm/Decisions.md`: D-021 (Exercise Library redesign and prescription PDF rebuild, 20 Oct 2026) and limitations L-34 to L-38.

---

## [EL-D-001] Founders' feedback, batch 1: head-to-toe library, dropdown filter, paging, stepper, quick picks, editable guidance

- **Date**: 2026-10-24
- **Context**: Founders' feedback of 23 Oct 2026 on the live Exercise Library: order the library head to toe by joints; replace the body part chips with a dropdown because there will be 30+ categories; bring back up/down buttons for sets, reps and hold alongside typing; let therapists tap to choose note phrases that grow over time with what they write; add more red flags. The library is expected to grow to a few thousand exercises.
- **Found while checking the code**: `GET /exercises` had no `ORDER BY`, so offset paging could repeat or skip rows; the app loaded at most 100 exercises and built the body part list from that first page only (L-35); the redesign of 20 Oct had replaced the number inputs with text inputs, which removed the up/down arrows.
- **Decision**:
  - Backend: one head-to-toe list (`app/services/body_regions.py`) orders the exercise list (region, body part, title, id: a total order, so paging is stable) and the new `GET /exercises/body-parts` (every visible body part with its count, empty body part counted as "Other", "Other" last). Filtering by "Other" now also returns exercises without a body part.
  - Backend: new `GET /prescriptions/note-suggestions` returns phrases from this clinic's own exercise notes (split at commas, semicolons, line breaks) and patient guidance (split into sentences), most used first. OWN scope sees only the user's own prescriptions. Nothing is invented (D-008).
  - Frontend: body part dropdown (searchable, multi-select, counts, head-to-toe, picked parts as removable pills, instant filtering); pages of 30 loaded on scroll with a "Load more" fallback; header shows the full total; up/down buttons on sets, reps and hold, typing and arrow keys still work; tap-to-add note chips under each exercise; "Guidance for the patient" is now an editable field (starts with the text every prescription had so far) with its own quick picks, saved in `physio_notes` and printed on the PDF; clearing it leaves the box out of the PDF.
- **Our call, founders can change**: the exact head-to-toe sequence (head, neck, shoulder, arm to hand, upper back, chest, spine, core, lower back, pelvis, hip, glutes, thigh, knee, leg, calf, ankle, foot, full body, then unknown names A to Z, then Other). Red flags: no list is shipped; clinics build their own through the quick picks until the founders give a reviewed list (EL-L-03).
- **API**: additive only. Existing requests and responses unchanged except the list order of `GET /exercises`, which was undefined before.
- **Verified**: backend `pytest` on a fresh Postgres: base dev 64be1e9 309 pass / 10 known environment failures; this branch 314 pass / the same 10 (5 new tests: head-to-toe ranks, phrase ranking, stable paging, body parts with clinic isolation and "Other", suggestions with clinic isolation and OWN scope). Frontend `tsc`, `eslint` and `next build` clean. Playwright on the production build at 1440 and 390 px against a local backend with 55 exercises: 55/55 loaded by scrolling with no duplicates and the same order as the API, dropdown order equal to the API, multi-select and "Other" counts correct, stepper, chips, guidance, save, PDF text, reopen and clear; no page errors and no failed calls.
- **Affected Files**: `backend/app/services/body_regions.py`, `backend/app/repositories/exercise.py`, `backend/app/api/v1/exercises.py`, `backend/app/services/prescription_suggestions.py`, `backend/app/api/v1/prescriptions.py`, `backend/tests/test_exercise_library_ux.py`, `frontend/exercise-library/src/**`

---

## [EL-D-002] Founders' feedback, batch 2: prescription PDF letterhead, co-branding and therapist name

- **Date**: 2026-10-24
- **Context**: Founders' feedback of 23 Oct 2026 on the prescription PDF: change "Physical Therapy & Rehabilitation" to "Exercise Prescription Tool"; our single logo top-left on every report; use the space where "Admin2 User" shows for the clinic's branding, and keep only our branding when the clinic is not onboarded; clinics have no digital signature, so remove the signature section and show the treating therapist; the date belongs at the top.
- **Found while checking the code**: "Admin2 User" is the test account's real name, printed as "Prescribed by". The CRM settings page saves the clinic logo in `clinics.branding_logo_url` as a data URI of any `image/*` file up to 200 KB, and the settings API accepts any string, so the value can also be SVG, a remote URL or not an image at all. On 24 Oct both production clinics had no logo stored. The letterhead band was 100% wide plus 28 mm of padding, so its right edge ran off the page (hidden before because the right column was short).
- **Decision**:
  - New shared letterhead `backend/app/services/report_letterhead.py`: Aarogya Virohan white wordmark top-left on every page with the subtitle "Exercise Prescription Tool"; the clinic name on the right with the clinic logo on a white tile next to it. Other reports can adopt it in their own work; the posture module is not changed.
  - Clinic logo: every value is decoded and re-encoded as a PNG of at most 400 px with Pillow before it reaches the PDF. PNG, JPEG, WebP and GIF data URIs are accepted; an https URL is downloaded with the exercise image rules (public hosts only, 6 s timeout, 8 MB cap). SVG, plain http, relative paths and anything unreadable are dropped, and the clinic name is shown without a logo.
  - No clinic on the prescription: the right side stays empty (Aarogya Virohan only). A clinic without a usable logo still shows its name, because the patient needs to know which clinic prescribed.
  - "Selectable" branding is automatic: the clinic logo shows when one is stored. No per-PDF toggle unless the founders ask for one.
  - Signature and date lines removed. "Treating therapist: <name>" is printed under the safety note (the prescriber). The date stays in the patient box at the top, in IST.
  - Letterhead uses `box-sizing: border-box`, so the right side sits inside the page margin.
- **API and data**: no change. No migration.
- **Verified**: backend `pytest` on a fresh Postgres: base `release/el-oct` 010bd96 314 pass / 10 known environment failures; this branch 325 pass / the same 10 (11 new tests: wording present and absent, AV-only, logo used, four raster formats re-encoded, twelve bad values dropped, remote URL through the fetcher, private host and size cap blocked, and a PDF generated through the API with a logo stored on the clinic in the DB). A mutation that allowed plain http logos made a test fail. Real PDFs rasterised and every page checked: 2-page prescription with a WebP logo and a long clinic name, AV-only, and an SVG logo falling back to the name.
- **Not verified**: live rendering on Railway (checked after the round reaches dev). Exercise images show "Image not available" locally because the container cannot reach Blogger.
- **Affected Files**: `backend/app/services/report_letterhead.py`, `backend/app/services/prescription_pdf.py`, `backend/app/services/prescription_service.py`, `backend/tests/test_prescription_pdf.py`

---

## Known Limitations

| # | Item | Status | Owner |
|---|---|---|---|
| EL-L-01 | Body part names are free text. Synonyms show as separate entries next to each other (e.g. "Thoracic" and "Upper Back"), and some exercises sit in the wrong part (e.g. a neck isometric under "Other"). The 30+ categories the founders plan need a fixed list and a data clean-up before the bulk import of new exercises | Open; waits for the founders' category list (body regions or exercise types) | Us + founders |
| EL-L-02 | L-35 (CRM file), exercise part fixed here: exercises page through the whole library. The patient picker still loads at most 100 patients | Open | Frontend |
| EL-L-03 | Red flags: no reviewed list exists. Quick picks only reuse what the clinic already wrote | Open; founders to give or approve a list | Founders |
| EL-L-04 | Quick picks read the clinic's last 1000 exercise notes and last 1000 prescriptions; older phrases drop out | Accepted | - |
| EL-L-05 | Exercise images and videos share `video_url` (some rows hold relative video names such as `hamstring.mp4`, so no picture shows) | Open; separate image and video fields, with the personalised exercise photos | Backend |
| EL-L-06 | The CRM settings page accepts any `image/*` logo and the settings API does not check the value. SVG logos never print on the prescription (name only) | Open; limit the CRM upload to PNG/JPEG/WebP, in the CRM round | CRM |
| EL-L-07 | The PDF names the prescribing therapist. "Head of clinic" needs clinic profile fields that do not exist yet (CRM L-14) | Open; founders to choose, fields come with the CRM clinic profile work | Founders + backend |

*Last updated: 2026-10-24 (EL-D-002, EL-L-06, EL-L-07) | Branch: feat/el-pdf*
