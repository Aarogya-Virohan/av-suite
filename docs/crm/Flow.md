# Flow.md — Execution Trace
> **Purpose**: Trace exactly how execution moves between files and functions,
> for every major user action. If you don't know the full call chain, read this first.

---

## 1. Application Bootstrap (Cold Start)

```
Browser loads /dashboard
  │
  ▼
Next.js App Router
  app/layout.tsx
    └─ renders <Providers>   (providers/index.tsx)
         ├─ QueryClientProvider   ← TanStack Query setup
         ├─ ThemeProvider
         └─ children
              └─ (dashboard) route group
                   ├─ Layout checks auth via useAuthStore
                   │    └─ store/index.ts → initializeFromStorage()
                   │         └─ lib/auth.ts → getStoredToken()
                   │              └─ reads localStorage 'access_token'
                   └─ Renders dashboard/page.tsx  ← active open file
```

**Key rule**: `initializeFromStorage()` must be called once on mount (in providers or layout).
If it's not called, `isAuthenticated` stays `false` even with a valid stored token.

---

## 2. Login Flow

```
User fills LoginForm → clicks Submit
  │
  ▼
components/auth/LoginForm.tsx
  │  calls useMutation
  ▼
features/auth/api.ts (or inline mutation)
  │  POST /api/v1/auth/login  { email, password }
  ▼
lib/api-client.ts  (Axios — no interceptor needed on login, no token yet)
  │
  ▼
Backend: api/v1/auth.py → login()
  │   validates credentials
  │   issues JWT: { sub: user_id, clinic_id, role, exp }
  ▼
Response: { access_token, refresh_token, token_type }
  │
  ▼
Frontend onSuccess:
  useAuthStore.setToken(access_token)
    └─ store/index.ts → parseJwt(token)
         └─ extracts: userId, clinicId, role
         └─ sets isAuthenticated = true
  lib/auth.ts → storeToken(access_token)
    └─ localStorage.setItem('access_token', token)
  router.push('/dashboard')
```

---

## 3. Authenticated API Request (Example: Fetch Leads)

```
app/(dashboard)/leads/page.tsx
  │  calls hook
  ▼
features/leads/api.ts → useLeads(stage?)
  │  useQuery({ queryKey: ['leads', { stage }], queryFn: ... })
  ▼
queryFn executes:
  apiClient.get('/leads', { params: { stage } })
  │
  ▼
lib/api-client.ts
  requestInterceptor:
    getStoredToken() → reads localStorage
    config.headers.Authorization = `Bearer ${token}`
  │
  ▼
HTTP GET http://localhost:8000/api/v1/leads?stage=new
  │
  ▼
Backend middleware stack:
  1. CORSMiddleware   (checks origin header, sets CORS response headers)
  2. ClinicGateMiddleware
       ├─ checks if route is in PUBLIC_PATHS — /health, /docs, /auth/*
       ├─ if protected: decodes JWT
       │    └─ extracts clinic_id, user_id, role
       │    └─ stores in request.state
       └─ passes request to endpoint
  │
  ▼
api/v1/leads.py → list_leads(...)
  │   reads request.state.clinic_id (injected by middleware)
  ▼
services/leads.py → get_leads(db, clinic_id, stage)
  │
  ▼
repositories/leads.py → async db.execute(select(Lead)...)
  │
  ▼
PostgreSQL → rows returned
  │
  ▼
Response: { data: { items: [...], total: N } }
  │
  ▼
Frontend responseInterceptor:
  on success → returns response as-is
  on 401 → clearStoredTokens() + redirect /login
  on 403 → console.error (no redirect)
  │
  ▼
TanStack Query caches result under key ['leads', { stage }]
  │
  ▼
Component re-renders with data
```

---

## 4. Create Lead Flow

```
LeadForm submitted
  │
  ▼
features/leads/api.ts → useCreateLead()
  │  useMutation({ mutationFn: ... })
  ▼
mutationFn:
  apiClient.post('/leads', formValues)
  │
  ▼
Backend: api/v1/leads.py → create_lead(body: LeadCreate)
  │
  ▼
services/leads.py → create_lead(db, clinic_id, data)
  │
  ▼
repositories/leads.py → db.add(Lead(...))  →  db.commit()
  │
  ▼
Response: { data: Lead }
  │
  ▼
onSuccess:
  queryClient.invalidateQueries({ queryKey: ['leads'] })
    └─ TanStack Query refetches all lead queries automatically
```

---

## 5. Convert Lead → Patient Flow

```
LeadCard "Convert" button clicked
  │
  ▼
features/leads/api.ts → useConvertLead()
  │  POST /api/v1/leads/{id}/convert
  ▼
Backend: api/v1/leads.py → convert_lead(id)
  │
  ▼
services/leads.py → convert_lead(db, clinic_id, lead_id)
  │  1. Fetch lead record
  │  2. Create Patient record from lead data
  │  3. Update lead.stage = 'converted'
  │  4. Commit both in single transaction
  ▼
Response: { data: Patient }
  │
  ▼
Frontend onSuccess:
  invalidate ['leads']     ← refreshes lead list
  (optionally) navigate to /patients/{id}
```

---

## 6. 401 Unauthorized Flow (Token Expired)

```
Any apiClient request
  │
  ▼
Backend returns HTTP 401
  │
  ▼
lib/api-client.ts responseInterceptor:
  clearStoredTokens()
    └─ lib/auth.ts → localStorage.removeItem('access_token')
  if window.location.pathname !== '/login':
    window.location.href = '/login'
  │
  ▼
User lands on /login page
  store/index.ts → initializeFromStorage() finds no token
  isAuthenticated = false
```

---

## 7. Dashboard Analytics Flow

```
app/(dashboard)/dashboard/page.tsx
  │  const { data: overview } = useAnalyticsOverview()
  ▼
features/analytics/api.ts → useAnalyticsOverview()
  │  GET /api/v1/analytics/overview
  ▼
Backend: api/v1/analytics.py → get_overview()
  │  Aggregates:
  │  - COUNT(patients) WHERE clinic_id = ?
  │  - COUNT(appointments) WHERE date = today
  │  - SUM(billing) WHERE month = current
  │  - COUNT(leads) WHERE stage = 'pending'
  ▼
Response: {
  total_patients,
  active_appointments_today,
  monthly_revenue,
  pending_leads
}
  │
  ▼
page.tsx renders 4 KPI cards
```

---

## 8. Function Call Index (Quick Reference)

| Action | Frontend entry | Hook/mutation | Backend endpoint |
|---|---|---|---|
| Bootstrap auth | `layout.tsx` | `initializeFromStorage()` | — |
| Login | `login/page.tsx` | `useMutation → POST /auth/login` | `auth.py → login()` |
| Fetch leads | `leads/page.tsx` | `useLeads()` | `leads.py → list_leads()` |
| Create lead | `LeadForm` | `useCreateLead()` | `leads.py → create_lead()` |
| Convert lead | `LeadCard` | `useConvertLead()` | `leads.py → convert_lead()` |
| Fetch patients | `patients/page.tsx` | `usePatients()` | `patients.py → list_patients()` |
| Fetch dashboard | `dashboard/page.tsx` | `useAnalyticsOverview()` | `analytics.py → get_overview()` |
| Logout | Sidebar/menu | `useAuthStore.logout()` | — (token cleared client-side) |

---

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
