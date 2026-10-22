# Tool 03 Psycho-Social Screening: DoD Checklist

SRS section 7, deliverable 04: a self-completed checklist for every functional requirement in SRS section 4.

Branch `feat/tool03-psychosocial`, v1.0 core (draft PR #33).

## How to read this

Status:
- **Done**: built and covered by the evidence listed.
- **Partial**: part of the requirement is built. The gap is named.
- **Not built**: planned for v1.1 (Known_Limitations S-L-009, Pending P-12).

Evidence:
- **API test**: backend test in `backend/tests/screening/test_api.py`, run against Postgres.
- **E2E**: Playwright test in `frontend/psychosocial/e2e/screening.spec.ts`, run at 390 px and 1440 px. E2E 1 is the physio and patient flow, E2E 2 is admin access, E2E 3 is the invalid link, E2E 4 is admin deletion, E2E 5 is the trend chart and PDF download, E2E 6 is repeat and the Due list, E2E 7 is clinic settings and the default repeat, E2E 8 is anonymised statistics and CSV, E2E 9 is the referral contact directory.
- **Report**: `docs/screening/Scoring_Validation_Report.md` (153 checks).
- **UI, not in E2E**: the screen exists and was reviewed by hand, but no automated browser test clicks it. The API behind it is tested.

Last full run, 22 Oct 2026, on this branch: screening backend tests 270 pass, full backend suite 572 pass with the same 10 pre-existing failures (P-09), Playwright 18 of 18 pass, `npm test` 24 of 24 pass, tsc, eslint and `next build` clean.

## Summary

| Status | Requirements |
|---|---|
| Done | 26 |
| Partial | 2 |
| Not built | 2 |
| Total | 30 |

Items marked "pending founder sign-off" work today with a safe default and may change after the founders answer (Decisions.md).

## 4.1 Physiotherapist

### 4.1.1 Screening Management

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Assign one or more screeners (PHQ-9, GAD-7, DASS-21) to a patient from the patient's profile | Done | API test `test_full_flow_phq9_then_gad7` (PHQ-9 and GAD-7 on one link), `test_validation_of_assign_payload`. E2E 1: "Send screener" on the patient page, two screeners on one link. |
| 2 | One-time or recurring assessment at a defined interval | Done | "Repeat" in the send drawer: just once, or every 2, 4, 6, 8 or 12 weeks (S-D-026). A repeat never sends by itself: when it is due again the patient shows in "Due again" and on their page, and the physio sends it with one click. API tests in `test_schedules.py` (`test_schedule_state`, `test_due_after_interval_and_upcoming_before`, `test_cancelled_or_expired_link_makes_it_due_and_a_new_link_waits`, `test_withdrawn_and_removed_patients_are_never_due`, `test_stop_schedule`). E2E 6. |
| 3 | View all pending, in-progress and completed sessions per patient | Done | API test `test_full_flow_phq9_then_gad7` (patient list with status per session). UI, not in E2E: patient page history. Clinic-wide worklist with status filter in E2E 1. |
| 4 | Cancel a pending session the patient has not started | Done | API test `test_cancel_only_before_start` (refused once an answer exists). UI, not in E2E: "Cancel screener" on the patient page. |

### 4.1.2 Results Review

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Completed session shows total score, severity band, every answer and date of completion | Done | API test `test_full_flow_phq9_then_gad7` (score, band, answer labels, unscored difficulty item). E2E 1: score 7, band and the item 9 answer on the result page. The completion date is in the page header. The test does not assert it. |
| 2 | Severity indicator that does not rely on colour alone | Done | E2E 1 finds the severity meter by its text label "Mild, band 2 of 5". |
| 3 | Longitudinal chart of scores across sessions, per instrument | Done | One chart per scale on the patient page (S-D-025): x by date, published bands named on the chart, referral line, readable without colour. API tests `test_trend_api_respects_scope_and_order`, `test_twenty_four_months_of_history` (SRS 3.5). Unit tests in `src/lib/trend.test.ts`. E2E 5. |
| 4 | Compare the current result against the patient's baseline | Done | API test `test_second_session_shows_baseline` (baseline 27, current 8). UI, not in E2E: baseline column on the result page. |

### 4.1.3 Referral Management

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Automatic referral at PHQ-9 >= 10, GAD-7 >= 10, any DASS-21 subscale Severe or above | Done | Report: every possible score on all three instruments. API tests `test_full_flow_phq9_then_gad7`, `test_dass21_severe_subscale_refers`. Extra rule: PHQ-9 item 9 above 0 also refers (S-D-005, pending founder sign-off F1). |
| 2 | Document the referral action taken | Done | API test `test_full_flow_phq9_then_gad7` (action saved, refused on an unflagged session). E2E 1: "Referred to psychologist" with a note. |
| 3 | History of all referral flags and documented actions for a patient | Done | API test `test_full_flow_phq9_then_gad7` (referral action history). UI, not in E2E: flags on each session and a "Referral history" list on the patient page. |

### 4.1.4 Reporting

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Single-patient summary report as PDF: sessions, scores, bands, referral actions | Done | "PDF summary" on the patient page (S-D-025). Rendered on request, streamed to the signed-in user, never stored. API tests `test_report_pdf_download_and_audit`, `test_report_content`. E2E 5 downloads it and checks it is a PDF. |
| 2 | Report suitable for the patient's clinical record | Done | Clinic name, patient details, report ID, date and author, a disclaimer and a signature line, in the posture report style. Reviewed as rendered pages with 28 sessions over 24 months. |

## 4.2 Patient

### 4.2.1 Informed Consent

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Plain-language explanation before the first screener: what is collected, how it is used, who sees it | Done | E2E 1: "Before you start" screen. Text in `backend/app/screening/consent.py`, draft `2026-10-20.draft1`, pending founder sign-off F6. |
| 2 | Active consent required, no screening without it | Done | API test `test_full_flow_phq9_then_gad7` (answer before consent gets `CONSENT_REQUIRED`). E2E 1: "Continue" stays disabled until the box is ticked. |
| 3 | Withdraw consent at any time, which stops future sessions | Done | API test `test_withdraw_consent_cancels_open_and_blocks_new`. UI, not in E2E: withdraw option on the screener page. There is no way back after a withdrawal yet (S-L-006, founder question). |

### 4.2.2 Questionnaire Completion

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Access through a direct link or the patient portal | Partial | Direct link only. AV Suite has no patient portal today. |
| 2 | Response options as in the published instrument | Done | Wording is verbatim (S-D-004). Scoring test `test_published_response_options`. E2E 1 answers by the published option labels. |
| 3 | Progress saved after each question, resume an unfinished session | Done | API test `test_full_flow_phq9_then_gad7` (saved answers come back on reopen). E2E 1 reloads the page at question 5 and resumes there. |
| 4 | A response cannot change after moving past it | Done | API test `test_full_flow_phq9_then_gad7` (`ANSWER_LOCKED`, strict order). The screener has no back button. A Postgres trigger also blocks changes to a submitted session (`test_completed_session_rejects_db_update`). |
| 5 | Confirmation on submit, and a calm message to talk to the physio when referral is flagged | Done | E2E 1: "Thank you", the "may help to talk things through" message, and no score shown. On a risk answer it also shows Tele-MANAS (pending founder sign-off F2). |

### 4.2.3 History Access

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Patient sees own score history if the physio enables it | Not built | v1.1. |
| 2 | Simplified labels (Low, Moderate, High), no clinical wording in the patient view | Not built | v1.1, with item 1. Today the patient never sees a score or a band. |

## 4.3 Clinic Administrator

### 4.3.1 Access Control

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Turn the module on or off for each physio | Done | E2E 2: admin turns off "Send screeners" on the Access page, then the physio's assign call gets 403. API tests `test_therapist_without_grant_is_refused`, `test_product_entitlement_required`. The CRM permission grid does not list the new keys yet (P-08). |
| 2 | Manage referral contacts (name, role, contact details) used when logging referral actions | Done | Settings page, S-D-029. `test_admin_adds_edits_archives_and_restores`, `test_physio_logs_a_referral_to_a_contact` (name and role kept after an edit and an archive, also in the PDF), `test_access_and_clinic_isolation`. E2E 9: admin adds and archives contacts, the physio refers to a listed contact, the history names it. |

### 4.3.2 Configuration

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Clinic-wide default screening interval per instrument | Done | Settings page, S-D-027. `test_admin_sets_default_and_the_assign_form_gets_it`, `test_changing_the_default_leaves_existing_schedules_alone`, `test_only_holders_of_screening_configure_can_configure`. E2E 7: the admin saves defaults, the physio's send drawer starts at the default, and a running repeat is not changed. |
| 2 | Configure referral thresholds, defaults equal to published norms, changes need confirmation | Partial | The Settings page shows the thresholds in force, built from the instrument definitions (`test_threshold_view_agrees_with_the_scoring_engine_at_every_score`, E2E 7). Clinic changes are not built and wait for a founder decision (S-L-015, P-13). |

### 4.3.3 Aggregate Reporting

| # | Requirement | Status | Evidence and notes |
|---|---|---|---|
| 1 | Anonymised clinic statistics: sessions completed, band distribution, referral flag rate | Done | Reports page, S-D-028. Counts from 1 to 4 hidden, plus a second count where needed. `test_admin_gets_suppressed_statistics_never_rows`, `test_no_hidden_cell_can_be_worked_out_from_the_total`, `test_referral_figure`. E2E 8. Admins still cannot open individual results (`test_admin_assigns_but_cannot_read_individual_results`, E2E 2). |
| 2 | Filter by date range and instrument | Done | `test_filters_by_ist_date_range_and_screener` (IST day boundaries), `test_default_range_and_invalid_input`. E2E 8 filters by screener and by a period with no results. |
| 3 | Export aggregates as CSV | Done | `test_csv_matches_the_screen_and_is_audited`: same figures as the screen, hidden cells stay hidden, audited. E2E 8 downloads the file and checks it. |

## Before go-live, outside section 4

- Deletion on request (SRS 3.2): done 22 Oct (S-D-024). The clinic admin deletes a patient's screening data from the patient page. Covered by `backend/tests/screening/test_deletion.py` and the Playwright test "admin deletes a patient's screening data on request".
- Founder answers F1 to F6, re-consent and staff accounts for screening-only clinics (P-03).
- `AV_Suite_Clinical_Reference_v1.xlsx` comparison (P-05).
