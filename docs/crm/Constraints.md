# Constraints.md — What AI Must Never Touch
> **Purpose**: Explicit no-go zones. These rules exist because violating them
> causes security holes, data leaks, multi-tenant contamination, or irreversible damage.
> No exception without a written entry in Decisions.md first.

---

## Legend

| Symbol | Meaning |
|---|---|
| ❌ NEVER | Absolute prohibition. Breaking this requires a security review. |
| ⚠️ ONLY IF | Conditional — document it in Decisions.md before doing it. |
| 🔒 AUTH BOUNDARY | Touches security model — triple-check and get human sign-off. |

---

## Section 1: Authentication & Security

### ❌ NEVER move authentication logic to the frontend
- Password hashing, token signing, permission checking — backend only.
- Frontend may only: receive a token, store it, send it, discard it.
- **Why**: Frontend JS is readable by any user. Auth logic there is theater, not security.

### ❌ NEVER validate credentials in frontend code
- No `if (password.length > 8)` security checks in components.
- Input validation (format, length for UX) is fine. Auth validation is not.

### ❌ NEVER bypass ClinicGateMiddleware
- Do not add `public_paths` entries without a documented security review.
- Every new protected route must flow through the middleware.
- **Why**: ClinicGateMiddleware is the only thing preventing cross-clinic data leakage.

### ❌ NEVER trust `clinic_id` sent from the frontend
- Backend always reads `clinic_id` from the signed JWT, never from request params/body.
- **Why**: A malicious user could pass any `clinic_id` and access another clinic's data.

### 🔒 ONLY IF: Adding a new public (unauthenticated) backend route
- Document the decision in Decisions.md with a full justification.
- Confirm the route returns zero patient/clinic-specific data.

---

## Section 2: Data & Database

### ❌ NEVER write raw SQL directly in API endpoint files
- Use SQLAlchemy ORM in `repositories/` layer.
- **Why**: Raw SQL bypasses type safety and the tenant-scoping patterns already in place.

### ❌ NEVER skip the `clinic_id` filter in repository queries
- Every query touching patient, lead, appointment, billing data MUST be filtered by `clinic_id`.
- Missing this means one clinic can read another's data.
- Pattern to follow: `select(Model).where(Model.clinic_id == clinic_id)`

### ❌ NEVER run Alembic migrations without reviewing the generated SQL
- `alembic revision --autogenerate` can produce destructive migrations.
- Always review with `alembic upgrade --sql head` before running.

### ⚠️ ONLY IF: Dropping or renaming a column
- Requires a 3-step migration: (1) add new column, (2) migrate data, (3) drop old column.
- Never drop in a single migration that runs on a live database.

---

## Section 3: Frontend Architecture

### ❌ NEVER call `axios` directly from a component
- All HTTP calls go through `lib/api-client.ts` via `features/*/api.ts`.
- **Why**: Interceptors (token injection, 401 redirect, error normalization) are only applied to the `apiClient` instance.

### ❌ NEVER duplicate server state in Zustand
- If data comes from an API, it belongs in TanStack Query cache, not a Zustand store.
- **Why**: Two sources of truth for the same data create stale-data bugs.

### ❌ NEVER introduce new mock data files
- The `src/mocks/` directory should be progressively deleted as real APIs are integrated.
- Show `<Loading>`, `<Empty>`, or `<Error>` states instead.

### ❌ NEVER create duplicate types
- Extend existing interfaces in `types/api.ts`.
- Before adding a new type, search for an existing one.

### ⚠️ ONLY IF: Creating a new Zustand store slice
- Only for UI state with no server-sourced data.
- Document the decision in Decisions.md.

---

## Section 4: Git & Branch Hygiene

### ❌ NEVER force push
- No `git push --force` or `git push -f` on any branch.

### ❌ NEVER modify unrelated files in a PR/commit
- One feature, one change set.

### ❌ NEVER rewrite commit history on shared branches
- No `git rebase` or `git commit --amend` on `integration/crm-merge`.

### ❌ NEVER delete branches without confirming they are fully merged
- Assume any existing branch is under review.

---

## Section 5: AI Behaviour Constraints

### ❌ NEVER invent API endpoints
- If an endpoint doesn't exist in `backend/app/api/v1/`, it does not exist.
- Check `openapi.yaml` or the actual route files. Never guess.

### ❌ NEVER create new architecture without justification
- No new state managers, API layers, auth systems, or folder structures
  unless explicitly requested by the user.

### ❌ NEVER perform large refactors unprompted
- If a refactor is needed, write the reasoning in Decisions.md, explain to the user, get approval.

### ❌ NEVER write code that silently swallows errors
- No bare `catch {}` blocks.
- No `console.log(error)` as the only error handling.
- Surface errors to users via toast, error state, or throw.

### ❌ NEVER skip the "understand before write" step
- Read the relevant existing file(s) before writing any new code.
- Always verify the backend contract (request/response schema) before building frontend integration.

---

## Section 6: PHI (Patient Health Information)

### ❌ NEVER log PHI to the console or log files
- Patient names, DOBs, diagnoses, billing amounts are PHI.
- Logs should contain IDs and statuses, not data values.

### ❌ NEVER expose prescription PDFs via unauthenticated endpoints
- PHI documents must only be served via: `GET /api/v1/prescriptions/{id}/pdf/download`
  with a valid JWT in the Authorization header.

### ❌ NEVER store PHI in browser localStorage beyond the session token
- Only `access_token` and `refresh_token` go into localStorage.
- Patient data lives in TanStack Query's in-memory cache.

---

## Constraint Update Protocol

If a constraint here is wrong or becomes outdated:
1. Do NOT silently ignore it.
2. Add an entry to `Decisions.md` explaining why the constraint should change.
3. Update this file with the revised constraint.
4. Reference the Decisions.md entry number in the constraint comment.

---

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
