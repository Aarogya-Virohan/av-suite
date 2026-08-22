# TestChecklist.md — Proof It Works
> **Purpose**: Test checklists per CRM module. Not claims that it works.
> Proof. Run through these and mark them. If something fails, log it in Bug.md.

---

## How to Use

1. Run through the checklist manually or with automated tests
2. Mark `[x]` for passing, `[F]` for failing
3. Log failures in `Bug.md` with a BUG-NNN reference
4. Do not mark a feature complete in `Feature.md` unless all P0 items pass

---

## Test Environment Setup

```bash
# Backend (from backend/ directory)
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (from frontend/crm/ directory)
npm run dev
# Opens http://localhost:3000

# Verify backend health
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

---

## Module 1: Authentication

### Backend API Tests

```bash
# Login with valid credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@clinic.com", "password": "yourpassword"}'
# Expected: 200, body contains access_token
```

**Checklist**:
- [ ] `POST /auth/login` with valid credentials → 200, returns `access_token`
- [ ] `POST /auth/login` with wrong password → 401 or 422
- [ ] `POST /auth/login` with missing fields → 422 Unprocessable Entity
- [ ] `GET /api/v1/patients` with valid token → 200 (not 401)
- [ ] `GET /api/v1/patients` without token → 401
- [ ] `GET /api/v1/patients` with expired token → 401
- [ ] `GET /health` without any token → 200 (public route, no auth)
- [ ] `GET /docs` without any token → 200 (public route)

### Frontend Tests

- [ ] `/login` page renders correctly (no blank screen)
- [ ] Valid login → redirects to `/dashboard`
- [ ] Invalid login → error message displayed (not generic "something went wrong")
- [ ] After login, refreshing the page keeps the user logged in (token persists in localStorage)
- [ ] Visiting `/dashboard` while not logged in → redirects to `/login`
- [ ] Logout button clears token → redirect to `/login`
- [ ] After logout, browser back button does not show protected content

---

## Module 2: Dashboard Analytics

### Backend API Tests

```bash
TOKEN="your-access-token"
curl http://localhost:8000/api/v1/analytics/overview \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200, body with total_patients, active_appointments_today, monthly_revenue, pending_leads
```

**Checklist**:
- [ ] `GET /analytics/overview` with valid token → 200
- [ ] Response contains all 4 fields: `total_patients`, `active_appointments_today`, `monthly_revenue`, `pending_leads`
- [ ] All values are numbers (not null, not string)
- [ ] Clinic A's token cannot see Clinic B's analytics (multi-tenant isolation)

### Frontend Tests

- [ ] Dashboard loads and shows 4 KPI cards
- [ ] KPI cards show actual numbers (not all 0)
- [ ] Loading spinner shown during initial fetch
- [ ] If backend is down, error message shown (not indefinite spinner)
- [ ] Numbers update after data changes (e.g., add a patient → refresh → count increases)

---

## Module 3: Leads

### Backend API Tests

```bash
TOKEN="your-access-token"

# List leads
curl http://localhost:8000/api/v1/leads \
  -H "Authorization: Bearer $TOKEN"

# Create a lead
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Lead", "phone": "9999999999", "stage": "new"}'

# Update stage
curl -X PATCH http://localhost:8000/api/v1/leads/{id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stage": "contacted"}'

# Convert to patient
curl -X POST http://localhost:8000/api/v1/leads/{id}/convert \
  -H "Authorization: Bearer $TOKEN"
```

**Checklist**:
- [ ] `GET /leads` → 200, returns array
- [ ] `GET /leads?stage=new` → only returns leads with stage=new
- [ ] `POST /leads` with valid data → 201, lead created with correct clinic_id
- [ ] `POST /leads` without auth → 401
- [ ] `PATCH /leads/{id}` → stage updated
- [ ] `PATCH /leads/{id}` with wrong clinic's ID → 404 or 403 (not the other clinic's lead)
- [ ] `POST /leads/{id}/convert` → lead stage = converted, new Patient record created

### Frontend Tests

- [ ] Leads page renders without error
- [ ] Leads list shows real data from API
- [ ] Create Lead form: submitting valid data creates a lead visible in list
- [ ] Create Lead form: submitting invalid data (missing name) shows inline error
- [ ] Stage update persists on page refresh
- [ ] Convert Lead: clicking convert creates a patient (verify by checking patients list)

---

## Module 4: Patients

### Backend API Tests

```bash
TOKEN="your-access-token"

# List patients
curl http://localhost:8000/api/v1/patients \
  -H "Authorization: Bearer $TOKEN"

# Create patient
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Test", "last_name": "Patient", "phone": "9000000001", "date_of_birth": "1990-01-01"}'
```

**Checklist**:
- [ ] `GET /patients` → 200, returns clinic-scoped list
- [ ] `GET /patients/{id}` → returns single patient with full detail
- [ ] `POST /patients` → creates patient with correct clinic_id
- [ ] `PUT /patients/{id}` → updates patient data
- [ ] `DELETE /patients/{id}` → soft delete (record moves to recycle bin, not deleted from DB)
- [ ] `GET /patients` after soft delete → deleted patient not in list
- [ ] Multi-tenant: Clinic A cannot access Clinic B's patients (try with different JWT)

### Frontend Tests

- [ ] Patients page renders
- [ ] Patient list shows real data
- [ ] Search / filter works
- [ ] Patient detail page loads correctly
- [ ] Edit patient → changes persist
- [ ] Delete patient → patient disappears from list, appears in recycle bin

---

## Module 5: Appointments

**Checklist**:
- [ ] `GET /appointments` → returns clinic-scoped appointments
- [ ] `POST /appointments` → creates appointment linked to patient + therapist
- [ ] Appointment datetime validated (no past dates unless explicitly allowed)
- [ ] `PATCH /appointments/{id}` → reschedule works
- [ ] `DELETE /appointments/{id}` → cancellation works
- [ ] Frontend: calendar/list view shows appointments
- [ ] Frontend: booking form shows available therapists

---

## Module 6: Billing

**Checklist**:
- [ ] `GET /billing` → returns billing records for clinic
- [ ] `POST /billing` → creates invoice linked to patient + appointment
- [ ] Billing totals match sum of individual line items
- [ ] Payment status update works
- [ ] Frontend: billing list renders
- [ ] Frontend: create invoice form works

---

## Module 7: Multi-Tenant Isolation (Critical)

These tests MUST pass before any production release.

**Setup**: Create two test clinic accounts (Clinic A and Clinic B) with data in each.

- [ ] Clinic A's JWT cannot fetch Clinic B's patients
- [ ] Clinic A's JWT cannot fetch Clinic B's leads
- [ ] Clinic A's JWT cannot fetch Clinic B's appointments
- [ ] Clinic A's JWT cannot fetch Clinic B's billing records
- [ ] Clinic A cannot convert Clinic B's lead
- [ ] Every DB query that touches tenant data is filtered by clinic_id

---

## Module 8: Error States (Frontend)

- [ ] When backend is down: all list pages show error message (not blank, not spinner)
- [ ] When API returns 500: toast or error banner visible to user
- [ ] When API returns 403: meaningful "you don't have permission" message
- [ ] When API returns 404: "not found" state shown, not crash
- [ ] Form validation: required fields, format checks, visible inline errors
- [ ] All loading states: spinner or skeleton shown while fetching

---

## Regression Test (Run Before Every PR Merge)

1. [ ] `GET /health` → healthy
2. [ ] Login flow end-to-end
3. [ ] Dashboard loads with real data
4. [ ] Create + view + update a lead
5. [ ] Convert lead → patient visible in patients list
6. [ ] No console errors in browser dev tools on any page
7. [ ] No TypeScript compile errors: `cd frontend/crm && npx tsc --noEmit`
8. [ ] No Python import errors: `cd backend && python -c "from app.main import app"`

---

*Last updated: 2026-08-13 | Branch: integration/crm-merge*
*Mark test results with date and tester name when running manually.*
