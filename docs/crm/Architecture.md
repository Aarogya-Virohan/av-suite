# Architecture.md — CRM System Map
> **Purpose**: The single diagram and narrative that tells you exactly what exists,
> where it lives, and how each layer talks to the next.
> Read this before touching **any** file. Nothing gets changed blind.

---

## 1. Repository Layout

```
av-suite/
├── backend/                   ← Shared FastAPI server (ALL tools share this)
│   ├── app/
│   │   ├── main.py            ← Entry point. Registers middleware + routers.
│   │   ├── api/v1/
│   │   │   ├── router.py      ← Master router — every endpoint prefix lives here
│   │   │   ├── auth.py        ← JWT issue / refresh / register
│   │   │   ├── patients.py    ← Patient CRUD
│   │   │   ├── leads.py       ← Lead pipeline
│   │   │   ├── appointments.py
│   │   │   ├── billing.py
│   │   │   ├── analytics.py
│   │   │   └── … (13 more route files)
│   │   ├── models/            ← SQLAlchemy ORM models
│   │   ├── schemas/           ← Pydantic request/response schemas
│   │   ├── services/          ← Business logic layer
│   │   ├── repositories/      ← DB access layer (async SQLAlchemy)
│   │   ├── middleware/
│   │   │   └── clinic_gate.py ← JWT + clinic-isolation middleware
│   │   ├── core/
│   │   │   └── config.py      ← All env vars / settings (single source)
│   │   ├── dependencies/      ← FastAPI Depends() factories
│   │   └── exceptions/        ← BaseAppException + handler
│   └── alembic/               ← Database migration scripts
│
├── frontend/
│   └── crm/                   ← CRM-specific Next.js 14 app
│       └── src/
│           ├── app/
│           │   ├── layout.tsx           ← Root layout (providers wrap here)
│           │   ├── (public)/login/      ← Unauthenticated login page
│           │   └── (dashboard)/         ← Auth-protected route group
│           │       ├── dashboard/page.tsx
│           │       ├── patients/page.tsx
│           │       ├── leads/page.tsx
│           │       ├── appointments/page.tsx
│           │       ├── billing/page.tsx
│           │       ├── analytics/page.tsx
│           │       └── settings/page.tsx
│           ├── components/
│           │   ├── layout/AppShell.tsx  ← Sidebar + topbar wrapper
│           │   ├── auth/                ← ProtectedRoute, guards
│           │   └── ui/                  ← Shared design primitives
│           ├── features/                ← Feature-scoped API + component bundles
│           │   ├── analytics/api.ts
│           │   ├── appointments/api.ts
│           │   ├── billing/api.ts
│           │   ├── leads/api.ts
│           │   ├── patients/api.ts
│           │   └── …
│           ├── lib/
│           │   ├── api-client.ts        ← Axios instance (single source of truth)
│           │   └── auth.ts              ← Token storage helpers
│           ├── store/index.ts           ← Zustand: useAuthStore + useUiStore
│           ├── providers/               ← QueryClientProvider, ThemeProvider
│           └── types/api.ts             ← Shared TypeScript interfaces
│
└── docs/
    ├── crm/                   ← All 15 field-guide files live here
    └── schema-visualizer.html ← DB schema visual explorer
```

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend framework | Next.js | 14 (App Router) | Pages, routing, SSR |
| Language (FE) | TypeScript | 5.x | Type safety |
| Styling | TailwindCSS | 3.x | Utility-first CSS |
| Server state | TanStack Query | v5 | API data fetching + caching |
| Client state | Zustand | 4.x | Auth + UI local state |
| HTTP client | Axios | 1.x | API calls (never raw fetch) |
| Backend framework | FastAPI | 0.x | REST API |
| Language (BE) | Python | 3.11+ | Backend logic |
| ORM | SQLAlchemy Async | 2.x | DB access |
| Database | PostgreSQL | 15 | Primary data store |
| Auth protocol | JWT | — | Bearer token auth |
| DB migrations | Alembic | — | Schema version control |

---

## 3. Request Lifecycle (Happy Path)

```
Browser
  │
  ▼
Next.js App Router  (app/(dashboard)/leads/page.tsx)
  │   calls feature hook
  ▼
features/leads/api.ts  → useLeads() / useCreateLead()
  │   calls apiClient
  ▼
lib/api-client.ts  (Axios instance)
  │   • request interceptor: attaches Bearer token from localStorage
  │   • response interceptor: 401 → redirect /login, 403 → log
  ▼
Backend: POST http://localhost:8000/api/v1/leads
  │
  ▼
main.py  (FastAPI app)
  │   middleware stack (bottom-up = last-added is first-executed):
  │   1. CORSMiddleware    ← handles preflight OPTIONS
  │   2. ClinicGateMiddleware ← validates JWT, injects clinic_id
  ▼
api/v1/router.py → leads.router
  │
  ▼
api/v1/leads.py  (endpoint function)
  │   calls service
  ▼
services/leads.py  (business logic)
  │   calls repository
  ▼
repositories/leads.py  (async SQLAlchemy)
  │
  ▼
PostgreSQL
```

---

## 4. Authentication Architecture

- **JWT is issued and validated entirely on the backend.**
- Frontend responsibilities (and ONLY these):
  1. Render login UI
  2. POST to `/api/v1/auth/login`, receive `access_token`
  3. Store token in `localStorage` via `lib/auth.ts → storeToken()`
  4. Attach token to every request via `api-client.ts` request interceptor
  5. On 401: clear tokens + redirect to `/login`
  6. Hide/show UI elements based on `useAuthStore().role` (UX only — never security)

> ⚠️ **NEVER validate permissions purely on the frontend. Backend enforces all rules.**

---

## 5. Authorization / RBAC

Roles available (from `types/api.ts → UserRole`):
- `admin` — full access
- `therapist` — own patients + appointments
- `receptionist` — lead intake, appointment booking
- `billing_staff` — billing module only

Permission checks flow:
1. `useAuthStore().role` → used for conditional UI rendering
2. Backend `ClinicGateMiddleware` + `Depends(get_current_user)` → enforces actual access

---

## 6. State Management Rules

| Data type | Where it lives | Tool |
|---|---|---|
| Server data (patients, leads, etc.) | TanStack Query cache | `useQuery` / `useMutation` |
| Auth token + user claims | Zustand `useAuthStore` | `store/index.ts` |
| Sidebar open/close, theme | Zustand `useUiStore` | `store/index.ts` |
| Form state | React local state | `useState` / `useForm` |

> ❌ Do NOT duplicate server state into Zustand.
> ❌ Do NOT call `axios` directly from a component — always go through `features/*/api.ts`.

---

## 7. Environment Variables

### Backend (`backend/.env`)
```
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=...
CORS_ORIGINS=http://localhost:3000
API_V1_PREFIX=/api/v1
DEBUG=true
```

### Frontend (`frontend/crm/.env.local`)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 8. What Shares the Backend

The backend is **NOT CRM-specific**. It currently serves:
- CRM frontend (`frontend/crm/`)
- Potentially: Posture tool (`app/api/v1/posture.py`)
- Potentially: Exercise tool (`app/api/v1/exercises.py`)

> ⚠️ **Any backend change ripples to all tools. Always announce backend changes before making them.**

---

## 9. Module Ownership Map

| Domain | Backend file | Frontend feature |
|---|---|---|
| Auth | `api/v1/auth.py` | `lib/auth.ts`, `store/index.ts` |
| Patients | `api/v1/patients.py` | `features/patients/api.ts` |
| Leads | `api/v1/leads.py` | `features/leads/api.ts` |
| Appointments | `api/v1/appointments.py` | `features/appointments/api.ts` |
| Billing | `api/v1/billing.py` | `features/billing/api.ts` |
| Analytics | `api/v1/analytics.py` | `features/analytics/api.ts` |
| Assessments | `api/v1/assessments.py` | `features/assessments/api.ts` |
| Treatments | `api/v1/treatments.py` | `features/treatments/api.ts` |
| Users | `api/v1/users.py` | `features/users/api.ts` |
| Settings | `api/v1/settings.py` | — |
| Audit | `api/v1/audit.py` | `features/audit/api.ts` |
| Recycle Bin | `api/v1/recycle_bin.py` | — |

---

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
