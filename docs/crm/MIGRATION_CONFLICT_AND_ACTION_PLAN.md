# AV Suite — Project State & Migration Conflict Analysis & 100-Step Master Action Plan

## 1. What Is Going On: Executive Summary

You and your teammate (**Sparsh**) have both been building upon the shared integration branch `integration/crm-merge` (or base migration `c5d8e9f4a1b2`).
- **You (Tarun)** worked on `feature/frontend-redesign-impl` (frontend route migration, login flow, auth store, RBAC UI guards, API contracts).
- **Sparsh** worked on `fix/backend-analytics-whatsapp` (PR #16: WhatsApp click-to-chat links, login test data seed migration, analytics endpoint changes).
- **Onkar (Tech Coordinator)** provided comprehensive review feedback on your frontend redesign and issued **AV Suite CRM Backend Scope Update (Rev 3)** regarding a revised per-user capability permission model and analytics split.

---

## 2. Deep Dive: The Migration Conflict (Sparsh vs Tarun)

### Root Cause
Both migrations branch from the exact same parent `down_revision = "c5d8e9f4a1b2"`.
When merged together into `integration/crm-merge`, Alembic detects two independent heads:
```
c5d8e9f4a1b2 (Alembic Head at merge time)
    ├── d8a9f0c1b2e3 (Sparsh: seed demo login data)
    └── e9f1a2b3c4d5 (Tarun: crm_schema_v2)
```
Running `alembic heads` will report multiple heads and break automated deployments.

### What Sparsh's Migration Does (`d8a9f0c1b2e3`)
**File:** `backend/alembic/versions/d8a9f0c1b2e3_seed_demo_login_data.py`
- **Purpose:** Seeds deterministic demo fixtures for testing login, bookings, and CRM workflows.
- **Operations:**
  - Inserts demo clinic (`11111111-1111-1111-1111-111111111111` — *Aarogya Virohan Demo Clinic*)
  - Inserts 3 demo users with hashed passwords:
    - Admin: `admin@avtest.com` (`22222222-2222-2222-2222-222222222222`)
    - Front Desk: `frontdesk@avtest.com` (`66666666-6666-6666-6666-666666666666`)
    - Therapist: `therapist@avtest.com` (`33333333-3333-3333-3333-333333333333`)
  - Inserts demo lead: `John Prospect` (`77777777-...`)
  - Inserts 2 demo patients: `Alice Patient` and `Bob Patient`
  - Inserts 2 demo appointments assigned to demo therapist.

### What Tarun's Migration Does (`e9f1a2b3c4d5`)
**File:** `backend/alembic/versions/e9f1a2b3c4d5_crm_schema_v2.py`
- **Purpose:** Consolidates schema extensions needed by the CRM v2 features.
- **Operations:**
  1. Adds `therapist_id` (FK to users) and `finalized` (bool) on `soap_assessments`.
  2. Adds `finalized` (bool) on `treatment_sessions`.
  3. Adds `date_of_birth` on `patients` table.
  4. Adds `date_of_birth` on `appointment_requests` table.
  5. Adds `appointment_type` on `appointments` table.
  6. Creates PostgreSQL ENUM `payment_status` and adds `status` + `idempotency_key` on `payments`.
  7. Creates PostgreSQL ENUMs: `gender_type`, `specialty_type`, `lead_source_type`.
  8. Adds check constraint `ck_treatment_sessions_pain_score` (0–10).
  9. Tightens `users.role` check constraint to remove `'patient'`, allowing only `('admin', 'therapist', 'front_desk')`.

### Specific Migration Changes Demanded by Onkar
1. **Remove `patients.date_of_birth`** from your migration in both `upgrade()` and `downgrade()` (the team decided against changing DOB structure here or keeping age handling separated).
2. **Ensure `PATIENT` is dropped** from `UserRole` enum / check constraints.
3. **Linearize Chain:**
   As Onkar noted: *"Two items on Tarun's migration are still being fixed, so plan for Sparsh's to land first."*
   - Sparsh's migration (`d8a9f0c1b2e3`) stays `down_revision = "c5d8e9f4a1b2"`.
   - Your migration (`e9f1a2b3c4d5`) changes to `down_revision = "d8a9f0c1b2e3"`.

---

## 3. Review of the 6 Specific Feedback Items from Onkar

| # | Item | Issue | Solution |
|---|------|-------|----------|
| **1** | **Role fallback to admin** | `const role = useAuthStore((s) => s.role) \|\| ('admin' as UserRole)` in 5 files (`SidebarNavigation`, `therapists`, `analytics`, `recycle-bin`, `patients/[id]`). If state is loading or token is corrupt, it fails open to Admin. | Set fallback to `null`. If `role === null`, block or show Access Restricted / Skeleton loader. Never fail open. |
| **2** | **Ungated Dashboard Routes** | `/settings`, `/billing`, `/leads` have no role checks on direct navigation. | Wrap with `AccessRestricted` guard based on role (Settings = admin only; Billing/Leads = not for therapists). |
| **3** | **Env Var Inconsistency** | CRM uses `NEXT_PUBLIC_API_BASE_URL` vs Exercise/Posture tools using `NEXT_PUBLIC_API_URL`. Silent fallback to localhost occurs. | Standardize to `NEXT_PUBLIC_API_URL` across CRM and provide `.env.example` in all frontends. |
| **4** | **Fake Success Alerts (Mock Saves)** | `TreatmentsTab.tsx` line 54, `DocumentsTab.tsx` line 70, `analytics` `handleSaveCosts` show success alerts without saving. | Replace fake success with either real API mutation or a clear visual indicator/error that backend integration is pending. |
| **5** | **Leftover Mock Data** | Hardcoded items in `recycle-bin`, `appointments`, public booking fallback, and analytics. | Remove hardcoded mock initializers and connect to API queries with appropriate empty states. |
| **6** | **Hardcoded Login Credentials** | `admin@avtest.com` and `Password123!` prefilled in production build. | Empty default values in `LoginForm` inputs (`""`), keeping placeholder hints or dev helper toggles only. |

---

## 4. Architectural Guidance: PDF Scope Update (Rev 3)
- **Per-User Permissions**: Permissions move from coarse role checks to per-user capability overrides with scopes (`none`, `own`, `all`).
- **Roles as Templates**: Default template seeded from role; admins can override individual capabilities in new table `user_permissions`.
- **Analytics Split**: Split `/analytics/overview` into:
  - `GET /analytics/my-performance` (capability: `analytics.performance.view`, scoped to therapist's own records)
  - `GET /analytics/clinic-financials` (capability: `analytics.financial.view`, clinic-wide admin P&L)
- **Answers Needed by Onkar**:
  - `schema.sql` at root: Tag with a clear reference header stating it is purely design documentation and Alembic is sole source of truth.
  - PR #8 & #9: Clarify that `feature/frontend-redesign-impl` supersedes/replaces them.

---

## 5. The 100-Step Master Action Plan

### Phase 1: Migration Alignment & Backend Foundation (Steps 1–15)
- [ ] 001. Check out `feature/frontend-redesign-impl` and fetch latest `origin/integration/crm-merge`.
- [ ] 002. Rebase or merge base updates from `integration/crm-merge`.
- [ ] 003. Inspect `backend/alembic/versions/e9f1a2b3c4d5_crm_schema_v2.py`.
- [ ] 004. Update `down_revision` of `e9f1a2b3c4d5` to point to Sparsh's revision `d8a9f0c1b2e3`.
- [ ] 005. Remove `date_of_birth` column addition from `patients` in `e9f1a2b3c4d5.py` `upgrade()`.
- [ ] 006. Remove `date_of_birth` column removal from `patients` in `e9f1a2b3c4d5.py` `downgrade()`.
- [ ] 007. Verify `appointment_requests.date_of_birth` handling complies with schema rules.
- [ ] 008. Verify `users.role` check constraint properly excludes `patient` role.
- [ ] 009. Run `python -m alembic heads` and verify exactly 1 head exists.
- [ ] 010. Run `pytest backend/tests` to verify backend tests pass on the migration sequence.
- [ ] 011. Inspect `backend/app/core/dependencies.py` to remove duplicate `require_roles` definition.
- [ ] 012. Verify `backend/app/core/rbac.py` permissions baseline matches PDF Rev 3.
- [ ] 013. Add header comment to root `schema.sql` declaring it as reference-only.
- [ ] 014. Prepare response message for Onkar regarding PR #8/#9 replacement status.
- [ ] 015. Commit backend migration and dependency fixes.

### Phase 2: Environment Variables & Configuration Standardization (Steps 16–25)
- [ ] 016. Check all occurrences of `NEXT_PUBLIC_API_BASE_URL` in `frontend/crm`.
- [ ] 017. Replace `NEXT_PUBLIC_API_BASE_URL` with `NEXT_PUBLIC_API_URL` in `frontend/crm/src/lib/api.ts` or config files.
- [ ] 018. Standardize fallback URL handling across all frontends to avoid silent failure.
- [ ] 019. Create `frontend/crm/.env.example` documenting `NEXT_PUBLIC_API_URL`.
- [ ] 020. Create `frontend/exercise-library/.env.example` if missing.
- [ ] 021. Create `frontend/posture-tool/.env.example` if missing.
- [ ] 022. Verify token storage key consistency notes across suite.
- [ ] 023. Update CRM build scripts and test environment configs.
- [ ] 024. Verify CRM frontend can read `NEXT_PUBLIC_API_URL` during dev and build.
- [ ] 025. Commit environment standardization changes.

### Phase 3: Auth Store & Security Hardening — Deny by Default (Steps 26–40)
- [ ] 026. Inspect `frontend/crm/src/store/authStore.ts` or equivalent Zustand auth store.
- [ ] 027. Ensure `role` state defaults to `null` (not `'admin'`).
- [ ] 028. Remove `|| ('admin' as UserRole)` from `SidebarNavigation.tsx`.
- [ ] 029. Remove `|| ('admin' as UserRole)` from `frontend/crm/src/app/(dashboard)/therapists/page.tsx`.
- [ ] 030. Remove `|| ('admin' as UserRole)` from `frontend/crm/src/app/(dashboard)/analytics/page.tsx`.
- [ ] 031. Remove `|| ('admin' as UserRole)` from `frontend/crm/src/app/(dashboard)/recycle-bin/page.tsx`.
- [ ] 032. Remove `|| ('admin' as UserRole)` from `frontend/crm/src/app/(dashboard)/patients/[id]/page.tsx`.
- [ ] 033. Search entire codebase for any remaining fallback assignments to `'admin'`.
- [ ] 034. Implement loading skeleton / state while auth hydration is resolving.
- [ ] 035. Ensure unauthenticated or role-less state displays Access Restricted or triggers redirect.
- [ ] 036. Inspect `frontend/crm/src/app/login/page.tsx` (or LoginForm component).
- [ ] 037. Remove hardcoded default credentials (`admin@avtest.com`, `Password123!`).
- [ ] 038. Ensure form inputs start empty (`""`).
- [ ] 039. Test login validation error messages with empty and invalid inputs.
- [ ] 040. Commit auth security and fallback hardening.

### Phase 4: Route-Level RBAC & Access Restriction Guards (Steps 41–55)
- [ ] 041. Review `frontend/crm/src/components/auth/AccessRestricted.tsx` component.
- [ ] 042. Add role protection guard to `frontend/crm/src/app/(dashboard)/settings/page.tsx` (Admin only).
- [ ] 043. Add role protection guard to `frontend/crm/src/app/(dashboard)/billing/page.tsx` (Admin & Front Desk; deny Therapist).
- [ ] 044. Add role protection guard to `frontend/crm/src/app/(dashboard)/leads/page.tsx` (Admin & Front Desk; deny Therapist).
- [ ] 045. Verify `frontend/crm/src/app/(dashboard)/therapists/page.tsx` salary and payroll gating.
- [ ] 046. Verify `frontend/crm/src/app/(dashboard)/analytics/page.tsx` access restriction.
- [ ] 047. Verify `frontend/crm/src/app/(dashboard)/recycle-bin/page.tsx` access restriction.
- [ ] 048. Verify `frontend/crm/src/app/(dashboard)/patients/[id]/page.tsx` clinical vs billing tabs gating.
- [ ] 049. Add unit / integration tests for role gating components.
- [ ] 050. Test direct browser URL navigation for each role: `/settings`, `/billing`, `/leads`.
- [ ] 051. Test therapist direct navigation to `/therapists` to ensure salary details are blocked.
- [ ] 052. Verify navigation links are dynamically filtered in the sidebar navigation.
- [ ] 053. Ensure unauthorized route access renders friendly error with back button.
- [ ] 054. Check mobile navigation drawer enforces same RBAC checks.
- [ ] 055. Commit route RBAC guarding updates.

### Phase 5: Elimination of Mock Success Actions & Mock Data (Steps 56–70)
- [ ] 056. Open `TreatmentsTab.tsx` and find line 54 ("mock mode for save").
- [ ] 057. Connect `TreatmentsTab` to real API endpoint (`POST /api/v1/treatments`).
- [ ] 058. If treatment endpoint is pending, show an explicit error/notice rather than a fake success banner.
- [ ] 059. Open `DocumentsTab.tsx` and find line 70 ("mock mode for upload").
- [ ] 060. Connect `DocumentsTab` to real document upload API (`POST /api/v1/documents`).
- [ ] 061. If upload is pending, show explicit unsupported/pending notice.
- [ ] 062. Open `analytics` page and find `handleSaveCosts`.
- [ ] 063. Remove fake "Running costs saved successfully" alert or wire to real API/state.
- [ ] 064. Open `recycle-bin/page.tsx` and replace `MOCK_DELETED_ITEMS` with API call `GET /api/v1/recycle-bin`.
- [ ] 065. Open `appointments/page.tsx` and replace `MOCK_REQUESTS` with API call `GET /api/v1/appointments`.
- [ ] 066. Check public booking page and remove demo fallback response.
- [ ] 067. Replace hardcoded running cost figures with dynamic values or clear empty state.
- [ ] 068. Check SOAP notes tab for any lingering mock data structures.
- [ ] 069. Verify all empty states look clean and premium when no data returns.
- [ ] 070. Commit mock elimination and real API wiring.

### Phase 6: Aligning with Backend Scope Update Rev 3 (Steps 71–85)
- [ ] 071. Review capability registry specification (Rev 3 Section 6).
- [ ] 072. Review `user_permissions` model design (Rev 3 Section 7).
- [ ] 073. Review scope resolution logic (`effective_scope(user, capability_key)`) (Rev 3 Section 8).
- [ ] 074. Prepare frontend API service for `/analytics/my-performance`.
- [ ] 075. Prepare frontend API service for `/analytics/clinic-financials`.
- [ ] 076. Ensure frontend analytics dashboard conditionally renders therapist performance tab vs clinic P&L.
- [ ] 077. Add frontend UI placeholders / screens for upcoming Admin User Permission overrides table.
- [ ] 078. Review "own patients" query derivation helper concept in backend.
- [ ] 079. Verify clinic multi-tenancy isolation (`clinic_id`) is strictly preserved across all calls.
- [ ] 080. Check audit log integration readiness for permission changes.
- [ ] 081. Verify WhatsApp click-to-chat links render properly on appointment & prescription screens.
- [ ] 082. Verify posture report viewing links in patient records.
- [ ] 083. Verify exercise prescription links in patient records.
- [ ] 084. Test token expiration handling and automatic logout / refresh.
- [ ] 085. Commit scope update alignment changes.

### Phase 7: End-to-End Testing, Browser Smoke Tests & Polish (Steps 86–100)
- [ ] 086. Run full backend regression checks:
  - `GET /api/v1/patients` with therapist token → 200
  - `GET /api/v1/booking/branding/test-clinic` with no token → 200
  - `GET /api/v1/patients` with no token → 401
  - `python -m alembic heads` → exactly 1 head
  - FastAPI app boot → 94+ routes
- [ ] 087. Run frontend lint and build (`npm run lint` / `npm run build`) in `frontend/crm`.
- [ ] 088. Test end-to-end admin login in browser.
- [ ] 089. Test end-to-end therapist login in browser.
- [ ] 090. Test end-to-end front desk login in browser.
- [ ] 091. Verify therapist cannot view clinic P&L or salary totals.
- [ ] 092. Verify therapist cannot access `/settings` or `/billing`.
- [ ] 093. Test patient creation and SOAP assessment recording.
- [ ] 094. Test appointment booking flow and status changes.
- [ ] 095. Verify responsive UI layout on mobile, tablet, and desktop viewports.
- [ ] 096. Check console logs to ensure no uncaught exceptions or hydration mismatches.
- [ ] 097. Update `docs/crm/AIChangelog.md`, `docs/crm/Bug.md`, and `docs/crm/Handover.md`.
- [ ] 098. Draft comprehensive PR handover note addressing Onkar's checklist.
- [ ] 099. Push changes to branch and verify CI checks pass.
- [ ] 100. Submit for final review and celebrate clean merge!
