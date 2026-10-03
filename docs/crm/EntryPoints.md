# EntryPoints.md — Code Entry Points and Execution Order
> **Purpose**: Know exactly where code starts and what it calls next.
> These are the anchors — the files you read when orientation is lost.

---

## Frontend Entry Points

### 1. Application Root
**File**: [`frontend/crm/src/app/layout.tsx`](file:///home/Dont_Fucking_Quit/av-suite/frontend/crm/src/app/layout.tsx)

```
Browser request arrives
  └─ Next.js: app/layout.tsx          ← ROOT ENTRY
       ├─ Loads global fonts + CSS
       ├─ Wraps all pages in <Providers>
       │    └─ providers/index.tsx
       │         ├─ QueryClientProvider  (TanStack Query)
       │         └─ ThemeProvider
       └─ Renders {children}           ← page.tsx of active route
```

**What it owns**: Global layout, provider tree setup.
**What it must NOT own**: Business logic, API calls, feature-specific state.

---

### 2. Auth Initialization Entry Point
**File**: [`frontend/crm/src/store/index.ts`](file:///home/Dont_Fucking_Quit/av-suite/frontend/crm/src/store/index.ts)

```
useAuthStore.initializeFromStorage()   ← called on mount by layout/provider
  ├─ lib/auth.ts → getStoredToken()
  │    └─ localStorage.getItem('access_token')
  └─ lib/auth.ts → parseJwt(token)
       └─ decodes JWT payload: { sub, clinic_id, role, exp }
  └─ sets: token, userId, clinicId, role, isAuthenticated
```

**When is it called?**: In `app/layout.tsx` or root provider, inside a `useEffect` on mount.
**What breaks if it's not called**: `isAuthenticated` stays `false` on page refresh even with a valid token. User gets redirected to login incorrectly.

---

### 3. Authenticated HTTP Layer
**File**: [`frontend/crm/src/lib/api-client.ts`](file:///home/Dont_Fucking_Quit/av-suite/frontend/crm/src/lib/api-client.ts)

```
const apiClient = axios.create({ baseURL: '/api/v1' })

Request Interceptor (every outgoing request):
  getStoredToken() → attach as Authorization: Bearer <token>

Response Interceptor (every response):
  success → pass through
  401 → clearStoredTokens() + redirect to /login
  403 → console.error (logged, not redirected)
  any error → extract backend's 'detail' field → set as error.message
```

**This is the ONLY Axios instance**. All feature API files import `apiClient` from here.

---

### 4. Feature API Entry Points
Each feature owns its own hook file. These are the only places components should import data from.

| Feature | File | Entry Hooks |
|---|---|---|
| Analytics | `features/analytics/api.ts` | `useAnalyticsOverview()` |
| Leads | `features/leads/api.ts` | `useLeads()`, `useCreateLead()`, `useUpdateLeadStage()`, `useConvertLead()` |
| Patients | `features/patients/api.ts` | `usePatients()`, `usePatient(id)`, `useCreatePatient()` |
| Appointments | `features/appointments/api.ts` | `useAppointments()`, `useCreateAppointment()` |
| Billing | `features/billing/api.ts` | `useBillingRecords()`, `useCreateBillingRecord()` |

---

### 5. Page Entry Points (Route Hierarchy)

```
app/
├─ layout.tsx                     ← Root (always runs)
├─ page.tsx                       ← Redirects / to /dashboard
├─ (public)/
│   └─ login/page.tsx             ← Unauthenticated entry (no JWT needed)
└─ (dashboard)/                   ← Protected route group
    ├─ [layout.tsx]               ← Auth guard lives here (check isAuthenticated)
    ├─ dashboard/page.tsx         ← KPI cards, useAnalyticsOverview()
    ├─ leads/page.tsx             ← Lead kanban / table, useLeads()
    ├─ patients/page.tsx          ← Patient list, usePatients()
    ├─ appointments/page.tsx      ← Calendar / list, useAppointments()
    ├─ billing/page.tsx           ← Billing records, useBillingRecords()
    ├─ analytics/page.tsx         ← Analytics charts
    ├─ settings/page.tsx          ← Clinic settings
    ├─ therapists/page.tsx        ← Therapist management
    └─ recycle-bin/page.tsx       ← Soft-deleted records
```

---

## Backend Entry Points

### 1. Application Entry
**File**: [`backend/app/main.py`](file:///home/Dont_Fucking_Quit/av-suite/backend/app/main.py)

```
uvicorn app.main:app                  ← PROCESS ENTRY POINT

main.py execution order (module load):
  1. FastAPI() instance created
  2. Exception handler registered (BaseAppException)
  3. ClinicGateMiddleware added
  4. CORSMiddleware added
  5. api_router included at prefix /api/v1
  6. posture_router included (no prefix — its routes have full paths)
  7. /health endpoint registered

Runtime (per request):
  CORSMiddleware runs first (handles preflight OPTIONS)
  → ClinicGateMiddleware (validates JWT, injects clinic context)
  → Route handler
```

---

### 2. Router Entry Point
**File**: [`backend/app/api/v1/router.py`](file:///home/Dont_Fucking_Quit/av-suite/backend/app/api/v1/router.py)

```
api_router = APIRouter()

Routers registered WITH prefix (prefix added by router.py):
  /auth          ← auth.py
  /exercises     ← exercises.py
  /patients      ← patients.py
  /posture       ← posture.py
  /prescriptions ← prescriptions.py
  /leads         ← leads.py
  /appointments  ← appointments.py
  /treatments    ← treatments.py
  /assessments   ← assessments.py
  /users         ← users.py

Routers registered WITHOUT extra prefix (routes define their own full paths):
  billing.py, booking.py, documents.py, audit.py,
  recycle_bin.py, settings.py, analytics.py
```

**Important**: The "no prefix" routers already include their resource path in their route decorators.
Adding a prefix again would double it (e.g., `/billing/billing/{id}`).

---

### 3. Execution Order Per Request (Detailed)

```
HTTP request arrives at port 8000
  │
  ▼
uvicorn ASGI server
  │
  ▼
FastAPI app (main.py)
  │
  ▼
[1] CORSMiddleware
    ├─ OPTIONS request → returns CORS headers, done
    └─ other methods → adds CORS headers, continues
  │
  ▼
[2] ClinicGateMiddleware (middleware/clinic_gate.py)
    ├─ Is path in PUBLIC_PATHS?  → yes: skip auth, continue
    └─ no: extract + verify JWT
         ├─ invalid/expired → 401 Unauthorized
         └─ valid:
              request.state.user_id = claims["sub"]
              request.state.clinic_id = claims["clinic_id"]
              request.state.role = claims["role"]
              continue
  │
  ▼
[3] Route handler (e.g., api/v1/leads.py → list_leads)
    ├─ reads request.state.clinic_id
    ├─ calls service layer
    └─ service calls repository layer
  │
  ▼
[4] Repository (repositories/leads.py)
    └─ async SQLAlchemy query → PostgreSQL
  │
  ▼
[5] Response serialized by Pydantic schema
    └─ returned as JSON
```

---

### 4. Authentication Endpoints
**File**: [`backend/app/api/v1/auth.py`](file:///home/Dont_Fucking_Quit/av-suite/backend/app/api/v1/auth.py)

| Endpoint | Method | Auth Required | Purpose |
|---|---|---|---|
| `/api/v1/auth/login` | POST | No | Issue JWT |
| `/api/v1/auth/register` | POST | No | Create user |
| `/api/v1/auth/refresh` | POST | Refresh token | Renew access token |
| `/api/v1/auth/logout` | POST | Yes | Invalidate token |

---

### 5. Key Environment Variables That Affect Execution

| Variable | Where | Effect |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | frontend `.env.local` | `api-client.ts` base URL |
| `DATABASE_URL` | backend `.env` | SQLAlchemy engine |
| `SECRET_KEY` | backend `.env` | JWT signing key |
| `CORS_ORIGINS` | backend `.env` | Allowed frontend origins |
| `DEBUG` | backend `.env` | uvicorn auto-reload |
| `API_V1_PREFIX` | backend `.env` | Router prefix (default `/api/v1`) |

---

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
