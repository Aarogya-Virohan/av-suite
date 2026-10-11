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

## Known Limitations and Deferred Questions
> Keep this list current. Remove an item only when it is resolved, and note where.

| # | Item | Status | Owner |
|---|---|---|---|
| L-1 | Treatment list API has no `order_by`; with the default limit of 100, older sessions may be skipped | Open, queued (D-012 Part 2) | Sparsh |
| L-2 | WA Session Report disabled until the clinical summary endpoint exists | Open (D-012 Part 3) | Frontend |
| L-3 | Prescriptions return 403 for CRM-only clinics; is Rx part of CRM or a separate tool? | **Deferred**: Onkar to discuss with founders. Onkar leans to "separate tool". | Onkar + founders |
| L-4 | Patient consent (DPDP) before sending clinical info (pain, treatment) on WhatsApp | **Deferred**: founders to decide, must be settled before launch | Onkar + founders |
| L-5 | Role templates are deny-all, contradicting the founders' 13 Aug decision | Open, queued after PR B | Sparsh |
| L-6 | Auth still reads `users.clinic_id`; no workspace switch; membership auth incomplete | In progress (PR B) | Sparsh |
| L-7 | Frontend lint config is broken (pre-existing) | Open | Unassigned |

*Last updated: 2026-10-12 | Branch: feat/crm-ui-theme*
