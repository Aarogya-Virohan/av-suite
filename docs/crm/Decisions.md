# Decisions.md — The Why Behind Every AI Decision
> **Purpose**: Log the reasoning behind architectural and implementation choices,
> not just what was done. If a future AI or dev asks "why is it like this?"
> the answer is here, not hidden in a git blame.

---

## Decision Log Format

Each entry follows this structure:

```
## [D-NNN] Short Decision Title
- **Date**: YYYY-MM-DD
- **Session / Model**: Claude Sonnet 4.6 (Thinking)
- **Context**: What problem or question triggered this decision
- **Options Considered**: What alternatives existed
- **Decision**: What was chosen
- **Reasoning**: Why this option over others
- **Trade-offs**: What we gave up
- **Affected Files**: Which files were created or changed
```

---

## [D-001] Backend is Shared Across All Tools
- **Date**: 2026-08-13
- **Session / Model**: Claude Sonnet 4.6 (Thinking)
- **Context**: Designing where CRM-specific logic lives vs. shared infrastructure
- **Options Considered**:
  1. Separate backend per tool (CRM backend, Posture backend, Exercise backend)
  2. Single shared FastAPI backend with tagged route modules
- **Decision**: Single shared backend (`backend/app/`)
- **Reasoning**: Reduces infrastructure overhead, enables shared auth/JWT, single DB,
  single deployment. CORS, auth middleware, and DB connection pooling are managed once.
- **Trade-offs**: Changes to `main.py`, `middleware/`, or `models/` affect ALL tools.
  Backend PRs need broader review.
- **Affected Files**: `backend/app/main.py`, `backend/app/api/v1/router.py`

---

## [D-002] CORSMiddleware Added After ClinicGateMiddleware
- **Date**: 2026-08-13
- **Session / Model**: Claude Sonnet 4.6 (Thinking)
- **Context**: FastAPI middleware executes in reverse order of registration (last added = first executed).
- **Options Considered**:
  1. Add CORS first, then ClinicGate → CORS executes second (wrong)
  2. Add ClinicGate first, then CORS → CORS executes first, handles preflight OPTIONS before auth check
- **Decision**: Add `ClinicGateMiddleware` first, `CORSMiddleware` second
- **Reasoning**: `OPTIONS` preflight requests must pass before auth middleware runs.
  If ClinicGate executed first on OPTIONS, it would reject unauthenticated preflight requests,
  breaking the browser's CORS handshake.
- **Trade-offs**: Middleware order is counter-intuitive. Documented in `main.py` docstring.
- **Affected Files**: `backend/app/main.py` lines 60–98

---

## [D-003] No Direct Axios Calls in Components
- **Date**: 2026-08-13
- **Session / Model**: Claude Sonnet 4.6 (Thinking)
- **Context**: Defining the API access pattern for frontend components
- **Options Considered**:
  1. Call `axios.get(...)` directly from `useEffect` inside components
  2. Route all calls through `features/*/api.ts` hooks
- **Decision**: All API access must go through `features/*/api.ts` (option 2)
- **Reasoning**: Centralizes token injection (interceptor in `api-client.ts` handles it),
  error normalization, and cache invalidation. Components stay presentational.
  Changing an endpoint URL means changing one file, not hunting through components.
- **Trade-offs**: Slight indirection. Worth it for maintainability.
- **Affected Files**: `lib/api-client.ts`, all `features/*/api.ts` files

---

## [D-004] Zustand for Auth + UI State Only (Not Server State)
- **Date**: 2026-08-13
- **Session / Model**: Claude Sonnet 4.6 (Thinking)
- **Context**: Choosing what belongs in Zustand vs. TanStack Query
- **Options Considered**:
  1. Store everything (patients, leads, auth) in Zustand
  2. Store server state in TanStack Query, client-only in Zustand
- **Decision**: TanStack Query for all server-fetched data; Zustand for auth claims + UI toggles
- **Reasoning**: TanStack Query has built-in caching, stale-while-revalidate, and background
  refetch. Duplicating server state in Zustand means manual sync — a source of bugs.
  Auth state (`token`, `userId`, `clinicId`, `role`) is not server state — it's derived from
  localStorage and doesn't need automatic refetching.
- **Trade-offs**: Two state systems to understand. The rule is simple: if it comes from the API, use Query; if it's local-only, use Zustand.
- **Affected Files**: `store/index.ts`, all `features/*/api.ts`

---

## [D-005] ClinicGateMiddleware Injects Clinic Context on Every Request
- **Date**: 2026-08-13
- **Session / Model**: Claude Sonnet 4.6 (Thinking)
- **Context**: Multi-tenant data isolation — each clinic's data must be isolated
- **Options Considered**:
  1. Frontend passes `clinic_id` as a request param/header
  2. Backend extracts `clinic_id` from JWT on every request
- **Decision**: Backend always extracts `clinic_id` from JWT (option 2)
- **Reasoning**: Never trust the client to declare its own identity. JWT is signed by the server —
  its claims cannot be forged. `clinic_id` in JWT means every DB query automatically scopes to the
  right clinic without relying on client input.
- **Trade-offs**: Every protected endpoint requires a valid JWT. No anonymous data access.
- **Affected Files**: `backend/app/middleware/clinic_gate.py`, all endpoint files that read `request.state.clinic_id`

---

## [D-006] Static Files (PDFs) Removed from Public Mount
- **Date**: Pre-2026-08-13 (noted in main.py comment)
- **Session / Model**: Unknown prior session
- **Context**: Prescription PDFs contain patient PHI (Protected Health Information)
- **Options Considered**:
  1. Serve PDFs via StaticFiles mount at `/static/*` (unauthenticated)
  2. Serve PDFs via authenticated download endpoint with JWT check
- **Decision**: Authenticated download only: `GET /api/v1/prescriptions/{id}/pdf/download`
- **Reasoning**: HIPAA compliance — PHI must never be served without verifying the requester
  has permission to access that patient's records. A static file mount has no auth.
- **Trade-offs**: Slightly more complex download UX (must use authenticated Axios call, not direct link).
- **Affected Files**: `backend/app/main.py` (comment at line 54), `api/v1/prescriptions.py`

---

## [D-007] Field-Guide Documentation Set Created (This Session)
- **Date**: 2026-08-13
- **Session / Model**: Claude Sonnet 4.6 (Thinking)
- **Context**: User requested 15 documentation files to be the foundation of project intelligence
  for all future AI sessions working on the CRM tool.
- **Options Considered**:
  1. Single long README
  2. 15 focused files in `docs/crm/`, each serving one purpose
- **Decision**: 15 separate files in `docs/crm/` (option 2)
- **Reasoning**: A single file becomes unnavigable. Separate files mean:
  - AI sessions can load only what's relevant
  - Humans can find answers without scrolling
  - Each file has a single clear purpose and update responsibility
- **Trade-offs**: 15 files to keep in sync. Mitigated by: Handover.md protocol to update
  relevant files at session end.
- **Affected Files**: All 15 files in `docs/crm/`

---

## [D-008] No New Mock Data Permitted
- **Date**: 2026-08-13 (from AI_RULES.md)
- **Session / Model**: Formalized from existing AI_RULES.md
- **Context**: Prior sessions may have introduced mock/stub data; real backend now exists
- **Decision**: Remove all mock data. Show Loading / Empty / Error states instead.
- **Reasoning**: Fake data masks real integration bugs. A loading state that never resolves
  is a visible signal that the API is down — fake data silently hides this.
- **Trade-offs**: Components must handle all 3 states (loading, empty, error). More code, but honest.
- **Affected Files**: Any component that previously used `mocks/` directory data

---

*Last updated: 2026-08-21 | Branch: feature/frontend-redesign-impl*
*Add new entries at the bottom with incremented D-NNN index.*

---

## [D-009] Rev3 Capability System Deferred to Phase 2
- **Date**: 2026-08-21
- **Session / Model**: Antigravity (Claude Sonnet 4.6 Thinking)
- **Context**: Rev3 spec requires a `user_permissions` table, capability keys, scope values (`none`/`own`/`all`), and split analytics endpoints. This is substantial backend work.
- **Options Considered**:
  1. Implement `user_permissions` table + capability resolver in this PR
  2. Defer to Phase 2 — merge current PR as Phase 1, then implement Rev3 in a dedicated branch
- **Decision**: Defer to Phase 2 (option 2)
- **Reasoning**: Phase 1 PR is already substantial (migration, auth hardening, API wiring). Adding a new DB table, resolver engine, and two new analytics endpoints would make the PR too large to review safely. The current RBAC system (`PERMISSION_MAP` in `rbac.py`) is functional for all existing routes.
- **Trade-offs**: Analytics page shows same view for admin and therapist in the interim.
- **Affected Files**: Will affect `backend/alembic/versions/`, `backend/app/core/rbac.py`, `backend/app/api/v1/analytics.py`, `frontend/crm/src/features/analytics/api.ts`, `frontend/crm/src/app/(dashboard)/analytics/page.tsx`

---

## [D-010] Zustand `.getState()` Used Outside React in `api-client.ts`
- **Date**: 2026-08-21
- **Session / Model**: Antigravity (Claude Sonnet 4.6 Thinking)
- **Context**: BUG-002 fix requires calling `useAuthStore.logout()` from within the Axios response interceptor, which is outside any React component tree.
- **Options Considered**:
  1. Subscribe to a global event bus and handle logout in a React component
  2. Use Zustand's vanilla `.getState()` API directly in the interceptor
- **Decision**: Use `useAuthStore.getState().logout()` (option 2)
- **Reasoning**: Zustand explicitly supports and documents calling `.getState()` on the store object outside React. This is simpler, has no side effects, and does not require any new infrastructure. No hooks are invoked — `.getState()` is a plain synchronous call on the store module export.
- **Trade-offs**: Slight coupling between `api-client.ts` (lib layer) and `store/index.ts`. Acceptable because auth state management is already centralized in the store by design.
- **Affected Files**: `frontend/crm/src/lib/api-client.ts`, `frontend/crm/src/store/index.ts`

---

## [D-011] Midnight & Grove Brand Theme Applied Through Tokens
- **Date**: 2026-10-11
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: The CRM UI looked generic and did not match the brand. Founders approved the "Midnight & Grove" palette: website midnight blue, green and lime, fused with the logo's cream and teal.
- **Options Considered**:
  1. Restyle every component by hand with new hex values
  2. Remap Tailwind v4 `slate` and `teal` scales plus semantic tokens in `globals.css`, then restyle pages one by one with shared primitives
- **Decision**: Option 2. Tokens live in `@theme` in `app/globals.css`; shared primitives in `components/ui/brand.tsx` (Card, PageHeader, KpiCard, Badge, Button, Avatar, IconChip, Delta).
- **Reasoning**: Every page picks up the palette at once without touching logic. A future palette change happens in one file. Pages are then restyled one at a time with before/after screenshots, keeping queries, permissions, handlers and test-visible text unchanged.
- **Trade-offs**: Pages not yet restyled still use the old layout (with new colours). `--brand-navy` can still be overridden by a clinic's `branding_color`.
- **Affected Files**: `app/globals.css`, `app/layout.tsx`, `lib/cn.ts`, `components/ui/brand.tsx`, `components/layout/*`, restyled pages

---

## [D-012] Hardcoded Pain Scores and WA Session Report Removed (D-008 violation)
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: The patient header showed "Initial Pain 8/10, Current 3/10, 5 pts improved" for every patient, and "WA Session Report" sent those same invented scores, a fixed treatment and fixed home advice to the patient on WhatsApp. Real data exists in `treatment_sessions` (`pain_score`, `treatment`, `home_advice`, `finalized`).
- **Options Considered**:
  1. Compute badges and the report on the client from `GET /treatments`
  2. Remove the fake values now; build both from a backend clinical summary later
- **Decision**: Option 2, in three parts:
  - Part 1 (done, frontend): remove the badges, disable the WA report button with a "coming soon" tooltip, sort sessions by `treatment_date` then `created_at` in the Progression tab.
  - Part 2 (Sparsh, after PR B): `order_by` in `list_sessions`; new `GET /patients/{id}/clinical-summary` counting only finalized sessions (initial/current pain, change, session count, last finalized session), scoped by `treatments.view`, with tests.
  - Part 3 (frontend, after Part 2): header badges and WA report built only from that summary; clinic name instead of hardcoded "Aarogya Virohan"; message opens prefilled in WhatsApp so the therapist reviews it before sending.
- **Reasoning**: Option 1 is unreliable: the list API has no ordering and a default limit of 100, so "initial" can be any session. Showing nothing is safer than showing wrong clinical data. Only finalized sessions should ever reach a patient.
- **Trade-offs**: The WA Session Report feature is unavailable until Parts 2 and 3 land.
- **Verified**: Three sessions inserted out of order (8, 5, 2). Old code showed initial 5, current 8, "-3 pts". New code shows 8 → 2, 6 pts.
- **Affected Files**: `app/(dashboard)/patients/[id]/page.tsx`, `features/patients/components/ProgressionTab.tsx`

---

## [D-013] Pages Must Subscribe to the Auth Store Before Using Permission Helpers
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: `hasCapability`, `canAccessModule` and `canPerformAction` in `config/permissions.ts` read `useAuthStore.getState()`, which never triggers a re-render. While restyling Billing, removing an "unused" `useAuthStore((s) => s.role)` line made admins see "Access Restricted" permanently. The same mechanism made Billing open on the wrong tab: the default tab was frozen into `useState` before capabilities loaded.
- **Options Considered**:
  1. Make the helpers reactive hooks (changes every call site)
  2. Keep helpers as they are; every page that uses them subscribes to `role` and `capabilities`, and never freezes permission results into `useState`
- **Decision**: Option 2 for now, with a comment at each subscription. Option 1 is the cleaner long-term fix (queued, not urgent).
- **Reasoning**: Smallest safe change during the UI freeze; no logic changes to the permission system.
- **Trade-offs**: The subscription line looks unused. Do not delete it.
- **Affected Files**: `app/(dashboard)/billing/page.tsx` (other pages are checked as they are restyled)

---

## [D-014] Hardcoded Therapist Salary Removed; No Payroll Until Real Data Exists
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: The Therapists page showed "Rs 35,000 / mo" for every therapist under "Monthly Salary" and was titled "Therapists Directory & Payroll". The backend has no salary or payroll data. Another D-008 violation, and on compensation data.
- **Decision**: Remove the column; rename the page "Therapists Directory". Payroll is listed as a not-built feature (L-12).
- **Reasoning**: Invented salary figures shown to admins are worse than none.
- **Affected Files**: `app/(dashboard)/therapists/page.tsx`

---

## [D-015] Frontend Types for API Responses Come From the Generated Schema
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: Recycle Bin defined its own interface (`name`, `resource`) while the API returns `title`, `resource_type`. Names showed blank and Restore called `/recycle-bin/undefined/...`. Billing had a similar mismatch (amounts are Decimal strings, code treated them as numbers).
- **Decision**: Pages type API data with `components['schemas'][...]` from `types/schema.ts` instead of hand-written interfaces, so a contract change fails `tsc`.
- **Trade-offs**: `types/schema.ts` must be regenerated when the backend changes.
- **Affected Files**: `app/(dashboard)/recycle-bin/page.tsx` (others as they are touched)

---

## [D-016] Public Booking Links Use the Clinic UUID Until a Real Slug Exists
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: `ClinicRepository.get_by_slug_or_id` resolves a non-UUID slug with `Clinic.name ILIKE '%<slug with spaces>%'` and returns the first row. Verified locally with two clinics, "Sunrise Physio" and "Sunrise Physio Clinic": `/booking/sunrise-physio` opened "Sunrise Physio Clinic". The public page then posted the patient's name, phone and complaint to that clinic, and showed a name built from the URL, so the patient could not tell. Separately, `POST /booking/request?clinic_slug=` calls `clinic_repository.get_by_slug`, which does not exist (HTTP 500). `clinics` has no slug column.
- **Options Considered**:
  1. Keep name slugs and wait for a backend fix
  2. Frontend now: link by clinic UUID (exact match through `get_by_slug_or_id`); public page verifies the clinic on load and shows the server's name. Backend later: unique `clinics.slug`, exact lookup, fix or remove the slug POST path.
- **Decision**: Option 2. The frontend part is done (commit a8d37c2).
- **Reasoning**: A UUID cannot match another clinic, so the leak path is closed without waiting on the backend. Nothing is deployed, so no name-based links exist in the wild.
- **Trade-offs**: Booking URLs are long until the backend slug exists. The fuzzy lookup still exists server-side (anyone typing a word gets some clinic's page), so the backend fix is still required before launch.
- **Affected Files**: `app/(dashboard)/appointments/page.tsx`, `app/(public)/booking/[clinicSlug]/page.tsx`; backend: `repositories/clinic.py`, `services/booking.py`, `models/clinic.py`
- **Status (2026-10-17)**: Retired. The backend now has a unique `clinics.slug` with exact lookup and sends it in `/auth/me`, so the booking link uses the slug. The UUID is still accepted, so links already shared keep working.

---

## [D-017] All Form Dates and Times Go Through lib/datetime.ts
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: Verified with the browser in Asia/Kolkata: Add Appointment sent `datetime-local` values without a zone, so 10:00 am was stored as 10:00 UTC and shown as 3:30 pm. Treatment sessions had the same bug. Defaults came from `toISOString()` (UTC), so forms showed yesterday or a time 5h30m behind before 5:30 am IST.
- **Decision**: Prefill with `localToday()` / `toLocalDateTimeInput()`; send with `localDateTimeInputToISO()`. Never use `toISOString().slice(...)` for form defaults. Date-only payment dates are sent at "now" for today, otherwise noon local.
- **Reasoning**: One tested place for time zone handling (`lib/datetime.test.ts` runs in IST, so a regression fails CI).
- **Affected Files**: `lib/datetime.ts`, appointment drawers, `TreatmentsTab.tsx`, billing drawers, public booking

---

## [D-018] Forms Never Invent Values
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: Forms prefilled values that were saved as if the user chose them: gender "male" and referral "Direct Walk-in" (Edit Patient even overwrote blanks on a plain save, verified), lead source "website", treatment pain 5, payment Rs 1,000, invoice line "Physical Therapy Session Rs 1,000", first patient/therapist/invoice in a list (which also broke submits because the lists loaded later).
- **Decision**: Optional fields start blank and are sent as `null`; required choices start on a "Select ..." option and show an error; numeric clinical or money fields start empty, except where a real value exists (payment amount defaults to the invoice's actual balance due). Every field that can fail validation renders its error.
- **Reasoning**: An invented default becomes clinical or financial data the moment someone clicks Save.
- **Affected Files**: all drawers under `features/*/components/*SlideOver.tsx`, `TreatmentsTab.tsx`, `lib/schemas/index.ts`

---

## [D-019] Finalized SOAP Notes Are Immutable; Corrections Go in a New Note
- **Date**: 2026-10-12
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: The SOAP tab offered "Re-open (Admin Only)", but `update_assessment` rejects any change to a finalized note, so it always failed. The tab also claimed autosave that did not exist, read `finalized_at` (never returned), and never saved pain VAS.
- **Decision**: Keep the backend rule (finalized notes cannot be edited), which matches medico-legal practice. The tab has Save draft, Finalize (with confirmation), a note list and New note. Pain VAS and clinical area are stored in `form_data` (`pain_vas`, `area`) because the DB enum lacks the area values (L-25).
- **Affected Files**: `features/patients/components/SoapNotesTab.tsx`, `types/api.ts`

---

## [D-020] Accounts in Several Clinics Choose a Workspace at Login and Can Switch
- **Date**: 2026-10-17
- **Session / Model**: Claude (Claude Code session, reviewed by Onkar)
- **Context**: With membership auth (#26 merged into `integration/crm-merge`), an account can belong to more than one clinic. Login without a clinic then returns 400 with `detail = {code: "WORKSPACE_SELECTION_REQUIRED", message, workspaces: [{clinic_id, name, role}]}`. The login page showed only "Request failed with status code 400", so such a user could not sign in.
- **Decision**: The API client reads structured `detail` objects (message and code). The login page shows the workspaces from that error and signs in again with the chosen `clinic_id`. The top bar lists the account's workspaces from `GET /api/v1/me` and switches through `POST /auth/switch-workspace`; after a switch the app does a full reload to /dashboard so no cached data from the previous clinic stays in memory. Accounts with one clinic see the same plain clinic name as before.
- **Trade-offs**: The password stays in the login form state while the picker is shown (it is needed to sign in again with the clinic). The top bar shows the plain name until `/me` loads, then the switcher.
- **Affected Files**: `lib/api-client.ts`, `lib/workspaces.ts`, `app/login/page.tsx`, `components/layout/WorkspaceSwitcher.tsx`, `components/layout/AppShell.tsx`

---

## [D-021] Exercise Library Redesigned to the AV Suite Brand; Prescription PDF Rebuilt

- **Date**: 2026-10-20
- **Context**: The Exercise Library still had the old look (dark serif login, shadcn defaults, no logo; the Geist font never loaded because `--font-sans` pointed at itself). Body part chips needed a second click on "Apply Filters". Login showed "[object Object]" for structured errors and accounts in two clinics could not sign in. The prescription PDF took about 18 s and 2.8 MB live: WeasyPrint downloaded every exercise image one after another at full size, inside the async route, blocking the server. The file sat on Railway's local disk (wiped on every redeploy), and the WhatsApp text carried a login-only relative download path.
- **Decision** (scope and the four product answers by Onkar, 20 Oct):
  - Frontend `frontend/exercise-library`: CRM tokens and fonts (copied from `frontend/crm/src/app/globals.css` at 6195026), AV logo, CRM-style login with the workspace picker, header with clinic and user, chips filter on click (multi-select, "All" clears), search debounced with stale requests aborted, image thumbnails on cards, searchable patient picker, previous prescriptions of a patient can be opened and edited, one primary action "Save & download PDF" (direct download, proper file name), toasts instead of `alert()`, phone layout with Library / Prescription tabs. The unused browser print view (`A4PrintView`, never reachable) and unused shadcn components were removed.
  - Frontend fixes found on the way: the Frequency select had no "Daily" (the default) and showed blank; number fields clamped on every keystroke so a value could not be cleared and retyped.
  - Backend: new `services/prescription_pdf.py` on the posture report's brand system (helpers imported, posture module untouched). Images fetched in parallel (https and public hosts only, 6 s timeout, 8 MB cap), shrunk with Pillow, cached, embedded as data URIs. Render in a worker thread. Stored in the `documents` bucket under `prescriptions/<clinic_id>/<rx_id>.pdf`; local disk only as fallback; the download regenerates a missing file instead of 404 and sends `Rx_<Patient>_<date>.pdf`. Dates in IST.
  - WhatsApp text has no link; the physiotherapist attaches the PDF. A public or signed link would put health data on an open URL.
- **Trade-offs**: API shapes unchanged except an added `filename` in the POST `/pdf` response. A PDF is regenerated on every download click (cheap now). Thumbnails load straight from the image host in the browser.
- **Verified**: backend suite 309 pass, the same 10 known environment failures as before (302 + 7 new PDF tests). Exercise Library `tsc`, `eslint` (0 problems, 15 before) and `next build` clean. Playwright end to end at 1440 and 390 px against a local backend: picker login, chips, search, add, dosage edits, save, download, edit and save again, reopen from history, add-patient validation, logout; no page errors and no failing API calls. Not verified in the sandbox: exercise images (the image host is blocked there), so live PDF time with images is still to be measured.
- **Affected Files**: `frontend/exercise-library/**`, `backend/app/services/prescription_pdf.py`, `backend/app/services/prescription_service.py`, `backend/app/api/v1/prescriptions.py`, `backend/tests/test_prescription_pdf.py`, `backend/tests/test_whatsapp_click_to_chat.py`

---

## [D-022] Founder Feedback Phase 0 (23 Oct): CRM Quick Fixes

- **Date**: 2026-10-23
- **Context**: Shivank's feedback of 23 Oct (list + 8 annotated screenshots). Analysis per item is in the CRM Project doc `feedback-crm-23Oct2026.md` (IDs C-01 to C-27, own findings X-1 to X-3). This batch is the frontend-only part that needed no founder decision.
- **Decision**:
  - C-01: the header date opens a month calendar; picking a day opens `/appointments?date=YYYY-MM-DD`, filtered by the local (IST) day on the client because the backend `date` filter uses UTC days. "Book Visit" prefills that day (future days at 10:00). Users without Appointments access keep the plain date.
  - C-03: hover states only where something is clickable. Read-only table rows and lead kanban cards no longer change on hover.
  - C-05: referral source is a dropdown (Google search, AI search, Walk-in, Friend or family, Doctor referral, Previous treatment, Practo / Justdial / other app, Social media, Other with free text). The column stays free text; an old value not in the list opens as Other with its text, so nothing saved is lost.
  - C-06: SOAP Notes and Assessments were the same component on the same table shown twice. They are one tab, "SOAP & Assessments", with an All / Initial / Re-assessment filter, a type badge per note, and a note type choice on unfinalized notes. A patient's first note defaults to Initial, later ones to Re-assessment. Tab name still to be confirmed by founders.
  - C-09: Leads page title "Patient Leads" (sidebar label unchanged).
  - C-12: opening an invoice or receipt adds a browser history entry, so Back closes the preview instead of leaving Billing. Next's own history state is copied into the entry, otherwise the App Router reloads the page on popstate. Reproduced before the fix (Back went from the receipt to /leads).
  - C-13: the preview modal is top-aligned and scrolls, with a sticky toolbar (Print and Close). Before, a centred flex box put the Close button above the screen (y = -195 px at 1366x720) with no way to reach it.
  - C-17: invoice line label "Sessions / Qty".
  - C-18: the transaction reference field is hidden and cleared for Cash.
  - C-27: rows per page (5, 10, 25, 50, 75) on every DataTable; the Patients list sends `page_size` to the API.
  - X-1: Lost leads have no Convert button.
  - X-2: Analytics no longer shows developer text ("UTC range ... (end exclusive)", "not persisted by the backend"); it shows the date range in words and says expenses are not recorded yet.
  - Found on the way: Appointments requested only 10 rows with no paging, so later appointments never showed. It now requests 500, the backend maximum (L-39).
- **Not in this batch**: C-14 / X-3 (test data cleanup, Onkar), C-19 onwards and everything needing founders or backend.
- **Verified**: `tsc` clean, vitest 25 pass (2 new for the referral field), `next build` clean; Playwright on the production build against a local backend and Postgres, desktop 1366 px with time zone Asia/Kolkata, checked every item above plus the DB rows for a new re-assessment; no page errors; only failing call is the expected Rx 403 for a clinic without the Rx entitlement. Phone width screenshots taken; the CRM layout itself is not phone-ready (sidebar stays open), unchanged by this batch.
- **Affected Files**: `frontend/crm/src/components/layout/{AppShell,HeaderCalendar}.tsx`, `components/ui/DataTable.tsx`, `app/(dashboard)/{appointments,billing,leads,analytics,patients}/page.tsx`, `app/(dashboard)/patients/[id]/page.tsx`, `features/patients/components/{SoapNotesTab,PatientFormFields,ReferralSourceField,AddPatientSlideOver,EditPatientSlideOver}.tsx`, `features/patients/referral-source.test.tsx`, `features/billing/components/{InvoicePreviewModal,RecordPaymentSlideOver,CreateInvoiceSlideOver}.tsx`, `features/appointments/components/AddAppointmentSlideOver.tsx`

---

## Known Limitations and Deferred Questions
> Keep this list current. Remove an item only when it is resolved, and note where.

| # | Item | Status | Owner |
|---|---|---|---|
| L-1 | Treatment list API has no `order_by`; with the default limit of 100, older sessions may be skipped | Open, queued (D-012 Part 2) | Sparsh |
| L-2 | WA Session Report disabled until the clinical summary endpoint exists | Open (D-012 Part 3) | Frontend |
| L-3 | Prescriptions return 403 for CRM-only clinics; is Rx part of CRM or a separate tool? | **Deferred**: Onkar to discuss with founders. Onkar leans to "separate tool". | Onkar + founders |
| L-4 | Patient consent (DPDP) before sending clinical info (pain, treatment) on WhatsApp | **Deferred**: founders to decide, must be settled before launch | Onkar + founders |
| L-5 | Role templates are deny-all, contradicting the founders' 13 Aug decision | Open, queued after PR B | Sparsh |
| L-6 | Auth still reads `users.clinic_id`; no workspace switch; membership auth incomplete | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): login uses memberships; more than one membership returns `WORKSPACE_SELECTION_REQUIRED` with the workspace list; `POST /auth/switch-workspace` issues a token for another clinic. Frontend: login shows a workspace picker and the top bar switches workspace (D-020) | - |
| L-7 | Frontend lint config is broken (pre-existing) | Open | Unassigned |
| L-8 | Billing resolves patient names from only the first 100 patients; others show a short reference | Open; fix with patient name in the invoice/payment API response | Sparsh (later) |
| L-9 | "Create Invoice" and "Record Payment" buttons showed for every role | Fixed 2026-10-12: hidden without `invoices.create` / `payments.record` (verified with a front desk user given view-only billing overrides) | Frontend |
| L-10 | Permission helpers are not reactive (see D-013); long-term, convert to hooks | Open, low priority | Frontend |
| L-11 | Recycle bin `deleted_by` is always null: the backend does not record who deleted an item | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): patients and leads record `deleted_by`, and the recycle bin shows it | - |
| L-12 | Payroll / salary is not built (fake column removed, D-014) | Product decision needed before building | Onkar + founders |
| L-13 | Pages that are only correct when reached via the sidebar: fixed for Leads, Therapists, Recycle Bin, Billing, then Patients, patient workspace, Appointments and the sidebar after a therapist test (D-013). All 9 pages pass a direct-load check as admin and as a therapist with overrides (2026-10-12) | Resolved | - |
| L-14 | Clinic address, phone, lead doctor and registration no. are not stored (the fake Settings fields were removed). Invoices and prescriptions will need them | Open; add clinic profile fields | Sparsh (later), then frontend |
| L-15 | Audit log is incomplete. `log_event` covers patient create/update/delete, user permission grant/revoke and delete, clinic settings updates and marketplace actions. Leads, appointments, invoices, payments and user creation are not audited | Open; needed for a healthcare CRM (follow-up PR) | Sparsh |
| L-16 | Booking slug: fuzzy clinic-name lookup and a missing `get_by_slug` (D-016) | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): unique `clinics.slug`, exact lookup (a partial name returns 404), slug in `/auth/me`. Frontend links by slug (D-016 retired) | - |
| L-17 | Public booking services and time slots are a fixed list, not configured per clinic | Open, product decision | Onkar + founders |
| L-18 | Prescription PDF fell back to "Aarogya-Virohan Clinic" when the clinic is missing (`prescription_service.py`) | Fixed 2026-10-20 (D-021): the clinic name comes from the prescription's clinic; "AV Clinic" (the posture report's fallback) only if that row is missing | - |
| L-19 | Appointments have no type column; the drawer's "Appointment Type" was silently dropped and was removed | Open, product decision (add a column if needed) | Onkar + Sparsh |
| L-20 | No overpayment check in `record_payment`: paid_amount can exceed total | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): a payment above the balance is rejected (600 of 1000 accepted, then 500 rejected, 400 accepted, then 0.01 rejected) | - |
| L-21 | Backend required a client-sent `invoice_number` with no uniqueness | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): backend numbers invoices per clinic (INV-0001, INV-0002, ...), unique per clinic, safe under concurrent requests, client value ignored. Frontend number field removed; the created number is shown | - |
| L-22 | `POST /users` created no `memberships` row | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): user creation creates a membership, an existing email gets a membership in the new clinic, and migration a8c4e2f1d903 backfills users without one | - |
| L-23 | Permissions drawer shows "none" for capabilities without an override (ignores the role template) and saves explicit "none" for all of them (PUT replaces all). Harmless while templates are deny-all; would wipe template access once templates are restored | Fix together with role templates: backend returns effective scopes, drawer sends only real overrides | Sparsh + frontend |
| L-24 | "Today" and appointment date filters use UTC day boundaries; between 00:00 and 05:30 IST the dashboard shows the previous day | Open; add clinic time zone (default Asia/Kolkata) | Sparsh (later) |
| L-25 | DB enum `specialty_type` lacked ortho/neuro/cardiopulm/sports/paeds/general, so saving them returned 500 | Backend fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it) (12 enum values, all save). Frontend still stores pain area in `form_data.area`; moving it into `specialty` is open | Frontend |
| L-26 | `types/schema.ts` is stale (e.g. SoapAssessment lacks `finalized`) | Open; regenerate from the backend OpenAPI | Frontend |
| L-27 | Auto-Rx creates a prescription with empty items and the note "Auto-generated prescription." (invented content on a clinical document), and the button shows even for users without prescription permissions. Not changed because Rx scope is parked with founders | Decide with Rx scope | Onkar + founders |
| L-28 | Document storage errors reached users as raw text (e.g. "[Errno 111] Connection refused") | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): storage failures return 503 "Document storage is temporarily unavailable." | - |
| L-29 | For non-admin roles every page called `GET /settings/clinic` and `GET /patients` and got 403 | Frontend part fixed 2026-10-12: settings are read only with `settings.view` (name/logo/colour/booking link come from `/auth/me`), patient lookups only with `patients.view` and only while a search or form is open. Verified: front desk dashboard and billing make no 403 calls | Frontend |
| L-30 | A newly registered clinic gets only the CRM entitlement, so Rx calls return 403 `PRODUCT_NOT_ENTITLED`; the tab was empty, Auto-Rx failed, and the console showed "{}" because the client ignored the `meta.error` envelope. Receipts had no payment details and showed a due date | Fixed 2026-10-12: client reads `meta.error` (message + code), Rx tab and Auto-Rx say "not enabled for this clinic" (no retry), receipt lists each payment (date, mode, reference, amount) and drops "Due". 403s are logged as warnings | Frontend |
| L-31 | Recycle Bin returned 500 once a patient was soft-deleted (`patients.deleted_by` did not exist) | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): column added; recycle bin lists deleted patients and restore works | - |
| L-32 | `patient_service.py` never filtered `deleted_at` | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): deleted patients are hidden from the list and search, and GET and PATCH by id return 404 | - |
| L-33 | `GET /patients` had no status filter, so the Patients page filtered only the loaded page | Fixed 2026-10-17 in `integration/crm-merge` 8665504 (verified by running it): `?status=` on the API (invalid value returns 422); the Patients page sends it and resets to page 1 | - |
| L-34 | Exercise Library: an account in several clinics picks the clinic at login, but there is no switcher after that (sign out to change) | Open; comes with the marketplace SSO phase | Frontend |
| L-35 | Exercise Library loads at most 100 exercises and 100 patients per request (`page_size=100`), and the body part chips come from the first unfiltered load. Fine for today's library (13 exercises), wrong once it grows | Open; add paging or a body part list endpoint before the library passes 100 | Frontend + backend |
| L-36 | Prescription PDF letterhead shows the clinic name with initials; the clinic logo and contact details are not printed (no clinic profile fields yet, see L-14) | Open | Frontend + Sparsh |
| L-37 | "Therapist guidance" on a prescription is the fixed default text from the builder; there is no field to write it | Open, product decision | Onkar |
| L-38 | Exercise images are cached in the server's memory only; the first PDF after a deploy downloads them again (parallel, 6 s cap). An image that fails prints "Image not available" | Accepted for now; move images into our own storage with the exercise image pipeline | Backend |
| L-39 | Appointments loads at most 500 appointments in one request (backend maximum) and has no paging; the backend has no `order_by` and its `date` filter uses UTC days, so the day filter runs on the client | Open; backend paging, ordering and a local-day filter | Backend + frontend |
| L-40 | Leads list loads every lead in one request and has no rows-per-page or paging (it is not a DataTable) | Open; fine at today's volume | Frontend |

*Last updated: 2026-10-23 (D-022, L-39, L-40 added) | Branch: feat/crm-feedback-phase0*
