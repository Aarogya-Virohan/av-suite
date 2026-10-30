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

## [EL-D-003] Exercise media, batch 3: picture and demo video read apart, no migration yet

- **Date**: 2026-10-24
- **Context**: `exercises.video_url` holds every media link (EL-L-05). The founders want personalised exercise photos from two angles (feedback item 2, question Q2 still open) and the library will grow to a few thousand exercises from the image pipeline.
- **Found while checking**: production data on 24 Oct: 12 global exercises with Blogger picture links (no file extension), 8 clinic exercises with video file links, 1 empty; no relative names such as `hamstring.mp4` remain. The library card put video links into an `<img>`, so the 8 clinic videos never showed anywhere. The prescription PDF downloaded every video link (up to 8 MB or the 6 s timeout) only to fail reading it as a picture. The open CDSS branch adds four migrations chained from `a8c4e2f1d903`, the same head a new migration here would use.
- **Decision**:
  - No migration in this batch. The media model depends on the founders' answer to Q2 (likely a media table with kind and angle, not one more column), so a column now would mean a second migration and a second data move. It also avoids two alembic heads while the CDSS branch is open.
  - New `backend/app/services/exercise_media.py` splits the stored link when it is read: a video is an https link whose path ends in a video extension (.mp4, .mov, .m4v, .webm, .m3u8, .ogv) or that points to YouTube or Vimeo; any other https link is a picture; anything that is not an absolute https link is neither.
  - API: `ExerciseRead` gains read-only `image_url` and `demo_video_url`. `video_url` is unchanged in requests, responses and the database, so existing clients keep working. Values sent for the new fields on create or update are ignored.
  - Prescription PDF fetches only `image_url`; video links are never downloaded.
  - Library card: picture from `image_url`; an exercise with only a video shows a "Watch video" tile that opens the video in a new tab (`noopener noreferrer`). This is a new visible control; the card looked the same as "no image" before.
- **Later, with the founders' answer**: a proper media model (picture, video, clinic photos from two angles, consent where a patient appears) in its own migration, chained after whichever head `dev` has then.
- **Verified**: backend `pytest` on a fresh Postgres: base `release/el-oct` a9c1483 325 pass / 10 known environment failures; this branch 349 pass / the same 10 (24 new: 21 split cases, API fields and unchanged `video_url` and DB value, create ignores the computed fields, PDF asks only for the picture link). Using `video_url` for the PDF again made the PDF test fail. Frontend `tsc`, `eslint`, `next build` clean. Playwright on the production build at 1440 and 390 px against a local backend: picture card uses `image_url`, video card shows the tile with the right link, a relative name shows the no-image icon, the tile opens a new tab; no page errors, no failed calls.
- **Not verified**: live. Whether the 12 Blogger and 8 video links in production all start with https (http links are now shown as neither).
- **Affected Files**: `backend/app/services/exercise_media.py`, `backend/app/schemas/exercise.py`, `backend/app/services/prescription_service.py`, `backend/tests/test_exercise_media.py`, `frontend/exercise-library/src/lib/api.ts`, `frontend/exercise-library/src/components/library/ExerciseCard.tsx`

---

## [EL-D-004] Clinic photos of an exercise, front and side

- **Date**: 2026-10-27
- **Context**: Founders' feedback item 2 (23 Oct 2026): admin or therapist can take a picture of an exercise from two angles to personalise it. Answer to question 2 (27 Oct): option A, the clinic adds its own photos of the exercise and only that clinic sees them. Photos of patients are out of scope.
- **Decision**:
  - New table `exercise_photos` (migration `c1e5f7a9b3d2`): clinic, exercise, angle (`front` or `side`), storage key, size, uploader. One photo per clinic, exercise and angle. Works for global exercises too; the photo belongs to the clinic, not to the exercise.
  - API: `PUT` and `DELETE /exercises/{id}/photos/{angle}` need `exercises.edit` (admins by default; a therapist only when the admin grants it, no role template changed). `GET /exercises/{id}/photos/{angle}` needs `exercises.view` and returns the JPEG for the caller's clinic only (`Cache-Control: private`). The list and detail responses carry `photos` (angle, size, `updated_at`) for the caller's clinic.
  - Every upload is decoded and re-encoded as JPEG with Pillow: EXIF data (GPS, camera, time) is dropped, the long side is capped at 1600 px, only JPG, PNG and WebP of at least 200 px are accepted, 10 MB at most.
  - Files go to the private bucket under `exercise-photos/<clinic>/<exercise>/<angle>-<random>.jpg`. No silent local fallback (Railway's disk is wiped on deploy): when storage is down the upload returns 503. A replaced or removed photo's file is deleted from the bucket (new `delete_file` in the shared `app/core/storage.py`, additive only). `EXERCISE_PHOTOS_LOCAL_DIR` is for local runs and must not be set on Railway.
  - Library: the card shows the clinic's front photo before the library picture, with a "Clinic photo(s)" tag; users with `exercises.edit` get a camera button that opens front and side slots (add, replace, remove; on phones the file picker offers the camera). The dialog says "Use photos of the exercise only. Do not upload photos of patients."
  - PDF: the clinic's photos replace the library picture (two side by side when both angles exist); the library picture is then not downloaded.
- **Migration order**: the open CDSS branch also chains from `a8c4e2f1d903`. Whichever of the two reaches dev second points its first migration's `down_revision` at the other's last revision and is tested again (noted in the migration file).
- **Verified**: backend `pytest` on a fresh Postgres: base `release/el-oct` 934a2b9 349 pass / 10 known environment failures; this branch 361 pass / the same 10 (12 new: EXIF removed and size capped, PNG with transparency, bad, tiny, GIF and oversize files refused, upload, view, list, replace (old file removed), delete, other clinic sees nothing and cannot delete, no photo on another clinic's own exercise, therapist with view only can see but not add, with `exercises.edit` can add, no storage gives 503 and saves nothing, bucket key and delete on replace, PDF uses both photos and skips the library picture). Mutations: dropping the clinic filter and writing EXIF back each made a test fail. Migration: upgrade, downgrade, upgrade on a fresh database; `alembic check` shows no difference for `exercise_photos` (two enum differences on `clinics.type` and `memberships.role` exist on the base too). Frontend `tsc`, `eslint`, `next build` clean. Playwright on the production build at 1440 and 390 px: camera button for the admin, bad file shows the error, front and side upload, remove, Escape closes, card shows the clinic photo after a reload, a therapist with view only sees the photo and no camera button; no page errors. Real PDF rasterised: two photos side by side, one photo, library picture.
- **Not verified**: live upload to the Supabase bucket (tested with a fake bucket and local disk); phone camera capture on a real device.
- **Affected Files**: `backend/alembic/versions/c1e5f7a9b3d2_exercise_photos.py`, `backend/app/models/exercise_photo.py`, `backend/app/models/__init__.py`, `backend/app/services/exercise_photos.py`, `backend/app/core/storage.py`, `backend/app/api/v1/exercises.py`, `backend/app/schemas/exercise.py`, `backend/app/services/prescription_service.py`, `backend/app/services/prescription_pdf.py`, `backend/tests/test_exercise_photos.py`, `frontend/exercise-library/src/**`

---

## [EL-D-005] Exercise categories: tag groups, filter panel and counts

- **Date**: 2026-10-27
- **Context**: Founders' feedback item 1 (23 Oct 2026) asked for 30+ categories. Answer to question 1 (27 Oct): use the same filter groups and category names as the reference platform the team uses, so we have the same number of categories; our exercise text and images are our own. The reference platform does not have one category list: every exercise carries tags from several groups and each group is a filter. The names were noted by hand from its filter panel (no data taken from it).
- **Decision**:
  - 11 groups, 222 values: Joint/Region 25, Position 11, Movement 22, Equipment 73, Difficulty 3, Specialty 18, Objective 43, Condition 12, Property of water 8, Assistance 2, Age group 5. The list lives in `app/services/exercise_categories.py`. Joint/Region runs head to toe, Difficulty from easy to hard, "No equipment" first, the rest alphabetical.
  - Objective completed on 30 Oct from a search for every letter a to z in the reference panel: 6 values added (BRRM (modified), Postural drainage, Swallowing, Taping, Tonal management, Traction). The seed migration has not reached production, so its frozen copy was updated in place.
  - Tables `exercise_categories` (group, name, order, active) and `exercise_category_links` (exercise, category), migration `d2f6a8c0e4b1` chained after `c1e5f7a9b3d2`. The migration seeds the list from its own frozen copy; a test checks the copy matches the module. Every category id is a uuid5 of group and name in a fixed namespace, so ids are the same on every database and tags can be written by id.
  - API: `GET /exercises/categories` returns the groups in panel order with each value's count over the exercises the clinic can see (its own and global). `GET /exercises?category=<id>` (repeat or comma separated): any value inside a group matches, every group must match. `POST` and `PUT /exercises` take `category_ids`: omitted keeps, a list replaces, an empty list clears; an unknown or inactive id gives 422 and nothing is saved. List, detail, create and update return each exercise's `categories`.
  - Library: the body part dropdown is replaced by a Filters panel (behaviour change): every group with counts, search inside groups longer than 6, show all, values with no exercises shown in grey, ticks apply straight away, ticked values stay as removable pills under the search with Clear all. Cards show the Joint/Region categories and fall back to the old body part.
  - `body_part` stays: the list order and `GET /exercises/body-parts` still use it, and older clients keep working.
- **Verified**: backend `pytest` on a fresh Postgres: base `feat/el-photos` 758bb51 361 pass / 10 known environment failures; this branch 368 pass / the same 10 (7 new: list matches the migration, list shape and fixed ids, groups and clinic-scoped counts, OR inside a group and AND across groups with search, bad and unknown ids refused, create and update set, keep, replace and clear, unknown or inactive ids save nothing and inactive values are hidden). Mutations: OR across groups, counts not limited to the clinic, and no id check each made a test fail. Migration: upgrade, downgrade, upgrade on a fresh database, 216 rows; `alembic check` shows only the two enum differences that exist on the base too. Frontend `tsc`, `eslint`, `next build` clean. Playwright on the production build at 1440 and 390 px against the 21 exercises of production (13 global from the seed migration, 4 per clinic) with draft tags: 17 visible, Cervical 6, Cervical and Retraction 2, Cervical or Shoulder 10, Clear all back to 17, Equipment shows all 73, Escape closes; no page errors, no failed calls.
- **Not verified**: live. The draft tags used in the local test are not in the repo and are not clinical decisions.
- **Affected Files**: `backend/alembic/versions/d2f6a8c0e4b1_exercise_categories.py`, `backend/app/models/exercise_category.py`, `backend/app/models/__init__.py`, `backend/app/services/exercise_categories.py`, `backend/app/services/exercise_category_service.py`, `backend/app/services/exercise_service.py`, `backend/app/repositories/exercise.py`, `backend/app/schemas/exercise.py`, `backend/app/api/v1/exercises.py`, `backend/tests/test_exercise_categories.py`, `frontend/exercise-library/src/**`

---

## [EL-D-006] Bigger exercise pictures in the library and on the prescription PDF

- **Date**: 2026-10-27
- **Context**: Onkar, 27 Oct, after the batch 1 to 3 release went live: the picture on the PDF the patient gets is too small to follow, and in the library it cannot be opened large. The new exercise pictures are wide (three numbered steps in one image).
- **Decision**:
  - PDF: each exercise card shows its number, name and body part, then the picture across the card (up to 60 mm high, about 85 mm wide for the current pictures; it was 40 x 32 mm beside the text), then the dose, steps and note. Two exercises fit on a page. Pictures are embedded at up to 1400 px (was 560) so they stay sharp.
  - Library: bigger thumbnail; clicking it opens the picture full size in a viewer (Escape, the close button or a click outside closes it).
  - No API or database change. Built on dev 60a0219, separate from `feat/el-photos` and `feat/el-categories` (those also change the card and the PDF and will need this merged in).
- **Verified**: pytest on dev 60a0219 369 pass / 10 known environment failures; this branch 370 / the same 10 (1 new test: picture above the dose, 60 mm, 1400 px; putting 560 px back makes it fail). Real PDFs rendered with three of the new pictures: 3 exercises on 2 pages, 6 on 3, every page looked at. Exercise Library `tsc`, `eslint`, `next build` clean; Playwright at 1440 and 390 px: viewer opens, picture 1024 x 721 on desktop and full width on a phone, Escape and outside click close it, no page errors.
- **Live**: since 27 Oct 2026 (dev 0c5212d).
- **Merged with EL-D-004** (29 Oct, `release/el-nov`): clinic photos use this layout. One photo sits across the card like a library picture; two photos sit side by side in the same area, each up to half the width and 60 mm high. In the library the clinic photo opens in the same full-size viewer.
- **Affected Files**: `backend/app/services/prescription_pdf.py`, `backend/tests/test_prescription_pdf.py`, `frontend/exercise-library/src/components/library/ExerciseCard.tsx`, `frontend/exercise-library/src/components/library/ImageViewer.tsx`

---

## [EL-D-007] Import of the AV exercise master list

- **Date**: 2026-10-30
- **Context**: Onkar, 30 Oct: every exercise of the AV master sheet (1507 rows, AV-EX-0001 to AV-EX-1500 plus 7 rows with another id format) goes into the library, with no duplicates. Images follow later with the image pipeline.
- **Decision**:
  - Migration `f4a9c2e7b1d3` (after `d2f6a8c0e4b1`) adds 1442 global exercises: id `md5('AV-EX-xxxx')::uuid`, title from the sheet, `body_part` from the sheet category, description empty (the sheet holds image prompts, not patient instructions), `is_free` true, no picture.
  - Not inserted (65 rows): 17 already in the library (5 renamed originals and 12 added on 27 Oct); 20 that repeat another sheet row under a reworded name (for example "Wall angel" and "Wall angels", "Supported mini squat" and "Mini squat (supported)"), keeping the name that fits the `<exercise> (<variant>)` pattern; 14 "(supported)" copies of exercises that are already supported; 7 rows without an AV-EX id (left out until they get one); 7 that are the same as an original exercise.
  - Those 7 originals are renamed to the sheet name instead of getting a second row, so saved prescriptions keep their exercise: CHIN TUCKS to Chin tuck, PENDULUM EXERCISE to Pendulum, the two cervical isometrics to Cervical flexion isometric and Cervical extension isometric, GLUTE SQUEEZE to Glute set, SCAPULAR SQUEEZES to Scapular retraction, WALL SLIDES to Wall angels (its description is a wall angel).
  - The insert skips any title that a global exercise already has (case and spaces ignored), and ids that exist, so a second run adds nothing. Downgrade removes only imported rows that no prescription or clinic photo uses.
- **Verified**: 11 parametrized checks on the frozen list (sheet numbers, id format and uniqueness, titles unique as written and with word order, plurals and punctuation ignored, no clash with the original or production titles, renames point at the right seed rows, column lengths, body part order, counts); adding a repeated or existing exercise to the list makes them fail. On a copy of production's exercise rows (25 global): 1467 after upgrade, no repeated title; downgrade with one imported exercise used in a prescription keeps that one (26); upgrade again 1467; a second run on an imported database adds nothing. Fresh database: 1455. Full pytest 400 pass / the same 10 known failures. Library on the production build at 1440 and 390 px: 1455 exercises, search "squat" 39, no page errors or failed calls.
- **Not verified**: live.
- **Affected Files**: `backend/alembic/versions/f4a9c2e7b1d3_import_av_exercise_master_list.py`, `backend/tests/test_exercise_master_import.py`

---

## [EL-D-008] Global exercises read-only for clinics; categories set from the card; titles as written

- **Date**: 2026-10-30
- **Context**: With 1455 shared exercises (EL-D-007), any clinic with `exercises.edit` could rename, re-tag or delete an exercise every clinic sees (EL-L-12). There was also no screen to set categories (EL-L-10). Onkar chose option A on 30 Oct.
- **Decision**:
  - `PUT` and `DELETE /exercises/{id}` on a global exercise give 403 ("part of the AV library") and change nothing. Clinics change only their own exercises. Clinic photos of a global exercise stay allowed (EL-D-004). Global exercises change only through migrations or SQL until an AV staff role exists.
  - Library card: a Categories button (users with `exercises.edit`, own exercises only) opens a dialog with every category group (same boxes as the filter panel) and saves with `category_ids`. Filter counts refresh after a save. In both the dialog and the filter panel a ticked value always shows, also when its group is collapsed.
  - Titles show as written, so "ROM" stays "ROM". Titles mostly in capitals (the older "CHIN TUCKS" style) show in sentence case. Same rule in the library (`lib/displayTitle.ts`) and on the PDF (`display_title`).
- **Verified**: 7 new tests (title, categories, clearing and both on a global give 403 with title and links unchanged; delete of a global gives 403 and the row stays; own exercise changes and deletes; another clinic's exercise stays 404); without the guard 5 fail. 7 title cases, same output from the TypeScript and Python versions. Full pytest 414 pass / the same 10 known failures. `tsc`, `eslint`, `next build` clean. Live API locally: PUT and DELETE on "Chin tuck" give 403, title unchanged. Playwright at 1440 and 390 px: Categories button on the clinic's own exercise only, Knee and Standing saved (card shows Knee, counts 1), dialog reopens with both ticked and visible, clearing works, no page errors.
- **Not verified**: live.
- **Affected Files**: `backend/app/services/exercise_service.py`, `backend/app/api/v1/exercises.py`, `backend/app/services/prescription_pdf.py`, `backend/tests/test_global_exercise_read_only.py`, `backend/tests/test_prescription_pdf.py`, `frontend/exercise-library/src/components/library/CategoryEditDialog.tsx`, `CategoryFilter.tsx`, `ExerciseCard.tsx`, `ExerciseList.tsx`, `ImageViewer.tsx`, `PhotoDialog.tsx`, `components/prescription/ExerciseRow.tsx`, `src/app/page.tsx`, `src/lib/api.ts`, `src/lib/displayTitle.ts`, `src/types/exercise.ts`

---

## [EL-D-009] Exercise templates, minimal version (clinic templates that fill a prescription)

- **Date**: 2026-10-30
- **Context**: Founders asked EL-7 (is a template per exercise or a generic program?) and EL-8 (whose branding?). The reference platform's templates are generic programs (name, description, several exercises). Onkar decided on 30 Oct: clinic templates first, a template only pre-fills a prescription, and a minimal version goes in this release.
- **Decision**:
  - New tables `exercise_templates` (clinic_id, name, description, created_by) and `exercise_template_items` (exercise, position, sets, reps, hold, frequency, note; one row per exercise). Migration `a3d8f1c5e7b2` on `f4a9c2e7b1d3`.
  - `clinic_id` NULL is kept for AV templates shared with every clinic, the same rule as global exercises. They are listed after the clinic's own and are read-only (403). None exist yet; adding them later is data only.
  - API `/exercise-templates`: list, get (needs `exercises.view`), create, replace, delete (need `prescriptions.create`, so no new capability and no role template change). Every exercise must be the clinic's own or global, else 422 and nothing is saved. Same dose bounds as prescriptions, at most 50 exercises, no repeats.
  - Builder: a Templates block under the patient. "Save as template" stores the exercises on screen with their dose, never patient details. "Use" fills a NEW prescription (asks first if there are unsaved exercises, never overwrites a saved one); the physio changes the dose and saves as usual. Own templates can be deleted.
  - Branding (EL-8): a template has none. The PDF is always made from the saved prescription, with the letterhead of EL-D-002.
  - Deleting an exercise drops it from templates (cascade); using a template then reports how many are missing.
- **Verified**: 13 new tests (create, list, get keep order and dose with categories; replace and delete; another clinic gets 404 on all four calls; another clinic's or unknown exercise gives 422 and saves nothing; 6 bad inputs give 422; AV template listed after own and read-only; deleted exercise drops out; migration chain). Migration up, down one, up again on an empty database: one head `a3d8f1c5e7b2`. Full pytest 427 pass / the same 10 known failures. `tsc` and `eslint` clean.
- **Not verified**: the builder in a browser; live.
- **Affected Files**: `backend/app/models/exercise_template.py`, `backend/app/models/__init__.py`, `backend/app/schemas/exercise_template.py`, `backend/app/services/exercise_template_service.py`, `backend/app/api/v1/exercise_templates.py`, `backend/app/api/v1/router.py`, `backend/alembic/versions/a3d8f1c5e7b2_exercise_templates.py`, `backend/tests/test_exercise_templates.py`, `frontend/exercise-library/src/components/prescription/TemplatesPanel.tsx`, `PrescriptionBuilder.tsx`, `src/lib/api.ts`

---

## Known Limitations

| # | Item | Status | Owner |
|---|---|---|---|
| EL-L-01 | Body part names are free text. Synonyms show as separate entries next to each other (e.g. "Thoracic" and "Upper Back"), and some exercises sit in the wrong part (e.g. a neck isometric under "Other") | Partly fixed: fixed category list since EL-D-005; `body_part` still drives the list order (EL-L-13) | Us + founders |
| EL-L-02 | L-35 (CRM file), exercise part fixed here: exercises page through the whole library. The patient picker still loads at most 100 patients | Open | Frontend |
| EL-L-03 | Red flags: no reviewed list exists. Quick picks only reuse what the clinic already wrote | Open; founders to give or approve a list | Founders |
| EL-L-04 | Quick picks read the clinic's last 1000 exercise notes and last 1000 prescriptions; older phrases drop out | Accepted | - |
| EL-L-05 | Exercise pictures and videos share `video_url`. Since EL-D-003 the API reads them apart (`image_url`, `demo_video_url`); the stored column is still shared. No relative names left in production (24 Oct) | Partly fixed; proper media model with the founders' answer on personalised photos | Backend + founders |
| EL-L-06 | The CRM settings page accepts any `image/*` logo and the settings API does not check the value. SVG logos never print on the prescription (name only) | Open; limit the CRM upload to PNG/JPEG/WebP, in the CRM round | CRM |
| EL-L-07 | The PDF names the prescribing therapist. "Head of clinic" needs clinic profile fields that do not exist yet (CRM L-14) | Open; founders to choose, fields come with the CRM clinic profile work | Founders + backend |
| EL-L-08 | The Exercise Library asks `/auth/me` twice on load (header and page) | Accepted; merge into one call when the header is next changed | Frontend |
| EL-L-09 | Library pictures and videos still share `video_url`; clinic photos have their own table (EL-D-004). Moving library pictures into the same model waits for the categories work (founders' reference for Q1) | Open | Backend |
| EL-L-10 | Categories of a clinic's own exercises are set from the card (EL-D-008). Global exercises (1455) carry no categories until reviewed tags come in a data migration | Partly fixed; global tags after review | Us + founders |
| EL-L-11 | Counts in the panel do not change with the filters picked. (The Objective list was completed on 30 Oct, 43 values.) | Open | Frontend + backend |
| EL-L-12 | Global exercises could be changed by any clinic | Fixed by EL-D-008 (403). Global changes need an AV staff role later | - |
| EL-L-13 | The list is still ordered by the free-text `body_part`, not by the Joint/Region categories | Open; switch once every exercise is tagged | Backend |
| EL-L-14 | Imported exercises have no picture, description or categories. 44 "(seated)" variants (found by a name check) describe positions that cannot be done seated (for example "Prone Y raise (seated)", "Glute bridge (seated)"); they were imported as asked and need a physio review. Card titles in title case ("Rom") fixed by EL-D-008 | Open; pictures with the image pipeline, tags and review with the founders | Us + founders |
| EL-L-15 | Templates, minimal version (EL-D-009): no AV templates yet (who writes and approves them is open with the founders); no edit screen (change = use, adjust, save as a new template, delete the old); no tags, phases or search; the guidance text is not saved in a template | Open; next release | Us + founders |

*Last updated: 2026-10-30 (EL-D-009, EL-L-15) | Branch: release/el-nov*
