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
- **Status**: 🔵 Needs investigation
- **Reported**: 2026-08-13
- **Reported By**: AI code review
- **Severity**: Medium
- **Affected Area**: Auth / api-client.ts

#### Symptom
When `api-client.ts` responseInterceptor handles a 401, it calls `clearStoredTokens()`
(clears localStorage) and redirects to `/login`. However, it does NOT call
`useAuthStore().logout()`, which means Zustand's in-memory state
(`isAuthenticated`, `token`, `role`) remains set until the page reloads.

#### Steps to Reproduce
1. Log in as a user
2. Manually expire or invalidate the JWT server-side
3. Trigger any API call
4. Observe: redirect happens, but Zustand state in memory still shows isAuthenticated = true
   until hard reload

#### Expected Behavior
On 401, both localStorage AND Zustand state should be cleared before redirect.

#### Root Cause
`api-client.ts` doesn't have direct access to the Zustand store (Zustand is a React hook context).
Calling hooks outside of React components is not allowed.

#### Fix Applied
TBD. Potential solutions:
1. Use Zustand's `getState()` outside React: `useAuthStore.getState().logout()`
   (Zustand supports this)
2. Subscribe to a global event from the store and clear there

#### Verification
TBD

#### Affected Files
| File | Change |
|---|---|
| `frontend/crm/src/lib/api-client.ts` | Add `useAuthStore.getState().logout()` call on 401 |

---

*Add new bugs at the bottom. Update status when resolved. Never delete entries.*
*Last updated: 2026-08-13 | Branch: integration/crm-merge*

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
