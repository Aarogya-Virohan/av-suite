# Tool 03 Psycho-Social Screening: Review Points

One place to see what was decided and what must be looked at again, and when. Details stay in Decisions.md (S-D), Known_Limitations.md (S-L) and Pending.md (P). This file links to them and does not repeat them. Update it in the same commit as any new decision or limitation.

Last updated: 22 Oct 2026 (S-D-029).

## 1. Decision index

Status: **Onkar** = decided by Onkar. **Founders** = built as a safe default, waiting for the founders' answer (rewire map in Pending.md). **Sign-off** = proposal, waiting for Onkar's sign-off (P-07). **Fact** = verified, nothing to decide.

| ID | Decision | Status |
|---|---|---|
| S-D-001 | Branch from `dev` at 770bc875 | Onkar |
| S-D-002 | Reuse product key `psycho-social-screening` | Sign-off |
| S-D-003 | Pure, versioned scoring engine in `backend/app/screening/` | Onkar |
| S-D-004 | Published instrument wording, one DASS-21 instruction adapted for screens | Sign-off |
| S-D-005 | PHQ-9 item 9 above 0 sets the risk flag and forces referral | Founders (F1) |
| S-D-006 | Difficulty question kept, not scored | Sign-off |
| S-D-007 | DASS-21 fully scored and validated | Onkar |
| S-D-008 | Lowest PHQ-9 and GAD-7 band labelled "None-minimal" | Sign-off |
| S-D-009 | Patients are not product-gated | Fact |
| S-D-010 | One link, one session per screener, token stored only as a hash | Sign-off |
| S-D-011 | Capabilities; admin sees no individual results | Founders (F3) |
| S-D-012 | No entitlement granted by migration | Sign-off |
| S-D-013 | Completed sessions immutable, also in the database | Sign-off |
| S-D-014 | Staff API shape | Sign-off |
| S-D-015 | Audit events carry no clinical values | Sign-off |
| S-D-016 | Consent text draft `2026-10-20.draft1` | Founders (F6) |
| S-D-017 | Risk answer visible to the physio before submit | Founders (with F1) |
| S-D-018 | Public screener routes, in-process rate limits, client IP header | Onkar (header choice: Sign-off) |
| S-D-019 | Standalone app `frontend/psychosocial` on the CRM theme | Onkar |
| S-D-020 | Frontend tooling versions (vitest 3, Node types 22) | Sign-off |
| S-D-021 | Patient screener behaviour and wording | Founders (F2 wording) |
| S-D-022 | Validation report generated from the tests | Sign-off |
| S-D-023 | App icon and vitest scope fixes | Sign-off |
| S-D-024 | Deletion on request by the clinic admin | Onkar (admin only), rest Sign-off |
| S-D-025 | Score trend and PDF summary, never stored | Sign-off |
| S-D-026 | Repeat schedules with a Due list, no scheduler | Onkar (no scheduler), rest Sign-off |
| S-D-027 | Default repeat per screener; thresholds read-only | Onkar (scope), rest Sign-off |
| S-D-028 | Anonymised statistics with a minimum cell of 5 | Onkar (minimum 5), rest Sign-off |
| S-D-029 | Referral contact directory; contacts archived, never deleted; name and role copied onto each referral | Sign-off |

## 2. Before merge and deploy

Nothing here is optional for the first deploy. Work through it in order.

| # | Point | Source | Owner |
|---|---|---|---|
| 1 | Set `SCREENER_CLIENT_IP_HEADER=X-Real-IP` on Railway | P-04, S-D-018 | Onkar |
| 2 | Before migrating, check the target database: `alembic current` must show a revision from `dev`, and `\dt` and `\dT` must match it. A stale revision stamp on an empty database made a local upgrade fail on 22 Oct. Then run `alembic upgrade head`; it must end at `e7a1c4b9d2f6` (four Tool 03 migrations). Nothing in the repo runs migrations on deploy, so confirm how the CRM Project applies them. | PR #33 | Onkar |
| 3 | Create the Vercel project for `frontend/psychosocial` and add its origin to `CORS_ORIGINS` | P-01, P-11 | Onkar |
| 4 | Re-check the merge with the latest `dev`: no conflicts, a single Alembic head, the same 10 pre-existing failures | PR #33 | Us |
| 5 | Install `psycho-social-screening` for the pilot clinic only | S-D-012 | Onkar |
| 6 | Founders approve the consent text at least for the pilot (our recommendation: approve for pilot, legal check before a wider launch) | F6, S-D-016 | Founders |
| 7 | Founders answer F1 (item 9) or explicitly accept the built default for the pilot | F1, S-D-005 | Founders |
| 8 | Onkar signs off the "Sign-off" rows in section 1 | P-07 | Onkar |
| 9 | Decide who creates staff logins for the pilot clinic | Q8, S-L-010 | Founders |
| 10 | Read the `npm ci` audit report (9 findings in an earlier run, not investigated). Report only, never `npm audit fix --force`. | Tracker | Us |
| 11 | Compare thresholds with `AV_Suite_Clinical_Reference_v1.xlsx` once uploaded; published norms win | P-05, S-L-003 | Onkar, then us |

## 3. After deploy, during the pilot

Look at these with real use, not before.

| # | Point | Source |
|---|---|---|
| 1 | Check that the screener rate limiter sees real client IPs on Railway (not the proxy's), by reading the request logs after a few patient sessions | S-D-018, P-04 |
| 2 | Check how long Railway and Vercel keep request logs, since link tokens appear in URLs | S-L-004 |
| 3 | Do physios notice due screeners without a notification? Decide on an email with no clinical detail together with F4 | S-L-014, F4 |
| 4 | Is the "Just once" wording clear when a screener already repeats? | S-L-016 |
| 5 | Statistics: with real volumes, is a minimum cell of 5 enough, and does the whole-group-in-one-band case happen? | S-D-028, S-L-017 |
| 6 | Admin cannot see or cancel links they sent; admin can self-grant `screening.view` (audited) | S-L-007, S-L-008, F3 |
| 7 | Patients in the CRM recycle bin cannot have their screening data deleted | S-L-011 |
| 8 | Audit events stay after a deletion; confirm this with the DPDP legal review | S-L-012, F6 |
| 9 | PDF and CSV file names are built in the browser; expose Content-Disposition when the CRM Project next changes CORS | S-L-013 |
| 10 | Re-consent after a withdrawal | S-L-006, Q7 |
| 11 | CRM permission grid lacks the six screening keys | P-08 |

## 4. Before scale (more clinics, more replicas, more data)

Fine at pilot size. Each one needs work before Tool 03 runs at scale.

| # | Point | Source |
|---|---|---|
| 1 | The rate limiter is per process; with more than one replica, move the counters to a shared store (Redis or Postgres) | S-L-001 |
| 2 | Column-level encryption needs a key-management decision; today it is disk encryption plus HTTPS | S-L-002 |
| 3 | Statistics are counted in Python per request; move to SQL GROUP BY with an index on `(clinic_id, status, completed_at)` | S-L-018 |
| 4 | The Due list and patient schedules are evaluated per request; measure the query cost with real numbers of schedules | S-D-026 |
| 5 | The PDF renders in a worker thread inside the API process; with heavy use, move rendering to a queue or a separate worker | S-D-025 |
| 6 | Shared `get_client_ip()` used by public booking trusts spoofable headers (CRM Project) | P-10 |
| 7 | Staff accounts for screening-only clinics without the CRM | S-L-010 |
| 8 | Clinic-editable referral thresholds, if the founders allow them | P-13, S-L-015 |
| 9 | The 10 pre-existing backend failures and the enum drift on `dev` (CRM Project) | P-09 |
