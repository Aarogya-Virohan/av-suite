# AV Suite CRM — Frontend Architecture & Build Spec
**FINAL — Ready to Build**

**Owner:** Tarun (Frontend) · **Backend counterpart:** Sparsh · **Product/Spec owner:** Onkar
**Status:** Final. All previous addenda and the RBAC spec have been reconciled into this single document. Do not reference earlier versions. `ADDENDUM_v2.md` and `ADDENDUM_v3.md` are historical changelogs only — nothing in them overrides this doc.

---

## 1. Scope & Context

Rebuilding the CRM frontend from scratch at `frontend/crm/` inside the `av-suite` monorepo, alongside the Posture Tool and Exercise Library frontends. Backend is FastAPI + PostgreSQL (Supabase, multi-tenant) per the SRS — this doc governs frontend structure, screens, and integration behavior only. Deploy target: Vercel, auto-deploy from `dev`, manual promote-to-production.

---

## 2. Information Architecture

- `/login` — outside the shell.
- `/` (Dashboard Shell), authenticated:
  - `/dashboard`, `/patients` (+ `/patients/:id` workspace), `/leads`, `/appointments`, `/therapists`, `/billing`, `/analytics`, `/recycle-bin`, `/settings`.
- `/booking/:clinicSlug` — public, outside the authenticated shell. Resolves clinic branding via `GET /api/v1/booking/branding/{clinic_slug}` (clinic name/logo/color only — no patient data). **Confirm with Sparsh before Day 11 that `clinics.slug` exists in the schema** — it was absent in the last schema review; see Q7.

---

## 3. RBAC

Centralized in `src/config/permissions.ts`. Source of truth is the RBAC Spec (Onkar, July 2026). This matrix is implemented as a typed, exported config object — changing a permission is a data edit, not a code refactor.

### 3.1 Module Visibility — Sidebar

| Module | Admin | Therapist | Front Desk |
|---|---|---|---|
| Dashboard | ✅ | ✅ | ✅ |
| Patients | ✅ | ✅ | ✅ |
| Appointments | ✅ | own only | ✅ |
| Analytics | ✅ | own only | ❌ |
| Billing | ✅ | ❌ | ✅ |
| Leads | ✅ | ❌ | ✅ |
| Therapists | ✅ | ❌ | ❌ |
| Recycle Bin | ✅ | ❌ | ❌ |
| Settings | ✅ | ❌ | ❌ |

**Own only** = records belonging to that therapist. Filtering is applied server-side; the frontend does not filter — it sends the request and renders what the backend returns.

**Therapists module note:** This screen displays individual salaries and total monthly payroll. The restriction applies to the data as well as the menu item.

### 3.2 Module Visibility — Inside Patient Detail

| Section | Admin | Therapist | Front Desk |
|---|---|---|---|
| Treatments / SOAP Notes | ✅ | own patients | ❌ |
| Assessments | ✅ | own patients | ❌ |
| Documents | ✅ | own patients | ✅ |

### 3.3 Action Permissions

| Action | Admin | Therapist | Front Desk |
|---|---|---|---|
| Create / edit patient | ✅ | ✅ | ✅ |
| Delete patient | ✅ | ❌ | ❌ |
| Create / edit / cancel appointment | ✅ | own only | ✅ |
| Create / edit SOAP note | ✅ | own only | ❌ |
| Create invoice, record payment | ✅ | ❌ | ✅ |
| Create / sell package | ✅ | ❌ | ❌ |
| Upload / download documents | ✅ | own patients | ✅ |
| Restore deleted records | ✅ | ❌ | ❌ |
| Manage users and roles | ✅ | ❌ | ❌ |
| Update clinic settings / branding | ✅ | ❌ | ❌ |

### 3.4 Enforcement Rules

- No 403 pages. Restricted sidebar items and tabs are hidden — not rendered at all.
- Route guards are for authentication only: no token → redirect to `/login`; logout clears token and returns to `/login`.
- The backend is the actual security boundary and returns 403 on any unauthorized action. When a 403 is received, surface a human-readable error toast — never suppress it silently.
- The `patient` role exists in the JWT enum but never logs into the CRM. No UI is required for it. Patients only use the public booking form.
- A Manager role may be introduced later. The config-driven `permissions.ts` makes this a data edit, not a refactor.

---

## 4. Design System & Tokens

CRM defines its own design tokens, built to be consumed by Posture Tool and Exercise Library later. CRM is the source, not a consumer, of the shared token set. Tokens live in a standalone, framework-agnostic package.

```text
packages/design-tokens/
├── src/
│   ├── colors.ts
│   ├── typography.ts
│   ├── spacing.ts
│   ├── radii.ts
│   ├── shadows.ts
│   ├── motion.ts
│   ├── breakpoints.ts
│   ├── z-index.ts
│   └── index.ts
├── tailwind-preset.ts
└── package.json          # published internally as @av-suite/design-tokens
```

**Token checklist:**
- **Color palette** — soft neutral backgrounds (slate/gray-50 → gray-900), one refined primary accent (deep healthcare blue or subtle teal), no heavy gradients. Semantic tokens (`bg-surface`, `text-primary`, `border-subtle`, `accent`, `destructive`, `success`, `warning`) map onto the raw scale.
- **Typography scale** — Inter (or equivalent legible sans), strict hierarchy tuned for data scanning.
- **Spacing scale** — 8px base grid.
- **Border radius** — 10–14px for cards and modals.
- **Shadows** — reserved for elevated elements only (modals, popovers, dropdowns); none on standard cards.
- **Animation duration** — short, purposeful; no decorative motion.
- **Breakpoints** — matched to Section 10 responsive tiers.
- **Z-index hierarchy** — single documented scale: base → sticky header → dropdown → drawer → modal → toast.
- **Iconography** — Lucide, consistent stroke width across the suite.

`frontend/crm/tailwind.config.ts` consumes `@av-suite/design-tokens`'s preset. No local color or type overrides.

---

## 5. Auth & Token Handling

**Confirmed decisions (supersedes all earlier drafts):**

- **Token storage: `localStorage`.** Not in-memory. Not cookies. Both the login branch and the integration branch must use the same mechanism. This is the committed approach for this pass.
- **Access token:** short-lived (15 minutes). JWT carries claims: `sub` (user ID), `clinic_id`, `role`. Stored in `localStorage` on receipt.
- **Refresh token:** 15-day lifetime. Endpoint: `POST /api/v1/auth/refresh` (exact path to confirm with Sparsh). The frontend calls this on 401 to obtain a new access token.
- **No `/me` endpoint exists.** Role, `clinic_id`, and user ID are decoded from the JWT claims directly. Do not call a separate endpoint to hydrate user state.
- **Role value:** The stored role value is `therapist`. The older value `physio` was migrated out and must never be used in any comparison anywhere in the frontend codebase.

**Flow:**
- `lib/api-client.ts` centralizes all HTTP calls. On any 401, call the refresh endpoint once, store the new access token in `localStorage`, retry the original request. If the refresh call itself fails, clear `localStorage`, redirect to `/login`, and show a "Session expired" toast.
- On full page reload, read the token from `localStorage` and proceed — no silent refresh call needed since the token is persisted. If the stored token is expired (check `exp` claim client-side before any request), call the refresh endpoint before rendering `AppShell`.
- No component or feature module calls `fetch` or any HTTP primitive directly. Everything routes through `api-client.ts`.

**Login response envelope:**
```json
{
  "data": {
    "access_token": "...",
    "token_type": "bearer"
  }
}
```

**Security mitigations (given localStorage storage):**
- No PHI in the token — `sub`, `clinic_id`, `role` only.
- Strict Content-Security-Policy at the app level — primary XSS defense.
- No `dangerouslySetInnerHTML` anywhere in the codebase.
- Sanitize any user-supplied content before rendering.
- `npm audit` runs as part of CI on every PR.
- Any dev-only API base URL override must be gated behind `NODE_ENV === 'development'` before merge.

---

## 6. API Contract

All paths are relative to `NEXT_PUBLIC_API_BASE_URL` + `/api/v1`, configured once in `api-client.ts`. Feature modules never hardcode the prefix.

All endpoints require a valid JWT except the two public booking routes. All authenticated endpoints are clinic-scoped server-side via `ClinicGateMiddleware`.

| Screen | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/refresh` (path to confirm with Sparsh) |
| Patients | `GET /patients`, `POST /patients`, `GET /patients/{id}`, `PATCH /patients/{id}`, `DELETE /patients/{id}` |
| Leads | `GET /leads`, `POST /leads`, `PATCH /leads/{id}`, `DELETE /leads/{id}`, `POST /leads/{id}/convert` |
| Appointments | `GET /appointments`, `POST /appointments`, `GET /appointments/{id}`, `PATCH /appointments/{id}`, `DELETE /appointments/{id}` |
| Public booking | `GET /booking/branding/{clinic_slug}` *(unauthenticated)*, `POST /booking/request` *(unauthenticated)* |
| Appointment requests | `GET /appointment-requests`, `GET /appointment-requests/{id}`, `POST /appointment-requests/{id}/approve`, `POST /appointment-requests/{id}/reject` |
| Treatment sessions | `POST /treatments`, `GET /treatments`, `GET /treatments/{id}`, `PATCH /treatments/{id}`, `DELETE /treatments/{id}` |
| SOAP assessments | `POST /assessments`, `GET /assessments`, `GET /assessments/{id}`, `PATCH /assessments/{id}` |
| Packages (catalog) | `POST /packages`, `GET /packages`, `GET /packages/{id}`, `PATCH /packages/{id}`, `DELETE /packages/{id}` |
| Patient packages | `POST /patients/{patient_id}/packages`, `GET /patients/{patient_id}/packages`, `GET /patient-packages/{id}`, `PATCH /patient-packages/{id}`, `DELETE /patient-packages/{id}` |
| Invoices | `POST /invoices`, `GET /invoices`, `GET /invoices/{id}`, `PATCH /invoices/{id}`, `DELETE /invoices/{id}`, `GET /invoices/outstanding-balance`, `POST /invoices/{id}/pdf`, `GET /invoices/{id}/pdf` |
| Payments | `POST /invoices/{invoice_id}/payments`, `POST /payments`, `GET /payments`, `GET /payments/{id}`, `DELETE /payments/{id}` |
| Documents | `POST /patients/{patient_id}/documents`, `GET /patients/{patient_id}/documents`, `POST /documents`, `GET /documents`, `GET /documents/{id}`, `PATCH /documents/{id}`, `DELETE /documents/{id}`, `GET /documents/{id}/download` |
| Recycle bin | `GET /recycle-bin`, `POST /recycle-bin/{resource}/{id}/restore` |
| Analytics | `GET /analytics/overview` |
| Settings | `GET /settings/clinic`, `PATCH /settings/clinic`, `GET /audit-logs` |

**Recycle bin scope:** only `patients`, `leads`, `appointments`, `invoices`, and `patient_documents` have `deleted_at` in the schema. Do not surface `packages`, `patient_packages`, `payments`, `treatment_sessions`, or `soap_assessments` as recycle bin resource types.

**User management and Therapists directory:** No confirmed `/users` CRUD endpoints exist yet. These screens are spec'd but blocked pending Sparsh confirmation. Build the UI shell and stub the data layer — do not invent endpoint shapes.

---

## 7. Component Hierarchy

```text
AppRoot (Providers: Query, Theme, Zustand Store)
 └── AuthLayout         (/login)
 └── PublicLayout       (/booking/:clinicSlug — no sidebar, no auth)
 └── AppShell           (authenticated routes, RBAC context from JWT claims)
      ├── SidebarNavigation (collapsible, role-filtered via permissions.ts)
      ├── CommandBar    (Cmd+K palette)
      ├── MainContentArea
      │    └── Route Components
      └── GlobalOverlays
           ├── ToastContainer
           ├── ModalManager
           └── SlideOverDrawer
```

---

## 8. Folder Structure

```text
frontend/crm/src/
├── app/
│   ├── (auth)/           # /login
│   ├── (public)/         # /booking/:clinicSlug
│   ├── (dashboard)/      # all 9 authenticated routes
│   ├── globals.css
│   └── layout.tsx
├── components/
│   ├── ui/               # consumes @av-suite/design-tokens
│   └── layout/           # AppShell, Sidebar, Topbar, PageWrapper
├── config/
│   └── permissions.ts    # single source of truth for RBAC matrix
├── features/             # patients, leads, appointments, billing,
│                         # treatments, soap, analytics
├── hooks/
├── lib/
│   ├── api-client.ts     # all HTTP calls, token handling, refresh logic
│   ├── auth.ts           # JWT decode helpers, token read/write to localStorage
│   └── schemas/          # Zod schemas per resource
├── mocks/                # typed mock response objects for every resource
│   └── index.ts
├── store/                # Zustand: sidebar state, theme, decoded JWT claims
└── types/
    └── api.ts            # TypeScript types generated from schema

packages/design-tokens/   # sibling package — see Section 4
```

---

## 9. Data Shape Reference

These are the canonical field names from `schema.sql`. Zod schemas and TypeScript types must use these names exactly.

### 9.1 Patients
`id`, `clinic_id`, `user_id` (nullable), `first_name`, `last_name`, `date_of_birth` (DATE, nullable), `phone`, `gender`, `chief_complaint`, `referral_source`, `status` (`active | inactive | discharged`), `created_at`, `updated_at`, `deleted_at`

> **Note:** The patient name is `first_name` + `last_name` as separate fields — not a single `full_name`. Every form, list display, search, and display component must handle this split.

### 9.2 Leads
`id`, `clinic_id`, `name`, `phone`, `email` (nullable), `source`, `stage` (`new | contacted | qualified | converted | lost`), `assigned_to` (FK → users, nullable), `notes`, `converted_patient_id` (nullable), `created_at`, `updated_at`, `deleted_at`, `deleted_by`

### 9.3 Appointments
`id`, `clinic_id`, `patient_id`, `therapist_id`, `appointment_type` (varchar, default `consultation`), `scheduled_at`, `duration_minutes` (default 30), `status` (`scheduled | completed | cancelled | no_show`), `source` (`manual | public_booking`), `created_at`, `updated_at`, `deleted_at`, `deleted_by`

### 9.4 Treatment Sessions
`id`, `clinic_id`, `patient_id`, `appointment_id` (nullable), `therapist_id`, `treatment_date`, `pain_score` (nullable int), `treatment` (text), `home_advice` (nullable), `notes` (nullable), `created_at`, `updated_at`

### 9.5 SOAP Assessments
`id`, `clinic_id`, `patient_id`, `appointment_id` (nullable), `author_id` (FK → users), `specialty` (varchar), `diagnosis` (nullable), `is_reassessment` (boolean), `form_data` (JSONB), `finalized_at` (nullable timestamptz), `created_at`, `updated_at`

> **Note:** `form_data` is dynamic JSONB keyed by specialty. The exact field structure per specialty is to be confirmed with Onkar before Day 7 SOAP Notes work begins — this is a hard dependency for that day.

### 9.6 Packages
`id`, `clinic_id`, `name`, `total_sessions`, `price`, `validity_days`, `status` (`active | inactive | completed | expired | cancelled`), `created_at`, `updated_at`

### 9.7 Patient Packages
`id`, `clinic_id`, `patient_id`, `package_id` (nullable), `package_name`, `total_sessions`, `completed_sessions` (not `sessions_used`), `price`, `status`, `purchased_at`, `expires_at`, `created_at`, `updated_at`

### 9.8 Invoices
`id`, `clinic_id`, `patient_id`, `appointment_id` (nullable), `invoice_number` (varchar — auto-generated by backend), `issue_date`, `due_date` (nullable), `subtotal`, `discount_amount`, `tax_amount`, `total_amount`, `paid_amount`, `status` (`unpaid | paid | partial | draft | issued | cancelled`), `notes`, `created_at`, `updated_at`, `deleted_at`, `deleted_by`

> **Note:** `status` includes `partial` — the Zod type must include it even though the current UI pass does not build a partial-payment flow. The backend may return `partial` and the UI must render it without breaking.

### 9.9 Invoice Items
`id`, `clinic_id`, `invoice_id`, `description`, `quantity` (default 1), `unit_price`, `total_price`, `created_at`, `updated_at`

> The Create Invoice slide-over collects line items using these fields: `description` (text input), `quantity` (number input, default 1), `unit_price` (decimal input). `total_price` is computed client-side as `quantity × unit_price` before submit.

### 9.10 Payments
`id`, `clinic_id`, `invoice_id`, `patient_id`, `amount`, `payment_method` (`cash | upi | card | bank_transfer | insurance | other`), `status` (`completed | voided`), `payment_date`, `transaction_reference` (nullable), `notes` (nullable), `created_at`, `updated_at`

> **Note:** The payment date field is `payment_date` — not `paid_at`. Use the schema name in all Zod schemas and display components. Voiding a payment is a `status` change to `voided`, not expected to remove the row — confirm with Sparsh that `DELETE /payments/{id}` performs this status flip server-side rather than a hard delete.

### 9.11 Patient Documents
`id`, `clinic_id`, `patient_id`, `uploaded_by` (nullable), `treatment_id` (nullable), `file_url`, `file_type`, `file_size` (nullable int, bytes), `label`, `category` (`medical_report | prescription | lab_result | consent | other` — confirm full enum with Sparsh as the schema reference was truncated), `notes`, `created_at`, `updated_at`, `deleted_at`, `deleted_by`

### 9.12 Audit Logs
`id`, `clinic_id`, `user_id` (nullable), `action`, `entity_type`, `entity_id` (nullable), `details` (JSONB — not `metadata`), `created_at`

### 9.13 Users (for display only — no CRUD endpoints confirmed yet)
`id`, `clinic_id`, `email`, `role` (`admin | therapist | front_desk | patient`), `first_name`, `last_name`, `phone`, `is_active`, `created_at`, `updated_at`

---

## 10. Screens & Business Logic

### 10.1 Login
Clean centered card. Email + password form (React Hook Form + Zod). On submit: `POST /api/v1/auth/login`. On success: store `access_token` in `localStorage`, decode JWT claims (`sub`, `clinic_id`, `role`) into Zustand, redirect to `/dashboard`. No additional step after login.

### 10.2 Dashboard
KPI summary cards (today's appointments, pending tasks), today's schedule list, recent activity feed, contextual drawer for quick tasks.

### 10.3 Patient Directory / Workspace

**Directory:** Virtualized DataTable. Columns display `first_name + last_name` concatenated for readability. Search by name or phone. Filter by `status` only (no tag filter — `patients` table has no tags column). Column toggles. "Add Patient" CTA.

**Workspace:** sticky header (first + last name, demographics summary, primary actions), tabs:

| Tab | Maps to | Visible to |
|---|---|---|
| Timeline | activity feed across all resources | Admin, Therapist (own), Front Desk |
| Documents | `patient_documents` | Admin, Therapist (own), Front Desk |
| Treatments | `treatment_sessions` | Admin, Therapist (own) |
| SOAP Notes | `soap_assessments` | Admin, Therapist (own) |
| Assessments | `soap_assessments` with `is_reassessment: true` | Admin, Therapist (own) |
| Billing | invoices + payments for this patient | Admin, Front Desk |

**Add/Edit Patient slide-over fields:**
- Demographics: `first_name`, `last_name`, `date_of_birth` (date picker), `gender` (select), `chief_complaint` (textarea)
- Contact: `phone`, `referral_source`
- No insurance section — no insurance fields exist in the schema.

### 10.4 Treatment Sessions Tab
Records of physical therapy treatment. Form fields: `treatment_date` (datetime picker), `pain_score` (0–10 slider or number input, nullable), `treatment` (textarea, required), `home_advice` (textarea, nullable), `notes` (textarea, nullable). Linked to `appointment_id` optionally. Therapists see only their own sessions (server-filtered).

### 10.5 SOAP Notes Tab
Dynamic SOAP form. `form_data` structure is keyed by `specialty` — the exact field set per specialty must be confirmed with Onkar before this tab is built (hard dependency, flag if not resolved by Day 6).

Fields always present regardless of specialty: `specialty` (select), `diagnosis` (textarea), `is_reassessment` (boolean toggle — if true, the record appears under the Assessments tab, not SOAP Notes).

**Finalize flow:**
- Note is autosaved (debounced, 2s) via `PATCH /assessments/{id}` while `finalized_at` is null.
- "Finalize" action sets `finalized_at` to current timestamp. Note becomes read-only.
- Admin can re-open a finalized note. Re-opening writes an Audit Log entry (`action: 'soap_note.reopened'`, `entity_type: 'soap_assessments'`).
- Therapist cannot re-open finalized notes.

### 10.6 Leads Module
Kanban (New → Contacted → Qualified → Converted → Lost). Drag-and-drop stage transitions call `PATCH /leads/{id}`. Lead detail/update slide-over (name, phone, email, source, assigned\_to, notes). "Convert" action calls `POST /leads/{id}/convert`, moves lead to Converted column, shows the resulting patient record. Pre-filled Add-Patient handoff on convert is a future refinement — not built in this pass.

### 10.7 Appointments Module
Calendar (Day/Week/Month/List views). Filters by therapist and status. Create/Reschedule slide-over: patient search, `appointment_type` (text input, default `consultation`), date/time picker, duration, provider select. Double-booking soft warning: on therapist + scheduled\_at selection, check the already-fetched appointments list client-side for overlap — if overlap found, show inline warning ("This therapist is already booked at this time") but do not block submission. Contextual drawer for status changes on existing appointments.

### 10.8 Billing Module
Tabs: Invoices, Payments, Packages. All with DataTables.

**Create Invoice slide-over:** Patient select, line item builder (`description`, `quantity`, `unit_price` per row, `total_price` computed), `discount_amount`, `tax_amount`, computed `total_amount`, `notes`. `invoice_number` is auto-generated by the backend — do not collect it in the form.

**Sell Package slide-over:** Select from package catalog (`GET /packages`), confirm price, call `POST /patients/{patient_id}/packages`.

**Record Payment slide-over:** `amount`, `payment_method` (select from enum), `payment_date`, `transaction_reference` (optional), `notes`.

**Package expiry:** Once `expires_at` passes, show "Expired" badge on the patient package. Sessions become non-bookable in the appointment package-selector. No auto-forfeit — Admin manually extends `expires_at` via `PATCH /patient-packages/{id}` to reactivate.

**Invoice PDF:** `POST /invoices/{id}/pdf` generates, `GET /invoices/{id}/pdf` downloads. Both require a valid JWT. Access token is attached by `api-client.ts` — no separate handling needed.

**Current pass scope:** Full-payment flow only. The `partial` invoice status will be returned by the backend — render it as a badge but do not build partial-payment entry UI in this pass.

### 10.9 Public Booking (`/booking/:clinicSlug`)
Standalone branded page, no sidebar, no auth. Fetch branding via `GET /api/v1/booking/branding/{clinic_slug}` (clinic name, logo URL, branding color — nothing else). **Dependency:** confirm `clinics.slug` exists in the schema before starting this screen — see Q7. Multi-step form: Select Service → Select Time → Patient Details (`name`, `phone`, `age`, `gender`, `chief_complaint`, `notes`, `preferred_date`, `preferred_slot`). Submit calls `POST /api/v1/booking/request`. Show confirmation state on success. Debounce the submit button and disable after first click to prevent duplicate submissions.

### 10.10 Analytics
Filterable KPI/chart grid against `GET /api/v1/analytics/overview`. Date range filter. Therapists see own analytics only (server-filtered). Front Desk has no access to this module.

### 10.11 Settings
Inner sidebar: Clinic Settings, User Management, Audit Log.
- Clinic Settings: `GET/PATCH /settings/clinic` — branding fields.
- User Management: No confirmed `/users` CRUD endpoints yet. Build the UI shell (table + add user slide-over with fields `first_name`, `last_name`, `email`, `phone`, `role` select). Data layer is stubbed until Sparsh confirms endpoints.
- Audit Log: `GET /audit-logs` — read-only table of entries. Display `action`, `entity_type`, `entity_id`, `user_id`, `details`, `created_at`.

### 10.12 Recycle Bin
Lists soft-deleted items for `patients`, `leads`, `appointments`, `invoices`, `patient_documents` only. `GET /recycle-bin`. Restore action: `POST /recycle-bin/{resource}/{id}/restore`. Admin only.

### 10.13 Therapists Directory
Admin only. Lists users with `role = 'therapist'`. Displays salaries and total monthly payroll. No confirmed endpoint yet — build UI shell, stub data layer.

### Slide-over Forms — Shared Rules
All slide-overs: slide in from right, sectioned layout, sticky Save/Cancel bar at bottom. React Hook Form + Zod. Loading state on submit. Error state surfaced inline. Success closes the drawer and triggers a query invalidation.

---

## 11. Interaction Patterns, Responsive Behavior, Component Inventory, State Management

**Interaction:**
- Cmd/Ctrl+K command palette — wired on Day 2, command set populated per screen as features are built.
- Prefetched routing, no shell remount on navigation.
- Optimistic updates on mutations via TanStack Query.
- Inline editing for minor fields (e.g. appointment status badge).
- Slide-overs for complex forms; modals for confirmations and simple prompts.

**Responsive:**
- Desktop-first.
- Tablet: sidebar collapses to icons, tables collapse to cards, slide-overs go full-width (100vw).
- Mobile: bottom nav for core routes (Dashboard, Patients, Appointments). Complex authoring (SOAP Notes, Analytics) deferred to desktop. Quick views (today's schedule) are prioritized.

**Component inventory (built on `shadcn/ui`, themed via `@av-suite/design-tokens`):**
- Form controls: Input, Textarea, Select, Checkbox, RadioGroup, DatePicker, Switch, Slider
- Navigation: Tabs, Breadcrumb, DropdownMenu, ContextMenu, Menubar
- Data display: DataTable (TanStack Table), Card, Badge, Avatar, Tooltip, HoverCard, Accordion, virtualized ScrollArea
- Feedback: Skeleton, Toast, Alert, Dialog, Sheet
- Action: Button variants, Command menu

**State management:**
- TanStack Query — server state, caching, optimistic updates
- React Hook Form + Zod — all forms
- `useState` / `useReducer` — local UI state
- Zustand — sidebar open/close, theme, decoded JWT claims (`sub`, `clinic_id`, `role`) from `localStorage`
- URL search params — filters, pagination, active tab

---

## 12. Package Management

Prefer existing dependencies. Core stack covers nearly everything: Next.js 14, TypeScript, Tailwind, TanStack Query, Zustand, React Hook Form + Zod, `shadcn/ui`, Lucide.

Add a new package only when it provides substantial long-term value with active maintenance. Any new package added must be justified in the PR description: what it replaces or enables, and why the existing stack cannot do the job.

---

## 13. Engineering Standards

- Strict TypeScript throughout. No `any`.
- Feature-first architecture (`features/` folder — each feature owns its components, hooks, and API calls).
- No duplicated business logic. No duplicated UI components.
- Maximum component size: ~250 lines. Maximum custom hook: ~150 lines.
- Absolute imports via `tsconfig.json` paths.
- ESLint + Prettier enforced.
- No component calls `fetch` or any HTTP primitive directly — all requests go through `lib/api-client.ts`.

---

## 14. Performance Standards

- Lazy load feature modules.
- Route-level code splitting.
- Virtualize large tables (DataTable + ScrollArea).
- Memoize expensive computations.
- Skeleton loaders for all async content.
- Minimize unnecessary re-renders.
- Optimize bundle size and Core Web Vitals.

---

## 15. UX Standards

Every screen must include:
- Loading state
- Empty state
- Error state
- Success feedback
- Search (where applicable)
- Filters (where applicable)
- Primary CTA
- Undo for destructive actions where feasible

Healthcare-specific requirements:
- Optimize for long working hours — clear visual hierarchy, low eye strain.
- Large click targets.
- Fast patient switching via Cmd+K.
- Autosave long forms — SOAP Notes and any multi-field clinical entry (debounced, 2s).
- Never lose entered data — autosave plus confirmation dialog before navigating away from an unsaved form.
- High information density without clutter — dense DataTables, generous 8px-grid spacing.
- Prioritize speed over decorative visuals.

---

## 16. Micro-Interactions

- Button hover and active states
- Focus ring (visible, meets WCAG AA)
- Sidebar collapse animation
- Drawer slide-in transition
- Skeleton loading
- Toast stacking
- Table row hover
- Card hover
- Success animation on form submit
- Error shake/highlight on validation failure

---

## 17. AI / Code Generation Rules

- Never invent backend API endpoints.
- Never invent database fields.
- Never hardcode permissions — always reference `permissions.ts`.
- Never duplicate components or business logic.
- Follow the RBAC matrix exactly (Section 3).
- Use schema field names exactly as documented in Section 9.
- Prefer configuration over hardcoding.
- Optimize for maintainability, not shortcuts.
- Keep dependencies minimal (Section 12).
- See `CLAUDE.md` at the project root for the enforced version of these rules, including exact endpoint/field cheat sheets and a pre-commit self-check.

---

## 18. Scalability

- New roles: add to `permissions.ts` config — no component changes.
- New modules: add to `features/` and expose via sidebar config — AppShell does not change.
- New permissions: config edit only.
- Independent feature ownership: each `features/` module is self-contained.

---

## 19. Error Handling

- Human-readable error messages surfaced via toast.
- On 403 from backend: surface the error — never suppress it.
- Retry actions where appropriate.
- Offline-friendly UI states.
- Global error boundary at `AppRoot`.
- All API errors funnel through `api-client.ts` — every feature module receives the same error shape.

---

## 20. Frontend Security

- Token stored in `localStorage` — mitigated by CSP, no PHI in token, sanitized inputs, `npm audit` in CI.
- No `dangerouslySetInnerHTML` anywhere.
- Sanitize any user-supplied content before rendering.
- RBAC visibility enforced in every screen and component, not just navigation.
- All requests through `api-client.ts` — no ad hoc fetch calls.
- On 401: refresh once, retry. On refresh failure: clear localStorage, redirect to `/login`.
- Dev-only API base URL overrides gated behind `NODE_ENV === 'development'`.

---

## 21. Non-Goals

- Do not redesign business workflows.
- Do not invent backend endpoints — flag missing ones.
- Do not add unnecessary animations.
- Do not introduce heavy UI libraries beyond `shadcn/ui`.
- Do not duplicate business logic between frontend and backend.
- Do not build partial-payment entry UI in this pass.
- Do not build pre-filled patient handoff on lead convert in this pass.
- Do not optimize prematurely.

---

## 22. Open Questions (Resolve Before the Relevant Day)

| # | Question | Blocks | Owner |
|---|---|---|---|
| Q1 | Exact path and response shape of `POST /auth/refresh`, and whether it rotates the refresh token on each use | Day 3 | Sparsh |
| Q2 | `form_data` JSONB structure per specialty for `soap_assessments` | Day 7 | Onkar + Sparsh |
| Q3 | Full `document_category` enum values (schema reference was truncated) | Day 7 | Sparsh |
| Q4 | `/users` CRUD endpoints — do they exist or are they being built? | Day 11 | Sparsh |
| Q5 | Therapists directory endpoint — filtered `/users` or separate route? | Day 11 | Sparsh |
| Q6 | Salary and payroll fields on Therapists module — what are the data fields? | Day 11 | Onkar |
| Q7 | Does `clinics.slug` exist? Absent in the last schema review, but public booking assumes it resolves clinics by slug | Day 11 | Sparsh |

---

## 23. Detailed Phase Breakdown

### Phase 1 — Foundation (Days 1–3)

**Day 1 — Monorepo & tokens**
- Scaffold `frontend/crm/` as Next.js 14 (App Router) + TypeScript-strict + Tailwind.
- Scaffold `packages/design-tokens/` per Section 4. Implement all token files. Export Tailwind preset.
- Wire `frontend/crm/tailwind.config.ts` to consume the preset. No local overrides.
- ESLint + Prettier aligned to repo-wide rules. Absolute import paths via `tsconfig.json`.
- Create `src/mocks/index.ts` with typed mock objects for every resource in Section 9 (Patient, Lead, Appointment, TreatmentSession, SoapAssessment, Package, PatientPackage, Invoice, InvoiceItem, Payment, PatientDocument). These are the shapes all Day 4+ feature work builds against.

**Day 2 — Shell & routing**
- `AppRoot` (Query + Theme + Zustand providers), `AuthLayout`, `PublicLayout`, `AppShell`.
- `SidebarNavigation` — collapsible, role-filtered via `permissions.ts`.
- `CommandBar` shell — Cmd+K wired, empty command set for now.
- Route stubs for all 9 authenticated routes + `/login` + `/booking/:clinicSlug`.
- `config/permissions.ts` implemented from the full matrix in Sections 3.1–3.3 as a typed, exported config object.

**Day 3 — Auth**
- Login screen (React Hook Form + Zod, email + password).
- `lib/api-client.ts`: base client, `NEXT_PUBLIC_API_BASE_URL + /api/v1` prefix, attach Bearer token from `localStorage` on every request, 401 → refresh → retry once → hard logout on refresh failure.
- `lib/auth.ts`: read/write token to `localStorage`, decode JWT claims, check `exp` before AppShell renders.
- Zustand auth slice: stores decoded `sub`, `clinic_id`, `role` from JWT.
- **Done when:** login → token in `localStorage` → decoded claims in Zustand → protected route renders → page reload restores session without redirect to `/login`.

### Phase 2 — Core Data & Patient Workspace (Days 4–7)

**Day 4 — Data layer**
- TanStack Query provider + query key conventions per feature module.
- `DataTable` component: sorting, filtering, column visibility, virtualization.
- Zod schemas for all resources in Section 9 using exact schema field names.

**Day 5 — Patient Directory**
- Directory screen: `first_name + last_name` display, name/phone search, status filter, column toggles, "Add Patient" CTA.
- Wired to `GET /patients` and `POST /patients` (mock shape from `src/mocks/index.ts`).
- Add/Edit Patient slide-over: Demographics (`first_name`, `last_name`, `date_of_birth`, `gender`, `chief_complaint`) + Contact (`phone`, `referral_source`) sections. No insurance section.
- Loading, empty, error states.

**Day 6 — Patient Workspace shell**
- Sticky header: `first_name + last_name`, demographics summary, primary actions.
- Tabs rendered and visibility-gated per Section 10.3 RBAC rules: Timeline (stub), Documents, Treatments, SOAP Notes, Assessments, Billing (all stubs).
- RBAC enforcement: Treatments, SOAP Notes, Assessments tabs not rendered for Front Desk.

**Day 7 — Treatments, SOAP Notes, Documents**

*Prerequisite: Q2 (form\_data structure) and Q3 (document\_category enum) must be resolved.*

- **Treatments tab:** list of `treatment_sessions`, create/edit slide-over with `treatment_date`, `pain_score` (0–10), `treatment`, `home_advice`, `notes`.
- **SOAP Notes tab:** dynamic form keyed by `specialty`, `diagnosis`, `is_reassessment` toggle. Autosave (debounced 2s) while `finalized_at` is null. Finalize action. Admin-only re-open with Audit Log write.
- **Assessments tab:** same `soap_assessments` resource filtered where `is_reassessment: true`. Same finalize flow.
- **Documents tab:** drag-and-drop upload zone, `category` dropdown (enum-constrained), `label` input, list view with `file_size` display, download action (access token attached by `api-client.ts`). Client-side validation: file type and size before upload.
- **Done when:** a patient can be created, a treatment session recorded, a SOAP note authored/autosaved/finalized, a document uploaded and downloaded — all within the same clinic scope.

### Phase 3 — Remaining Modules & Polish (Days 8–12)

**Day 8 — Leads**
- Kanban (New/Contacted/Qualified/Converted/Lost), drag-and-drop.
- Lead detail/update slide-over.
- Convert action → `POST /leads/{id}/convert` → move to Converted column, show resulting patient.

**Day 9 — Appointments**
- Calendar views (Day/Week/Month/List), therapist/status filters.
- Create/Reschedule slide-over: patient search, `appointment_type`, date/time, duration, provider.
- Double-booking client-side soft warning (check fetched appointments list for overlap).
- Contextual drawer for status changes.

**Day 10 — Billing**
- Invoices / Payments / Packages DataTables.
- Create Invoice slide-over: line item builder (`description`, `quantity`, `unit_price`, computed `total_price`), discount, tax, total. `invoice_number` not collected — backend generates it.
- Sell Package, Record Payment slide-overs.
- Package expiry: "Expired" badge, non-bookable in appointment selector, Admin reactivation via `PATCH /patient-packages/{id}`.
- Invoice PDF generate + download.
- Render `partial` invoice status as a badge — no data entry UI for partial payments this pass.

**Day 11 — Public Booking, Analytics, Settings, Recycle Bin, Therapists**

*Prerequisite: Q4, Q5, Q6, Q7 must be resolved or these screens remain as shells.*

- `/booking/:clinicSlug`: branding fetch, multi-step form, confirmation state. Debounced submit. Confirm Q7 (`clinics.slug`) before starting.
- Analytics: KPI/chart grid, date-range filter, `GET /analytics/overview`.
- Settings: Clinic Settings form, User Management shell (stub data layer until Q4 resolved), Audit Log table.
- Recycle Bin: soft-deleted items list, restore action. Scope: patients, leads, appointments, invoices, patient\_documents only.
- Therapists directory: Admin-only, shell built, data layer stubbed until Q5/Q6 resolved.

**Day 12 — Polish & QA**
- Toasts and skeleton loaders across every remaining async operation.
- Accessibility pass: keyboard navigation, ARIA labels, focus management in slide-overs and modals.
- Micro-interactions per Section 16.
- Responsive QA: desktop, tablet, one mobile viewport.
- Confirm `physio` role value is not used anywhere in the codebase (`grep -r "physio"` check).
- **Done when:** every screen has loading/empty/error/success states, is keyboard-navigable, and the `physio` check passes clean.

---

*This is the single frontend build reference. All previous drafts, the original spec, and Addendum v2/v3 are superseded by this document for build purposes. `CLAUDE.md` enforces these rules during AI-assisted development. Backend data model, endpoint behavior, and infrastructure standards remain governed by the SRS.*
