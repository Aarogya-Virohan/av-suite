# AV Suite CRM — Tarun's Master 100-Step Execution Guide & Codebase Architecture Map

> **Author**: Tarun Sisodia  
> **Role**: Frontend & Full-Stack Engineer  
> **Branch**: `feature/frontend-redesign-impl`  
> **Context**: Complete Codebase Audit, Backend Architecture Manual, Sparsh vs Tarun Migration Linearization & Onkar Review Fixes  
> **Last Updated**: 2026-08-21 (updated by Antigravity cross-verification session)

---

## 1. Executive Summary & Codebase Intelligence

### What Happened & Current Status:
1. **Frontend Modernization**: Migrated the CRM frontend from single-page tabs into real Next.js App Router routed pages under `(dashboard)/` (`/dashboard`, `/patients`, `/appointments`, `/leads`, `/billing`, `/analytics`, `/therapists`, `/settings`, `/recycle-bin`).
2. **Real Authentication & Security**: Dropped mock credential encryption, wired standard JWT login, centralized token storage under `NEXT_PUBLIC_API_URL`, hardened RBAC with fail-closed checks on `null` role, and introduced `<AccessRestricted />`.
3. **Backend Scope Update (Rev 3 from Onkar)**: Transitioning from rigid role checks to **per-user capability overrides** with scopes (`none`, `own`, `all`), splitting analytics into `/analytics/my-performance` vs `/analytics/clinic-financials`, and linearizing Alembic heads.
4. **The Migration Issue**: Sparsh's branch (`fix/backend-analytics-whatsapp` / PR #16, revision `d8a9f0c1b2e3`) and your branch (`feature/frontend-redesign-impl`, revision `e9f1a2b3c4d5`) both chained from parent `c5d8e9f4a1b2`.

---

## 2. Deep Dive: Backend Codebase Map (Every Module & Role)

Below is the manually verified architecture map of the backend layers:

### A. Core & Infrastructure (`backend/app/core/`, `backend/app/middleware/`)
- `main.py`: ASGI entry point. Registers `BaseAppException` handler, `ClinicGateMiddleware` (JWT verification and multi-tenant clinic scoping), and `CORSMiddleware`.
- `core/config.py`: Single source of truth for settings, Supabase URL/keys, database pooling, JWT secrets.
- `core/database.py`: SQLAlchemy async engine and session generator (`get_db`).
- `core/security.py`: Password hashing (bcrypt), JWT creation, JWT decoding with claims extraction (`sub`, `clinic_id`, `role`, `exp`).
- `core/rbac.py`: Centralized `PERMISSION_MAP` defining which roles can access each resource domain.
- `core/dependencies.py`: FastAPI `Depends()` factories (`get_authenticated_context`, `get_current_user`, `get_current_clinic`, `require_roles`, `require_permission`). ✅ Duplicate `require_roles` (sync, lines 55-64) removed 2026-08-21.
- `middleware/clinic_gate.py`: Intercepts all requests, skips `PUBLIC_PATHS` (`/health`, `/docs`, `/api/v1/auth/*`, `/api/v1/booking/*`), validates JWT for protected paths, and injects `request.state.clinic_id`, `user_id`, `role`.

### B. Routers & API Contracts (`backend/app/api/v1/`)
- `router.py`: Aggregates all submodule routers under `/api/v1`.
- `auth.py`: Login, register, token refresh, logout endpoints.
- `patients.py`: Patient CRUD, search, clinic-filtered listings.
- `appointments.py`: Scheduling, rescheduling, cancellation, status transitions.
- `treatments.py`: Physical therapy treatment logs, pain scores, therapist-scoped filtering.
- `assessments.py`: Clinical SOAP notes, assessments, therapist assignment, note finalization.
- `billing.py`: Invoices, line items, payments logging, package catalog.
- `booking.py`: Public clinic booking endpoints, appointment request intake.
- `leads.py`: Lead pipeline management, stage transitions (`new` → `contacted` → `qualified` → `converted`), lead conversion to patient.
- `documents.py`: Patient document metadata, categorized storage, secure authenticated download redirect.
- `analytics.py`: ✅ Split done (2026-08-21): `GET /analytics/overview` (admin-only clinic financials) + `GET /analytics/my-performance` (therapist own-only stats). Per RBAC Spec §4 + Rev3 scope.
- `users.py`: Clinic user directory and staff registration (admin only).
- `settings.py`: Clinic branding colors, logo URL, clinic details.
- `recycle_bin.py`: Soft-deleted records retrieval and restoration.
- `audit.py`: System audit trails.
- `exercises.py` & `posture.py`: Shared suite modules for exercise prescriptions and AI posture analysis.

### C. Models, Services & Repositories (`backend/app/models/`, `services/`, `repositories/`)
- `models/`: SQLAlchemy ORM definitions for `Clinic`, `User`, `Patient`, `Appointment`, `Lead`, `TreatmentSession`, `SoapAssessment`, `Invoice`, `Payment`, `Package`, `PatientDocument`, `AuditLog`.
- `repositories/`: Clean async queries scoped by `clinic_id` (e.g. `PatientRepository`, `TreatmentSessionRepository`, `AppointmentRepository`, `BillingRepository`, `UserRepository`).
- `services/`: Business validation, state machines, transactions (e.g. converting lead creates patient atomically).

---

## 3. Sparsh vs Tarun: Migration Comparison & Linearization

```
                          c5d8e9f4a1b2 (Base Head)
                                   │
                                   ▼
         d8a9f0c1b2e3 (Sparsh: seed_demo_login_data.py)
         - Seeds Demo Clinic, Admin, Front Desk, Therapist, Lead, Patients
                                   │
                                   ▼
         e9f1a2b3c4d5 (Tarun: crm_schema_v2.py) [UPDATED]
         - Adds therapist_id & finalized on soap_assessments / treatments
         - Adds appointment_type on appointments
         - Adds payment_status ENUM + idempotency_key on payments
         - Adds gender_type, specialty_type, lead_source_type ENUMs
         - Adds pain_score CHECK constraint (0-10)
         - Tightens users.role CHECK to exclude 'patient'
         - REMOVED date_of_birth from patients (per Onkar review)
```

### Why and How We Fix It:
1. **Sparsh's migration runs first**: `backend/alembic/versions/d8a9f0c1b2e3_seed_demo_login_data.py` keeps `down_revision = "c5d8e9f4a1b2"`.
2. **Your migration runs second**: `backend/alembic/versions/e9f1a2b3c4d5_crm_schema_v2.py` changes its `down_revision` to `"d8a9f0c1b2e3"`.
3. **Strip `patients.date_of_birth`**: Remove the `ALTER TABLE patients ADD COLUMN date_of_birth` from `upgrade()` and `downgrade()` in `e9f1a2b3c4d5.py`.
4. **Single Head Result**: `python -m alembic heads` outputs exactly 1 linear head.

---

## 4. Master 100-Step Action Plan

### Phase 1: Migration Chain & Backend Foundation (Steps 1–15)
- [ ] **Step 001**: Switch working branch to `feature/frontend-redesign-impl`.
- [ ] **Step 002**: Fetch latest refs from `origin/integration/crm-merge` and check for any upstream commits.
- [ ] **Step 003**: Inspect `backend/alembic/versions/e9f1a2b3c4d5_crm_schema_v2.py`.
- [ ] **Step 004**: Change `down_revision` in `e9f1a2b3c4d5_crm_schema_v2.py` from `"c5d8e9f4a1b2"` to `"d8a9f0c1b2e3"`.
- [ ] **Step 005**: In `e9f1a2b3c4d5_crm_schema_v2.py` `upgrade()`, remove section 3 (`ALTER TABLE patients ADD COLUMN date_of_birth`).
- [ ] **Step 006**: In `e9f1a2b3c4d5_crm_schema_v2.py` `downgrade()`, remove section 3 (`op.drop_column('patients', 'date_of_birth')`).
- [ ] **Step 007**: Ensure `appointment_requests.date_of_birth` is intact or compliant with booking spec.
- [ ] **Step 008**: Confirm `users.role` check constraint properly enforces `('admin', 'therapist', 'front_desk')`.
- [ ] **Step 009**: Run `alembic heads` or verify migration graph has exactly 1 head.
- [ ] **Step 010**: Open `backend/app/core/dependencies.py` and inspect duplicate `require_roles` definition.
- [ ] **Step 011**: Remove the redundant synchronous `require_roles` helper in `backend/app/core/dependencies.py` (lines 55–64).
- [ ] **Step 012**: Verify `backend/app/core/rbac.py` aligns with permission registry.
- [ ] **Step 013**: Open repo root `schema.sql` and add clear header note: `-- REFERENCE ONLY / ARCHITECTURAL DESIGN SPECIFICATION (Alembic is single source of truth)`.
- [ ] **Step 014**: Verify PR #8 & PR #9 replacement notes in documentation.
- [ ] **Step 015**: Commit Phase 1 backend and migration fixes.

### Phase 2: Environment Variables & Suite-Wide Consistency (Steps 16–25)
- [ ] **Step 016**: Search codebase for any residual `NEXT_PUBLIC_API_BASE_URL` references.
- [ ] **Step 017**: Verify `frontend/crm/src/lib/api-client.ts` uses `NEXT_PUBLIC_API_URL` with standard fallback.
- [ ] **Step 018**: Ensure `frontend/crm/.env.example` has `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- [ ] **Step 019**: Ensure `frontend/exercise-library/.env.example` exists and documents `NEXT_PUBLIC_API_URL`.
- [ ] **Step 020**: Ensure `frontend/posture-tool/.env.example` exists and documents `NEXT_PUBLIC_API_URL`.
- [ ] **Step 021**: Check and verify `backend/.env.example` contains complete configuration variables.
- [ ] **Step 022**: Ensure no local storage overrides for base API URLs exist in any frontend app.
- [ ] **Step 023**: Standardize token storage key references across documentation (`token` vs `av_crm_access_token`).
- [ ] **Step 024**: Test build pipeline with environment variable substitution.
- [ ] **Step 025**: Commit Phase 2 configuration standardization.

### Phase 3: Auth Store & Security Hardening — Deny by Default (Steps 26–40)
- [ ] **Step 026**: Inspect `frontend/crm/src/store/index.ts` Zustand auth store.
- [ ] **Step 027**: Confirm `role` initial state defaults to `null` (not `'admin'`).
- [ ] **Step 028**: Check `SidebarNavigation.tsx` for any `|| ('admin' as UserRole)` fallback.
- [ ] **Step 029**: Check `therapists/page.tsx` for any fallback to `'admin'`.
- [ ] **Step 030**: Check `analytics/page.tsx` for any fallback to `'admin'`.
- [ ] **Step 031**: Check `recycle-bin/page.tsx` for any fallback to `'admin'`.
- [ ] **Step 032**: Check `patients/[id]/page.tsx` for any fallback to `'admin'`.
- [ ] **Step 033**: Audit `config/permissions.ts` functions: `canAccessModule(role, ...)` must return `false` if `role === null`.
- [ ] **Step 034**: Ensure all permission checks fail closed (deny access) when role is undefined/null.
- [ ] **Step 035**: Verify `frontend/crm/src/app/login/page.tsx` default values.
- [ ] **Step 036**: Remove any hardcoded `admin@avtest.com` and `Password123!` from `useForm` defaults.
- [ ] **Step 037**: Ensure login form inputs mount completely empty (`""`).
- [ ] **Step 038**: Verify login submission performs plaintext credentials POST to `/api/v1/auth/login`.
- [ ] **Step 039**: Verify 401 response interceptor clears stored tokens and triggers clean redirect.
- [ ] **Step 040**: Commit Phase 3 authentication and security hardening.

### Phase 4: Route-Level RBAC & Route Access Guards (Steps 41–55)
- [ ] **Step 041**: Inspect `frontend/crm/src/components/ui/AccessRestricted.tsx`.
- [ ] **Step 042**: Verify `/settings/page.tsx` is guarded with `canAccessModule(role, 'settings')` (Admin only).
- [ ] **Step 043**: Verify `/billing/page.tsx` is guarded with `canAccessModule(role, 'billing')` (Admin & Front Desk; deny Therapist).
- [ ] **Step 044**: Verify `/leads/page.tsx` is guarded with `canAccessModule(role, 'leads')` (Admin & Front Desk; deny Therapist).
- [ ] **Step 045**: Verify `/therapists/page.tsx` is guarded with `canAccessModule(role, 'therapists')` (Admin only).
- [ ] **Step 046**: Verify `/analytics/page.tsx` is guarded with `canAccessModule(role, 'analytics')`.
- [ ] **Step 047**: Verify `/recycle-bin/page.tsx` is guarded with `canAccessModule(role, 'recycleBin')`.
- [ ] **Step 048**: In `patients/[id]/page.tsx`, verify tab-level visibility gates (`billing`, `soapNotes`, `treatments`, `documents`).
- [ ] **Step 049**: Ensure therapists cannot see billing tabs or financial numbers inside patient profiles.
- [ ] **Step 050**: Verify sidebar navigation dynamically hides inaccessible menu links for therapist role.
- [ ] **Step 051**: Test direct URL bar typing: `/settings` as therapist renders `<AccessRestricted />`.
- [ ] **Step 052**: Test direct URL bar typing: `/billing` as therapist renders `<AccessRestricted />`.
- [ ] **Step 053**: Test direct URL bar typing: `/leads` as therapist renders `<AccessRestricted />`.
- [ ] **Step 054**: Test direct URL bar typing: `/therapists` as therapist renders `<AccessRestricted />`.
- [ ] **Step 055**: Commit Phase 4 route-level RBAC protections.

### Phase 5: Wire Real APIs & Eliminate Mock Success Alerts (Steps 56–70)
- [ ] **Step 056**: Open `frontend/crm/src/features/patients/components/TreatmentsTab.tsx`.
- [ ] **Step 057**: Check `onSubmit` in `TreatmentsTab.tsx` — remove mock mode save alert.
- [ ] **Step 058**: Create TanStack mutation `useCreateTreatmentSession` in `src/features/treatments/api.ts`.
- [ ] **Step 059**: Wire `TreatmentsTab.tsx` form submission to `POST /api/v1/treatments`.
- [ ] **Step 060**: Open `frontend/crm/src/features/patients/components/DocumentsTab.tsx`.
- [ ] **Step 061**: Check `onSubmit` in `DocumentsTab.tsx` — remove mock mode upload alert.
- [ ] **Step 062**: Create TanStack mutation `useUploadPatientDocument` in `src/features/patients/api.ts`.
- [ ] **Step 063**: Wire `DocumentsTab.tsx` upload form to `POST /api/v1/patients/{id}/documents`.
- [ ] **Step 064**: Open `frontend/crm/src/app/(dashboard)/analytics/page.tsx`.
- [ ] **Step 065**: In `analytics/page.tsx`, update `handleSaveCosts` to display an explicit notice that cost persistence is slated for backend Phase 2.
- [ ] **Step 066**: Open `frontend/crm/src/app/(dashboard)/recycle-bin/page.tsx` and verify `GET /api/v1/recycle-bin` is live with no mock fallback array.
- [ ] **Step 067**: Open `frontend/crm/src/app/(dashboard)/appointments/page.tsx` and verify `GET /api/v1/appointment-requests` is live.
- [ ] **Step 068**: Remove any mock fallback objects in public booking components.
- [ ] **Step 069**: Verify all empty and error states render clean UI without broken cards.
- [ ] **Step 070**: Commit Phase 5 API wiring and mock alert cleanup.

### Phase 6: Scope Update (Rev 3) & Multi-Tenant Capabilities (Steps 71–85)
- [ ] **Step 071**: Review Backend Scope Update Rev 3 capability registry keys in `backend/app/core/rbac.py`.
- [ ] **Step 072**: Review `user_permissions` table design specification (`id`, `clinic_id`, `user_id`, `capability_key`, `scope`).
- [ ] **Step 073**: Prepare capability resolution engine logic (`effective_scope(user, capability_key)`).
- [ ] **Step 074**: Prepare `/analytics/my-performance` endpoint schema (patients seen, appointments, treatments, own-scoped).
- [ ] **Step 075**: Prepare `/analytics/clinic-financials` endpoint schema (revenue, clinic-wide totals).
- [ ] **Step 076**: Update frontend `features/analytics/api.ts` to support both split analytics endpoints.
- [ ] **Step 077**: Update `analytics/page.tsx` to conditionally render My Performance for therapists vs Clinic Financials for Admins.
- [ ] **Step 078**: Ensure multi-tenant isolation (`clinic_id`) is strictly enforced on all queries.
- [ ] **Step 079**: Confirm WhatsApp click-to-chat links are rendered in appointments and prescription components.
- [ ] **Step 080**: Verify prescription PDF authenticated generation flow (`POST /prescriptions/{id}/pdf`).
- [ ] **Step 081**: Confirm posture report viewing links in patient records.
- [ ] **Step 082**: Verify exercise prescription library integration links in patient records.
- [ ] **Step 083**: Review lockout guard logic (prevent removing last `permissions.manage` or `users.manage` grant).
- [ ] **Step 084**: Ensure audit logging records every permission grant and revocation.
- [ ] **Step 085**: Commit Phase 6 capability and scope alignment.

### Phase 7: Verification, Regression Testing & Merge Preparation (Steps 86–100)
- [ ] **Step 086**: Run full backend health check: `GET /health` → 200.
- [ ] **Step 087**: Run therapist login test: `GET /api/v1/patients` with token → 200.
- [ ] **Step 088**: Run unauthenticated public test: `GET /api/v1/booking/branding/test-clinic` with no token → 200.
- [ ] **Step 089**: Run unauthorized test: `GET /api/v1/patients` with no token → 401.
- [ ] **Step 090**: Run Alembic head verification: `python -m alembic heads` → exactly 1 head.
- [ ] **Step 091**: Verify FastAPI app boot: `from app.main import app` boots cleanly with all routes.
- [ ] **Step 092**: Run TypeScript type check: `cd frontend/crm && npx tsc --noEmit` → 0 errors.
- [ ] **Step 093**: Run frontend build check: `cd frontend/crm && npm run build` → clean build.
- [x] **Step 094**: Perform manual browser smoke test for Admin login and dashboard navigation.
- [ ] **Step 095**: Perform manual browser smoke test for Therapist login (verify restricted routes blocked, my-performance shows).
- [ ] **Step 096**: Perform manual browser smoke test for Front Desk login (verify analytics not in sidebar).
- [x] **Step 097**: Update `docs/crm/AIChangelog.md` with session summary and diff details.
- [x] **Step 098**: Update `docs/crm/Bug.md` and `docs/crm/Handover.md`.
- [ ] **Step 099**: Prepare concise PR review reply for Onkar with checklist confirmation.
- [ ] **Step 100**: Push verified commits to `feature/frontend-redesign-impl` and celebrate merge readiness!

---

## 9. Resolved Open Questions (2026-08-21)

> Answers documented after cross-verification session with full RBAC Spec PDF review.

### Q1: Sparsh's Branch Merge Status
**Answer (confirmed by Tarun)**: PR #16 (`fix/backend-analytics-whatsapp`) is **NOT merged yet** into `integration/crm-merge`. Tarun confirmed he will follow Sparsh's merge as directed by Onkar.

**Impact**: Migration linearization fix (changing `down_revision` in `e9f1a2b3c4d5` from `c5d8e9f4a1b2` → `d8a9f0c1b2e3`) is **DEFERRED** until after Sparsh's branch merges. Do NOT apply this change now.

### Q2: Analytics Split — New Endpoints or Query Param?
**Answer (confirmed by Tarun)**: Follow Rev3 PDF — new dedicated endpoints.

**Implemented (2026-08-21)**:
- `GET /analytics/overview` — admin only (clinic-wide financials, revenue, leads). Now guarded by `require_roles(UserRole.ADMIN)`.
- `GET /analytics/my-performance` — therapist + admin (own-scoped stats: appointments, sessions, SOAP notes, patients seen).
- Frontend: analytics page renders `<TherapistPerformanceView>` for role=therapist and the full admin P&L view for admins.

### Q3: `user_permissions` Table — Phase 1 or Phase 2?
**Answer (from RBAC Spec PDF review)**: The RBAC Spec does **NOT** mention a `user_permissions` table. It is a purely **role-based** system with no per-user capability overrides. The capability system described in Rev3 is a **separate Phase 2** deliverable.

**Conclusion**: `user_permissions` table → Phase 2. No migration needed for this PR.

**Key RBAC Spec Findings**:
| Section | Finding | Action Taken |
|---|---|---|
| §4 Module Visibility | Front Desk: Analytics = **No** | Fixed `permissions.ts` + `rbac.py` — removed front_desk from analytics |
| §4 Module Visibility | Therapist: Analytics = **Own only** | Implemented `/analytics/my-performance` endpoint |
| §4 Module Visibility | Therapists module: **Admin only** (shows salaries) | Already enforced via `settings` permission |
| §7 Route Guards | Route guards only for auth — no 403 page needed | `<AccessRestricted />` is correct behavior |
| §8 Implementation Notes | Role from JWT claim, no `/me` endpoint | Already implemented correctly |
| §2 Role Source | `physio` role deprecated — use `therapist` | Migration `c5d8e9f4a1b2` already handles this |

### Q4: Hardcoded Therapist Salary
**Answer (confirmed by Tarun)**: Keep as editable default for now, add a comment.

**Implemented**: `therapistSalariesTotal = 65000` merged into editable `runningCosts` array as `{ id: '4', label: 'Therapist Salaries', amount: 65000 }`. Admin can edit it in the Running Costs UI. Phase 2: persist via `/api/v1/settings/running-costs`.

---

*Last updated: 2026-08-21 | Cross-verification session complete*
