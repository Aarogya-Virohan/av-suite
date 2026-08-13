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

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
*Add new entries at the bottom with incremented D-NNN index.*
