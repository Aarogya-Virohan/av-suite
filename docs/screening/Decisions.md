# Tool 03 Psycho-Social Screening: Decisions

Format: context, choice, reason, decided by. Status "pending sign-off" means it is built as the safe default and can still change.

A one-line index of every decision, and the points to review before deploy, during the pilot and before scale, is in Review_Points.md.

## S-D-001 Branch base
- Context: Tool 03 work starts on its own branch.
- Choice: `feat/tool03-psychosocial` from `origin/dev` at `770bc87507a541ae93700751c517de21c7dca708` (20 Oct 2026). Alembic head at that commit: `a8c4e2f1d903` (single head).
- Decided by: Onkar (handoff).

## S-D-002 Reuse the existing product key `psycho-social-screening`
- Context: the handoff proposed a new key `psychosocial-screening`. The repo already registers `psycho-social-screening` in `backend/app/core/products.py`, in migration `6b0f1d2c3a4e`, in `d0c1b2a3f4e5` (allowed clinic types) and in `frontend/av-marketplace/data/products.ts`.
- Choice: use `psycho-social-screening`. No new product row. Capability prefix mapping for it gets added in `PRODUCT_CAPABILITY_PREFIXES` when the capabilities land.
- Reason: a second key would split entitlements and break the marketplace card.
- Decided by: proposal, pending Onkar sign-off.

## S-D-003 Engine location and shape
- Choice: generic engine in `backend/app/screening/`. Instrument definitions are frozen Python dataclasses with an `id` and `version`, registered in `registry.py`. Scoring (`scoring.py`) is pure: no DB, no IO.
- Reason: definitions are reviewed in code and covered by tests. Sessions will store `instrument_id`, `instrument_version`, raw responses and computed results, so old results stay explainable. Tool 04 instruments plug in the same way.
- Decided by: Onkar (handoff section 8).

## S-D-004 Instrument wording is verbatim from the published forms
- PHQ-9 and GAD-7: item text, stems and the four options follow the published Pfizer forms, including the em-dashes inside PHQ-9 items 6 and 8 (fidelity to the instrument wins over our no-em-dash writing rule). Both are free to reproduce, no permission needed.
- DASS-21: item text and options from the Lovibond 1995 short form. One adaptation: the instruction says "choose the option" instead of "circle a number 0, 1, 2 or 3", because there is nothing to circle on screen. The DASS is public domain per its authors; we must reference the DASS website (done in `licence_note`, to be shown in the UI footer).
- Decided by: proposal, pending Onkar sign-off on the DASS instruction adaptation.

## S-D-005 PHQ-9 item 9 risk rule (founder question F1)
- Context: the SRS has no rule for item 9 (thoughts of self-harm).
- Choice: any answer above 0 on item 9 sets `risk_item_flag = true` and forces `referral_flag = true`, whatever the total.
- Decided by: safe default from handoff, pending founder sign-off.

## S-D-006 Functional difficulty question kept, not scored
- Context: both published PHQ-9 and GAD-7 forms end with "how difficult have these problems made it...". It is not part of the score.
- Choice: included as an optional, unscored item (`phq9_difficulty`, `gad7_difficulty`) so the physio sees it. It never changes the total or the band.
- Decided by: proposal, pending Onkar sign-off.

## S-D-007 DASS-21 fully scored and validated
- Context: SRS section 6 lists DASS-21 scoring validation as a stretch goal for v1.0.
- Choice: scored and tested to the same bar as PHQ-9 and GAD-7. Subscale = sum of 7 items x 2, Lovibond 1995 cut-offs. Referral at Severe or above on any subscale (SRS 4.1.3).
- Decided by: Onkar (handoff plan step 2).

## S-D-008 Band labels
- PHQ-9 and GAD-7 lowest band is labelled "None-minimal" (Kroenke 2001 / Spitzer 2006 wording) where the SRS table says "None". Score ranges are identical.
- Decided by: proposal, pending Onkar sign-off.

## S-D-009 Patients are not product-gated
- Context: a clinic may buy Tool 03 without CRM.
- Finding (verified in `core/products.py`): `patients.*` capabilities are platform-core and are not in `CAPABILITY_PRODUCT_MAP`, so a screening-only clinic can still list and pick patients. No change needed for the patient picker.
- Decided by: verified fact, recorded for the build.

## S-D-010 Data model: one link, one session per screener
- Context: a physio can assign several screeners at once (SRS 4.1.1). One link per screener would mean several WhatsApp messages for one patient.
- Choice: `psychosocial_assignments` is the link (hashed token, expiry, status). Each assigned screener is a row in `psychosocial_sessions` with its own status, raw responses (JSONB), `instrument_id`, `instrument_version` and computed result. The patient fills them in the assigned order on one link.
- The token is `secrets.token_urlsafe(32)` and only its SHA-256 is stored, so a database leak does not expose working links. The link is shown once when it is created. If it is lost, the physio issues a new link, which kills the old one.
- Consent (`psychosocial_consents`) and referral actions (`psychosocial_referral_actions`) are append-only logs.
- Decided by: proposal, pending Onkar sign-off.

## S-D-012 No entitlement granted by migration
- Context: CRM lesson, new products need an explicit grant decision.
- Choice: migration `b3d7e1f0c2a9` creates tables only. A clinic gets `psycho-social-screening` through the existing marketplace install flow (`services/marketplace.py install_product`), the same as other add-on tools. No existing clinic gets it silently.
- Decided by: proposal, pending Onkar sign-off.

## S-D-013 Immutability enforced in the database too
- Choice: a Postgres trigger (`trg_psychosocial_sessions_immutable`) rejects any UPDATE of a session row whose status is already `completed`. DELETE stays allowed, which the deletion-on-request flow needs. The same SQL is attached to the model, so test databases built with `create_all()` have the trigger as well.
- Verified: the API test tries a raw UPDATE on a completed row and expects the error, and a manual check on a database built through the full Alembic chain gave the same error, while cascade DELETE still worked.
- Decided by: proposal, pending Onkar sign-off.

## S-D-011 Capabilities and the admin default (founder question F3)
- New keys in `core/rbac.py`: `screening.assign` (None/All), `screening.view` (None/Own/All), `screening.refer` (None/Own/All). Own means sessions the user assigned. All three map to the `psycho-social-screening` product in `core/products.py`, so a clinic without the product gets `PRODUCT_NOT_ENTITLED`.
- Shared file change: `_admin_template()` now leaves `screening.view` and `screening.refer` at None (`ADMIN_TEMPLATE_EXCLUDED`). SRS 3.2 says administrators never see individual responses. Admins keep `screening.assign`, so they can send links (F5 default) but cannot open results.
- Therapists start at None for everything, like every other module in this repo. An admin grants the screening keys per physio. Every grant is audited by the existing permissions endpoint.
- Gap found: the CRM permission grid (`frontend/crm/src/config/permissions.ts`) is a hardcoded list of 64 keys, so the new keys do not show there. The Tool 03 app will carry its own small access page for this (SRS 4.3.1). The CRM list needs the 3 keys later (Pending P-08).
- Decided by: F3 safe default, pending founder sign-off.

## S-D-014 Staff API shape
- Assign: `POST /api/v1/patients/{id}/psychosocial/sessions` with `{instruments, expires_in_days}` (1 to 30, default 7, F5). Returns the assignment and `screener_path` (`/screener/{token}`), path only. The app that hosts the screener adds its own origin, so the backend needs no frontend URL setting.
- Review: patient list, clinic worklist (`GET /psychosocial/sessions`, filter by status and flagged, risk-item rows first, which covers the F4 default "flagged badge in the session list"), session detail with every item, the answer label, the reasons for any flag and the baseline compare (first completed session of the same screener).
- Cancel only while nothing is answered (SRS 4.1.1 "not yet started"). Re-issue link kills the old token.
- Referral action log only on a completed, flagged session. Actions: referred_gp, referred_psychologist, referred_psychiatrist, already_under_care, patient_declined, monitor_and_rescreen, other, plus an optional note.
- CDSS read contract v1: `GET /patients/{id}/psychosocial/summary` gives the latest completed session per screener plus `referral_flag` and `risk_item_flag` (SRS 5.1). Supporting input only.
- Decided by: proposal, pending Onkar sign-off.

## S-D-015 Audit events carry no clinical values
- Events: `psychosocial.assigned`, `.cancelled`, `.link_reissued`, `.consent_granted`, `.consent_withdrawn`, `.completed`, `.result_viewed`, `.referral_logged`. Details hold ids and screener names only, never a score, band or flag, because admins can read the audit log (SRS 3.2). Opening a result is audited because it is sensitive data.
- Decided by: proposal, pending Onkar sign-off.

## S-D-017 Risk answer visible before submit
- Context: if a patient answers PHQ-9 item 9 above zero and then closes the page, the session never completes and no flag would show.
- Choice: every staff view computes `partial_risk` for in-progress sessions from the saved answers, so the physio sees it without a submit. The final flags are still written only on submit.
- Decided by: proposal, pending founder sign-off with F1.

## S-D-016 Consent (founder question F6)
- The consent text lives in the backend (`app/screening/consent.py`) with a version string. Every consent row stores that version, so we can always show which wording a patient agreed to. A new version asks the patient again on their next link.
- Consent is per patient, asked before the first screener and again only when the text version changes (SRS 4.2.1). No answer is saved without it (`CONSENT_REQUIRED`).
- Withdrawal from the screener page records a `withdrawn` row, cancels every open link for that patient and blocks new links (`CONSENT_WITHDRAWN`). Completed results stay until a deletion request (S-L-005).
- Text status: draft `2026-10-20.draft1`, pending founder approval.
- Decided by: F6 safe default, pending founder sign-off.

## S-D-018 Public screener routes and rate limiting
- Routes under `/api/v1/screener/{token}`: GET (questions and saved answers, no patient identity, no session ids, no scores), `/consent`, `/withdraw`, `/answers` (auto-save, one call per answer), `/submit`. Added to the ClinicGate public allowlist (shared file change).
- Answers are accepted strictly in order: only the next unanswered item. Re-sending the same answer is a no-op (safe retry). A different value for a saved item gets `ANSWER_LOCKED` (SRS 4.2.2). A row lock stops two fast taps from both claiming the next item. Re-sending a submit that already went through returns the same reply, so a dropped response loses nothing.
- Repo check first, as asked: there is no rate limiter in the repo, and the Turnstile check in `api/v1/booking.py` is a form CAPTCHA, not a rate limiter, so there was nothing to reuse. No new dependency was added (Onkar, 20 Oct).
- Limiter: in-process sliding window in `app/screening/rate_limit.py`, on the public routes only. Two keys per request: per link token 200 requests per 15 minutes, per client IP 600 per 15 minutes. All three screeners on one link take about 50 requests, so a real patient stays far below both. Memory is capped at 20,000 tracked keys. A blocked call gets 429 `RATE_LIMITED` with `Retry-After`.
- Client IP: the shared `get_client_ip()` trusts `CF-Connecting-IP` and the leftmost `X-Forwarded-For` from any caller, so it is not used. The limiter reads only the header named in the new optional setting `SCREENER_CLIENT_IP_HEADER`, otherwise `request.client.host`. Checked by running uvicorn with the Dockerfile flags (`--proxy-headers --forwarded-allow-ips=*`): `request.client.host` becomes the leftmost `X-Forwarded-For` entry. That is the real client only if Railway's edge replaces any client-sent `X-Forwarded-For`. Railway staff answers on this disagree. A Railway moderator says `X-Real-IP` is written at the edge and cannot be spoofed. Recommendation: set `SCREENER_CLIENT_IP_HEADER=X-Real-IP` on Railway before merge (Pending P-04). Spoofed IPs can only dodge the per-IP limit. The per-token limit and the 32-byte token still hold.
- Decided by: Onkar (in-process, no dependency, per token and per IP); header choice is a proposal pending Onkar.

## S-D-019 Standalone app `frontend/psychosocial` with CRM tokens copied verbatim
- Approved by Onkar (20 Oct): separate app, local build and test only. Onkar adds the Vercel project and the CORS origin at deploy time.
- `globals.css`, `brand.tsx`, `SlideOver.tsx` and `cn.ts` are verbatim copies from `frontend/crm` at commit `619502675d60dacd0226c074cb1b506258c9f955`, so a diff shows any drift. App-only CSS is in `app.css`. The CRM SlideOver uses `animate-fade-in` and `animate-slide-in-right`, which the CRM never defines. This app defines them in `app.css`.
- Same login and token storage key (`token`) as the CRM and Exercise Library. Gating comes from `/me` (`capabilities`, `active_products`).
- Pages: Screenings worklist (Needs attention includes unsubmitted risk answers), patient page (send screener, history, new link, cancel), result page (risk banner, score, severity, baseline, every answer, referral log), Access (SRS 4.3.1, because the CRM grid lacks the new keys), Add patient (for clinics without the CRM), public screener.
- Decided by: Onkar (app), proposal for the page set.

## S-D-020 Frontend tooling versions
- Shared dependencies are pinned to the CRM lockfile versions (Next 16.3.2, React 19.2.4, Tailwind 4.3.3, TanStack Query 5.101.4).
- Two deliberate differences. `vitest` is 3.2.4: npm 10.9 crashes (`Cannot read properties of null (reading 'edgesOut')`) on install with vitest 4 or 5. And `@types/node` is 22: vitest needs it, and the CRM lockfile has the same peer conflict with 20. Unit tests cover pure logic only. UI behaviour is covered by Playwright 1.56.0.
- Decided by: proposal, pending Onkar sign-off.

## S-D-021 Patient screener behaviour
- One question per screen. Large option buttons work as a radio group (arrow keys, screen reader). The patient picks an option, then presses Next. Next saves the answer, and from then on it cannot change (SRS 4.2.2).
- Answers save in the background in order, so the next question shows at once (SRS 3.5). A dropped call retries with backoff, and Send waits until every answer is saved. If the server disagrees (`ANSWER_LOCKED` or `OUT_OF_ORDER`), the page reloads its state from the server.
- The patient never sees a score. After submit they see a calm message when a referral flag is set. When the PHQ-9 item 9 risk flag is set, they also see Tele-MANAS (14416 or 1-800-891-4416, 24x7, verified on PIB 11 Feb 2026) and 112 for immediate danger (F2 default, pending founder sign-off).
- Patient-facing titles are plain ("How you have been feeling"). Question and option text is the published wording. The DASS website reference shows on DASS-21 screens.
- Decided by: proposal, pending founder sign-off for F2 wording.

## S-D-022 Scoring validation report is generated from the tests
- Context: SRS section 7, deliverable 02 asks for a document or test output showing correct PHQ-9 and GAD-7 scores for at least 5 inputs each, matched against published norms.
- Choice: `docs/screening/Scoring_Validation_Report.md` is generated by `backend/tests/screening/validation_report.py`. It runs the hand-written golden cases from `test_scoring.py` and every possible score through the production scoring function and prints expected and actual values side by side. The generator exits with an error on any mismatch. `test_validation_report.py` fails when the committed report no longer matches the engine, so the report cannot silently go stale.
- Coverage: 12 PHQ-9 cases, 8 GAD-7 cases, 10 DASS-21 cases, every total for each instrument, and invalid input, 153 checks in all.
- Verified: changing the GAD-7 Moderate band to 10 to 13 made the generator report 2 failures and made both report tests fail.
- Decided by: proposal, pending Onkar sign-off.

## S-D-023 Fixes found while re-running the frontend checks (22 Oct)
- App icon: the app had no favicon, so every page made the browser request `/favicon.ico` and log a 404 console error. The Playwright tests fail on any console error, and on a re-run 4 of 6 failed for this reason alone. Choice: `src/app/icon.png`, a copy of `public/brand/av-logo-mark.png`, which Next serves as the page icon. After the fix: 6 of 6 pass, twice. The CRM has no favicon either. That is noted here only, it is not changed from this branch.
- Vitest scope: there was no vitest config, so `npm test` also collected `e2e/screening.spec.ts` and exited with status 1 even though the 4 unit tests passed. Choice: `vitest.config.ts` limits vitest to `src/**/*.test.{ts,tsx}`. After the fix: `npm test` exits 0 with 4 of 4.
- Decided by: proposal, pending Onkar sign-off.

## S-D-024 Deletion on request (SRS 3.2)
- Context: SRS 3.2 says patients must be able to request deletion of their screening history, and the consent text tells them they can ask the clinic. Until now that needed a manual database step (S-L-005).
- Who: the clinic admin. A new capability `screening.delete` (None/All) is in the admin template and starts at None for therapists and front desk. Deletion cannot be undone, so one accountable role handles it (Onkar, 22 Oct). The admin still cannot see any answers or scores: the screen shows counts only. A clinic can grant `screening.delete` to another user through the permissions endpoint, and the grant is audited. The Tool 03 Access page does not show it.
- What is deleted, in one transaction: every link, every screener session (answers and results, including completed ones; the immutability trigger blocks UPDATE, not DELETE), every referral action and every consent record of that patient in that clinic.
- What is kept: if the patient's latest consent decision is a withdrawal, that one record stays (status, text version, date, with its link reference cleared). Without it, a clinic could send a new screener to a patient who said no. The patient profile itself is not touched.
- Audit: one `psychosocial.data_deleted` event with the admin's user id and the counts removed. No scores, bands, flags or screener names.
- API: `GET /patients/{id}/psychosocial/data` (counts and whether a withdrawal is on file) and `POST /patients/{id}/psychosocial/data/delete` with `{"confirm": "DELETE"}`. Any other confirm value is rejected with 422. Running it twice is safe.
- UI: a "Delete screening data" card on the patient page for holders of `screening.delete`. The drawer lists what is deleted and what stays, and the delete button unlocks only after typing DELETE.
- Verified: 7 backend tests in `test_deletion.py` check every table in the database before and after, a second patient's data staying intact, the kept withdrawal, 403 without the capability, 404 across clinics, and the audit details. Mutation checks (keep logic removed, consents not deleted, a clinical word in the audit details, the wrong capability) each made at least one test fail. Playwright runs the admin flow at 390 px and 1440 px and confirms both old links return 404 afterwards.
- Limits: S-L-011 (patients in the CRM recycle bin), S-L-012 (earlier audit events stay).
- Decided by: Onkar (admin only); the rest is a proposal, pending Onkar sign-off.

## S-D-025 Score trend and PDF summary (SRS 4.1.2, 4.1.4, 3.5)
- Trend: `app/screening/trend.py` builds one series per scored scale from completed sessions, oldest first. Points use the score stored at submit time. Bands and the referral line come from the published instrument definition (PHQ-9 and GAD-7 from 10, DASS-21 depression 21, anxiety 15, stress 26). The API (`GET /patients/{id}/psychosocial/trend`, `screening.view`) and the PDF both use it, so they always agree.
- Chart: drawn as SVG in the app, no new chart library. X is spaced by date, so 24 months of results spread by time, not by count. Bands are named on the chart and points carry a title, and a hidden table lists every result for screen readers (SRS 3.6). Values are printed on the points up to 12 results. On phones the chart keeps a minimum width and scrolls inside its card so labels stay readable; the page itself does not scroll sideways (checked in E2E 5).
- PDF: `GET /patients/{id}/psychosocial/report.pdf` (`screening.view`, same Own/All scope as the app). Rendered with WeasyPrint in a worker thread, streamed with `Cache-Control: no-store`, never stored, never on a public path. Content per SRS 4.1.4: trend charts, every completed session with scores, bands and flags, every referral action with note and author, plus clinic name, patient details, report ID, generation time and author, a disclaimer and a signature line. Individual answers are left out: the SRS does not ask for them and they stay one click away in the app. With Own scope the PDF says it includes only the user's own screenings.
- Look: brand constants and fonts are imported from the posture PDF module, the same way the prescription PDF does on `dev`. Nothing in the posture module changes.
- Audit: `psychosocial.report_generated` with the patient id and the number of sessions. No clinical values.
- Verified: 9 backend tests (series order, published referral lines, scope, clinic isolation, 24 monthly results with the PDF in under 15 s, headers, audit, report content, empty patient, HTML escaping). Five mutation checks (newest first, scope ignored, escaping removed, audit renamed, referral line off by one band) each failed at least one test. A 28-session, 24-month report was rendered and read page by page (about 2.5 s). Playwright downloads the PDF on phone and desktop and checks the file starts with %PDF.
- Decided by: proposal, pending Onkar sign-off.

## S-D-026 Repeat schedules and the Due list (SRS 4.1.1 recurring)
- Context: SRS 4.1.1 asks for screeners that repeat at an interval. Links reach the patient through the physio's WhatsApp, and the system cannot send WhatsApp itself. A link created by a scheduler would sit unused, so a scheduler or cron job adds moving parts for no gain.
- Choice: no scheduler. A schedule (`psychosocial_schedules`, migration `c4e8a2b6d1f3` on top of `b3d7e1f0c2a9`) stores the patient, the screener and the interval. The physio picks "Repeat" in the send drawer (just once, every 2, 4, 6, 8 or 12 weeks; the API accepts 1 to 52 weeks). One active schedule per patient and screener; sending again with another interval changes it. "Stop repeating" sets `stopped_at` and keeps the row.
- When it is due: last completed result of that screener + interval, or straight away if it was never answered and no link is open (cancelled or expired). While a link with that screener is open it is "waiting". If the patient's latest consent decision is a withdrawal it is "paused" and never due. Patients removed in the CRM are left out of the Due list.
- Where it shows: a "Due again" tab on Screenings (most overdue first, no results in it) and a banner on the patient page with "Send due screeners", which opens the send drawer with the due screeners ticked. Both need `screening.assign`, so an admin who sends links sees what is due but still no results.
- Deletion on request now also removes the patient's schedules (S-D-024).
- Audit: `psychosocial.schedule_set` (screeners and interval) and `psychosocial.schedule_stopped`. No clinical values.
- Verified: 12 backend tests (every state in the pure function including the boundary day, interval change, waiting, cancelled and expired links, withdrawn and removed patients, stop and restart, access, clinic isolation), the deletion tests now count schedules, six mutation checks each caught. Playwright runs the whole flow at 390 px and 1440 px. It caught a stale schedule card after a cancel, fixed in the same delivery. Migration upgrade, downgrade and upgrade again checked on an empty database; `alembic check` shows only the old enum drift (P-09).
- Decided by: Onkar (due list, no scheduler, 22 Oct); details are a proposal pending his sign-off.

## S-D-027 Clinic configuration (SRS 4.3.2)
- Context: SRS 4.3.2 asks for clinic-wide default screening intervals per instrument, and for configurable referral thresholds whose defaults match the published norms, with any clinic change confirmed.
- Default intervals: a new table `psychosocial_clinic_settings` (migration `d5f9b3c7e2a4` on top of `c4e8a2b6d1f3`), one row per clinic and screener, holding `default_repeat_weeks` (1 to 52, or empty for just once). The admin sets it on a new Settings page. It only prefills the Repeat field in the send drawer, and the sender can still change it. Changing a default never edits repeats that are already running.
- Prefill rule: one link has one repeat, so the default is used only when every ticked screener shares it. If they differ, the field stays at Just once and the drawer names each default. A screener that already repeats for this patient never gets the default, because sending with a repeat replaces the running interval (S-D-026). Without this rule, "Send due screeners" would quietly move a patient from, say, every 2 weeks to the clinic default. The drawer says which repeat is running and that Just once keeps it. While the patient's schedules are still loading nothing is prefilled.
- Thresholds: shown read-only on the same page, built from the instrument definitions (`app/screening/thresholds.py`) so the page cannot drift from scoring. A test checks the page's referral line against the scoring engine at every possible score. Editing is not built: it changes who gets a referral recommendation, which is a clinical decision for the founders, and PHQ-9 item 9 (F1) is still open. What editing would need is listed in Pending P-13.
- Access: new capability `screening.configure` (None/All), in the admin template, None for therapists and front desk. It holds clinic settings only, no patient data. The CRM permission grid does not list it yet (P-08), and the Tool 03 Access page does not manage it.
- API: `GET /psychosocial/settings` and `PUT /psychosocial/settings/{instrument_id}` (`screening.configure`). `GET /psychosocial/instruments` now also returns each screener's `default_repeat_weeks` for the send drawer.
- Audit: `psychosocial.settings_updated` with the screener and the value before and after. Saving an unchanged value writes nothing.
- Verified: 16 backend tests in `test_settings.py`, 6 new vitest cases for the prefill rule, and Playwright E2E 7 at 390 px and 1440 px (admin saves defaults, physio sees the prefill and the mixed-default hint, a running 4-week repeat stays at 4 weeks after the admin changes the default to 2 weeks and the due screener is sent again).
- Decided by: Onkar (start with 4.3.2, 22 Oct); read-only thresholds and the prefill rule are a proposal, pending Onkar sign-off.

## S-D-028 Anonymised clinic statistics (SRS 4.3.3)
- Context: SRS 4.3.3 asks for clinic statistics (sessions completed, band distribution, referral flag rate), all anonymised, filtered by date range and screener, with CSV export. SRS 3.2 says administrators see only anonymised, aggregated data.
- What is counted: completed screeners of the clinic whose completion date falls in the range. Dates are Indian calendar days (IST). The default range is the last 90 days, and the longest is three years. Open, cancelled and expired links are not counted. Bands come from the result stored at submit time, so an older result keeps the band it was scored with. Results of patients later moved to the CRM recycle bin are still counted, since nothing identifies them here.
- Small-cell rule (Onkar, 22 Oct: minimum 5): with fewer than 5 completed in the period only the total is shown. Any band count from 1 to 4 is hidden. If exactly one band is hidden, the smallest other non-zero band is hidden too, so the hidden one cannot be worked out from the total. The referral figure is hidden when either the flagged or the not-flagged count is from 1 to 4. Zero is always shown. The rules live in one pure module, `app/screening/aggregates.py`.
- Access: new capability `screening.aggregates` (None/All), in the admin template, None for therapists and front desk. The response holds only totals, labels and counts: no patient ids, names, session ids or scores. A test checks the response keys and that no UUID appears in it.
- API: `GET /psychosocial/aggregates?from=&to=&instrument=` and `GET /psychosocial/aggregates.csv` with the same parameters. The CSV carries exactly what the screen shows, with hidden cells written as "hidden". It is streamed with `no-store` and never stored. The file name is built in the browser, as for the PDF (S-L-013).
- Audit: `psychosocial.aggregates_exported` with the range and screener. Viewing the page is not audited.
- Verified: 24 backend tests in `test_aggregates.py` (suppression cases, a 5000-case randomised check that a hidden count can never be worked out from the total, referral rule, IST day boundaries at 23:59 and 00:01, other clinics and open links not counted, invalid ranges, CSV content and headers, audit, access). Playwright E2E 8 at 390 px and 1440 px: five patients answer, the counts show; a sixth answers Moderate and the page hides both affected bands and the referral figure; filters; the CSV download.
- Limits: S-L-017 (a whole group in one band), S-L-018 (computed per request in Python).
- Decided by: Onkar (minimum cell 5); the secondary rule, the referral rule and the rest are a proposal, pending Onkar sign-off.
