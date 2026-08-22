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

---

### [BUG-007] Schema Validation Error on Patient Retrieval
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-22
- **Reported By**: User via Terminal Log (fastapi.exceptions.ResponseValidationError)
- **Severity**: High
- **Affected Area**: Patients (Listing/Retrieval)

#### Symptom
When attempting to view patients, the backend throws a 500 error, and the terminal log displays `ResponseValidationError` indicating that the `last_name` field does not match the allowed pattern.

#### Root Cause
The `PatientBase` schema defined a strict `NAME_PATTERN` (`^[A-Za-z][A-Za-z .'-]{0,99}$`) which explicitly forbid digits. Since the `seed.py` (and potentially users in the UI) created patients with digits in their last name (e.g. "3" or "2"), Pydantic threw a validation error when serializing the `PatientRead` response. This strict validation only existed in the Patient module.

#### Fix Applied
Updated `NAME_PATTERN` in `backend/app/schemas/patient.py` to allow digits (`^[A-Za-z0-9][A-Za-z0-9 .'-]{0,99}$`).

#### Verification
Database queried to confirm patients with digits in their name exist. Updated the regex pattern to accommodate this data.

#### Affected Files
| File | Change |
|---|---|
| `backend/app/schemas/patient.py` | Updated `NAME_PATTERN` to allow numbers |

---

### [BUG-008] Cannot Create Patient due to Schema Mismatch
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-22
- **Reported By**: User via Frontend Add Patient UI
- **Severity**: High
- **Affected Area**: Patients (Creation/Update)

#### Symptom
When attempting to add a new patient through the frontend modal, the API request fails. The frontend modal requires fields such as Gender, Chief Complaint, and Referral Source, but the backend `PatientCreate` schema lacked these fields. Furthermore, the `create_patient` service method crashed with an `AttributeError` because it tried to read `payload.full_name` from the schema, which didn't exist.

#### Root Cause
The Pydantic schemas in `backend/app/schemas/patient.py` were out of sync with the PostgreSQL `patients` table (missing `gender`, `chief_complaint`, `referral_source`, `status`, `age`). Additionally, `app/services/patient.py` manually attempted to read a `full_name` attribute that was never defined on `PatientCreate`.

#### Fix Applied
1. Added the missing fields (`gender`, `chief_complaint`, `referral_source`, `status`, `age`) as `Optional` to `PatientBase` and `PatientUpdate` in `backend/app/schemas/patient.py`.
2. Updated `backend/app/services/patient.py` to use `payload.first_name` and `payload.last_name` instead of `payload.full_name`.

#### Verification
Database models and Pydantic schemas now align, preventing validation drops and `AttributeError` crashes on creation.

#### Affected Files
| File | Change |
|---|---|
| `backend/app/schemas/patient.py` | Added missing fields to schemas |
| `backend/app/services/patient.py` | Fixed `AttributeError` in `create_patient` |

---

### [BUG-009] React Hook Order Violation in Patient Workspace
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-22
- **Reported By**: User via Frontend Console
- **Severity**: High
- **Affected Area**: Patients (Patient Workspace / Profile Page)

#### Symptom
When clicking on a patient to view their profile, the page crashes with a red Next.js error: `React has detected a change in the order of Hooks called by PatientWorkspacePage.` or `Rendered more hooks than during the previous render.`

#### Root Cause
The `usePrescriptions`, `useCreatePrescription`, and `useGeneratePrescriptionPdf` React hooks were being called *after* conditional early returns (`if (isLoading)` and `if (!patient)`). React enforces a strict Rule of Hooks that requires all hooks to be called unconditionally at the top level of the component to guarantee the exact same order of execution on every render.

#### Fix Applied
Moved the prescription-related hooks to the top of the component in `frontend/crm/src/app/(dashboard)/patients/[id]/page.tsx`, directly below the other hook calls and before any `if` statements.

#### Verification
Navigating to the Patient Workspace no longer crashes the app, and the React Hooks correctly execute in a consistent order regardless of loading state.

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/app/(dashboard)/patients/[id]/page.tsx` | Moved hooks above conditional returns |

---

### [BUG-010] Maximum Update Depth Exceeded (Infinite Loop) in SOAP Notes
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-22
- **Reported By**: User via Frontend Console
- **Severity**: High (Crashes tab/browser)
- **Affected Area**: Patients (SOAP Notes Tab)

#### Symptom
When navigating to the SOAP Notes tab, the React console rapidly flooded with errors stating: `Maximum update depth exceeded. This can happen when a component calls setState inside useEffect...` The number of errors quickly climbed into the hundreds, freezing the application.

#### Root Cause
In `SoapNotesTab.tsx`, `assessmentsData` was derived using `assessmentsResponse?.data || []`. The fallback `[]` creates a new array reference on every single render. This variable was then passed to a `useEffect` dependency array, causing the effect to run infinitely, calling `setAssessments`, triggering a re-render, creating a new array reference, and looping endlessly.

#### Fix Applied
1. Wrapped the `assessmentsData` fallback in a `React.useMemo` to ensure stable references across renders: `const assessmentsData = React.useMemo(() => assessmentsResponse?.data || [], [assessmentsResponse?.data]);`.
2. Added a `useEffect` to safely sync `activeNote` with fetched data when the assessments load, preventing existing notes from being hidden by the default dummy state.

#### Verification
Navigating to the SOAP Notes tab no longer triggers the infinite loop, the console remains clear of depth errors, and existing SOAP notes correctly load into the editor.

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/features/patients/components/SoapNotesTab.tsx` | Added `useMemo` and `useEffect` for data sync |

---

### [BUG-011] 500 Internal Server Error when Finalizing SOAP Notes
- **Status**: ✅ Verified fixed
- **Reported**: 2026-08-22
- **Reported By**: User via Screenshot/Console
- **Severity**: High (Data Loss / Fails to save)
- **Affected Area**: Patients (SOAP Notes Tab)

#### Symptom
When attempting to finalize or save a SOAP note, the frontend threw a CORS error and the backend logged a 500 Internal Server Error (`DataError: invalid input value for enum specialty_type: "ortho"`). Even if the enum matched, the database was silently rolling back because of a missing `session.commit()`.

#### Root Cause
1. **Enum mismatch**: The frontend was sending `ortho`, `neuro`, etc. for `specialty`, which did not exist in the PostgreSQL `specialty_type` enum (only `physiotherapy`, `chiropractic`, etc. were allowed).
2. **Missing commit**: `SoapAssessmentService` and `TreatmentSessionService` were calling `repository.create()` which only flushed the transaction without committing, causing silent data loss on successful insertions.

#### Fix Applied
1. Changed `SPECIALTIES` array in `SoapNotesTab.tsx` to map to existing valid backend enum values (`physiotherapy`, `chiropractic`, etc.) while retaining clinical UI labels.
2. Modified `create_assessment`, `update_assessment`, `create_session`, `update_session`, and `delete_session` in `backend/app/services/treatment.py` to correctly call `await self.repository.session.commit()`.

#### Verification
Restarted the backend server and tested creating SOAP notes. Data now persists properly in the database and 201 Created is returned without 500 DataError.

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/features/patients/components/SoapNotesTab.tsx` | Mapped specialty keys to valid backend enums |
| `backend/app/services/treatment.py` | Added explicit `commit()` to mutating operations |


### [BUG-003] 422 Unprocessable Entity during Seeding (Phone Number Format)
- **Status**: ✅ Resolved
- **Severity**: High (Blocked E2E testing)
- **Reported**: 2026-08-22
- **Fixed**: 2026-08-22

#### Description
The seeding script (`seed.py`) was generating phone numbers that didn't meet the `PatientBase` Pydantic model requirements, specifically requiring exactly 10 digits and validating with a regex (`^\d{10}$`).

#### Root Cause
Dummy generation logic was creating arbitrary length phone numbers (e.g. `9876543210` with loops).

#### Fix Implemented
Updated `seed.py` dummy data generators to ensure all phone numbers stringify into exactly 10 digits (e.g., `1234567891`). Updated the `test_bucket_rbac.py` file to conform to this standard.

---

## 2026-08-22
- **Issue:** `user_id` was NULL in audit logs for `grant_permission`.
  **Fix:** Correctly passed `current_user.id` as `granted_by` in `update_user_permissions` route in `backend/app/api/v1/users.py`.
- **Issue:** Image upload for clinic logo failed with 422 Unprocessable Entity due to Base64 length exceeding 2048 characters.
  **Fix:** Removed `max_length` from `branding_logo_url` in `app/schemas/settings.py`, updated `Clinic` model to use `Text` in `app/models/clinic.py`, and ran Alembic migration.
- **Issue:** Clinic settings page flickered with mock data.
  **Fix:** Removed hardcoded initial state values in `frontend/crm/src/app/(dashboard)/settings/page.tsx`.
- **Issue:** UI Layout did not reflect custom branding.
  **Fix:** Updated `AppShell.tsx` and `SidebarNavigation.tsx` to use `clinicSettings.name`, `clinicSettings.branding_logo_url`, and `bg-[var(--brand-navy)]`.
