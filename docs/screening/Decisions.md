# Tool 03 Psycho-Social Screening: Decisions

Format: context, choice, reason, decided by. Status "pending sign-off" means it is built as the safe default and can still change.

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
