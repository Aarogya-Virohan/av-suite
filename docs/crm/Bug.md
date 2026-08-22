# Bug.md — Bug Trail
> **Purpose**: A start-to-finish trail for every bug anyone can pick up cold.
> No bug is "fixed" until it has an entry here with root cause and verification.

---

## Active Bug Log

> ✅ = Verified fixed | 🔴 = Active / Unresolved | 🟡 = Fix in progress | 🔵 = Needs investigation

---

## Bug Report Template

```markdown
### [BUG-NNN] Short Bug Title
- **Status**: 🔴 Active
- **Reported**: YYYY-MM-DD
- **Reported By**: [User / AI session / test]
- **Severity**: Critical / High / Medium / Low
- **Affected Area**: [Feature / module]

#### Symptom
[What the user sees or what fails]

#### Steps to Reproduce
1.
2.
3.

#### Expected Behavior
[What should happen]

#### Actual Behavior
[What actually happens]

#### Root Cause
[Once investigated — what caused it]

#### Fix Applied
[What was changed, which files]

#### Verification
[How we confirmed it's fixed — test run, manual steps]

#### Affected Files
| File | Change |
|---|---|
| path/to/file | Description |
```

---

## Bug Log

### [BUG-001] Dashboard Analytics Shows 0 on First Load (Needs Investigation)
- **Status**: 🔵 Needs investigation
- **Reported**: 2026-08-13
- **Reported By**: AI analysis of dashboard/page.tsx
- **Severity**: Medium
- **Affected Area**: Dashboard / Analytics

#### Symptom
Dashboard KPI cards may show `0` instead of a loading state when the analytics API call
is in-flight or when the backend is unreachable.

#### Steps to Reproduce
1. Start with a slow network or temporarily stop the backend
2. Load `/dashboard`
3. Observe KPI cards

#### Expected Behavior
A loading spinner or skeleton should display while the data is fetching.
An error state should display if the API is unreachable.

#### Actual Behavior
TBD — `|| 0` fallbacks in the JSX (`{overview?.total_patients || 0}`) may silently
show zero instead of distinguishing between "zero records" and "data not loaded yet".

#### Root Cause
TBD — the `|| 0` pattern hides the difference between:
- API returned `0` (legitimate empty state)
- API not yet responded (`overview` is `undefined`)
- API failed (`isError` is true but numbers still fall back to 0)

#### Fix Applied
TBD

#### Verification
TBD

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/app/(dashboard)/dashboard/page.tsx` | Review `|| 0` fallbacks |

---

### [BUG-002] 401 Redirect Does Not Clear Zustand State
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-13
- **Reported By**: AI code review
- **Severity**: Medium
- **Affected Area**: Auth / api-client.ts

#### Symptom
When `api-client.ts` responseInterceptor handles a 401, it calls `clearStoredTokens()`
(clears localStorage) and redirects to `/login`. However, it did NOT call
`useAuthStore().logout()`, which means Zustand's in-memory state
(`isAuthenticated`, `token`, `role`) remains set until the page reloads.

#### Root Cause
`api-client.ts` doesn't have direct access to the Zustand store via React hooks (hooks
are only valid inside React components). The fix uses Zustand's `.getState()` vanilla API
which is explicitly designed for use outside React component trees.

#### Fix Applied
Added `useAuthStore.getState().logout()` call in `api-client.ts` 401 handler, alongside
`clearStoredTokens()`. Zustand's `.getState()` is the officially supported pattern for
accessing store state outside React (documented in D-004).

#### Verification
401 response now: (1) clears localStorage via `clearStoredTokens()`, (2) resets Zustand
in-memory auth state via `.getState().logout()`, (3) redirects to `/login`.

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/lib/api-client.ts` | Added `useAuthStore.getState().logout()` on 401 |

---

*Add new bugs at the bottom. Update status when resolved. Never delete entries.*
*Last updated: 2026-08-21 | Branch: feature/frontend-redesign-impl*

---

### [BUG-004] Hardcoded `therapist_id` & `clinic_id` in TreatmentsTab Default Values
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-21
- **Reported By**: Antigravity cross-verification audit
- **Severity**: High (security + constraint violation)
- **Affected Area**: TreatmentsTab / Patient Management

#### Symptom
`TreatmentsTab.tsx` constructed a fake `TreatmentSession` object with hardcoded
`clinic_id: 'cln_aarogya_1'` and `therapist_id: 'usr_therapist_1'`. Even though this
object was never persisted (the form was mocked), these values would have been sent to
the backend if wired naively.

#### Root Cause
Mock-first implementation from early development stage. `clinic_id` was never meant to
be sent from the frontend (backend derives it from JWT). `therapist_id` defaulted to a
hardcoded string instead of the authenticated user's ID.

#### Fix Applied
- Removed the entire fake `TreatmentSession` object construction
- `therapist_id` default now reads from `useAuthStore.getState().userId`
- `clinic_id` is never sent — the backend injects it from the JWT via `get_current_clinic()`
- The `onSubmit` now calls `useCreateTreatmentSession().mutate(values, ...)`

#### Verification
- Mock toast removed. Form submission now calls `POST /api/v1/treatments` with bearer token.
- On success: `toast.success` + cache invalidation. On error: `toast.error` with backend detail.

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/features/patients/components/TreatmentsTab.tsx` | Replaced mock with real mutation |
| `frontend/crm/src/features/treatments/api.ts` | Added `useCreateTreatmentSession` |

---

### [BUG-003] Unwired Endpoints Emitting Warnings (Technical Debt)
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-13
- **Reported By**: AI compliance review
- **Severity**: Low
- **Affected Area**: Settings, Patients, Appointments

#### Symptom
The UI allows interacting with "Save Branding", "Finalize SOAP Note", and "Generate Rx", but these now emit a yellow warning toast that backend synchronization is pending.

#### Steps to Reproduce
1. Navigate to Settings and click Save Branding.
2. Navigate to Patient > SOAP Notes and click Finalize.
3. Observe the `toast.warning`.

#### Expected Behavior
These actions should be wired to actual backend APIs and emit a green `toast.success` upon successful server response.

#### Actual Behavior
State is only updated locally or not at all (pending backend implementation).

#### Root Cause
Backend endpoints for these specific operations are either missing or the frontend `apiClient` mutations have not been written.

#### Fix Applied
Wired up the endpoints using the Feature Slices architecture (`src/features/settings`, `src/features/users`, `src/features/assessments`, `src/features/prescriptions`). The UI components now correctly use TanStack Query mutations to hit the backend endpoints.

#### Verification
TypeScript compilation passed with 0 errors. The UI now emits `toast.success()` after successful API mutations.

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/app/(dashboard)/settings/page.tsx` | Wire Save action |
| `frontend/crm/src/features/patients/components/SoapNotesTab.tsx` | Wire Finalize action |
| `frontend/crm/src/app/(dashboard)/patients/[id]/page.tsx` | Wire Rx Generation |

---

### [BUG-005] Missing Database Commits in Backend Services
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-22
- **Reported By**: User via CRM Lead Pipeline missing records
- **Severity**: Critical
- **Affected Area**: Leads, Billing, Booking, Documents

#### Symptom
When creating a lead or approving an appointment request, the backend returned a 201 Created or 200 OK success response, but the record was missing from the database on subsequent fetches.

#### Root Cause
Backend service methods (e.g., `create_lead` in `LeadService`) performed database repository operations which called `flush()`, but explicitly forgot to call `await session.commit()` before returning the result to the FastAPI router. As a result, the transaction was silently rolled back when the request finished.

#### Fix Applied
Injected `await self.*_repository.session.commit()` directly after the mutation operations in `lead.py`, `billing.py`, `booking.py`, and `document.py`.

#### Verification
Created a new lead and verified the record is visible in the frontend list and exists in PostgreSQL.

#### Affected Files
| File | Change |
|---|---|
| `backend/app/services/lead.py` | Added commit |
| `backend/app/services/billing.py` | Added commit |
| `backend/app/services/booking.py` | Added commit |
| `backend/app/services/document.py` | Added commit |

---

### [BUG-006] Appointments Table Empty on Frontend
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-22
- **Reported By**: User 
- **Severity**: High
- **Affected Area**: Appointments Dashboard

#### Symptom
The appointments view in the frontend displayed an empty list despite appointments existing in the backend. 

#### Root Cause
The frontend API client (`useAppointments`) assumed the backend returned `{ data: [...] }`. However, the backend pagination schema (`AppointmentListResponse`) returns `{ items: [...] }`. This resulted in `undefined` being assigned to the list, cascading to an empty array fallback.

#### Fix Applied
Updated the response mapping in `useAppointments` to correctly extract the array from `res.data?.items` before passing it to the UI components.

#### Verification
Navigated to `/appointments` and confirmed the appointment data correctly populates the UI table.

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/features/appointments/api.ts` | Fixed response mapping |
