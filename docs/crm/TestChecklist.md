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

## Module 1: Authentication & Session

### Backend API Tests

```bash
# Login with valid credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin1@clinic.com", "password": "password123"}'
# Expected: 200, body contains access_token and user object

# Get current user profile & permissions
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200, contains user, clinic branding, and permissions dictionary
```

**Checklist**:
- [ ] `POST /auth/login` with valid credentials → 200, returns `access_token` and `user`
- [ ] `POST /auth/login` with wrong password → 401 Unauthorized
- [ ] `POST /auth/login` with missing fields → 422 Unprocessable Entity
- [ ] `GET /auth/me` with valid token → 200, returns clinic name/logo and effective permissions
- [ ] `GET /auth/me` without token → 401 Unauthorized
- [ ] `GET /health` without any token → 200 (public route, no auth)
- [ ] `GET /docs` without any token → 200 (public route)

### Frontend Tests

- [ ] `/login` page renders correctly (no blank screen)
- [ ] Valid Admin login (`admin1@clinic.com`) → redirects to `/dashboard`, renders clinic branding and all 9 sidebar modules
- [ ] Valid Therapist login (`therapist1_1@clinic.com`) → redirects to `/dashboard`, renders clinic branding
- [ ] Valid Front Desk login (`frontdesk1@clinic.com`) → redirects to `/dashboard`, renders clinic branding
- [ ] Invalid login → error message displayed (not generic "something went wrong")
- [ ] After login, refreshing the page keeps the user logged in (token persists in localStorage)
- [ ] Visiting `/dashboard` while not logged in → redirects to `/login`
- [ ] Logout button clears token → redirect to `/login`
- [ ] After logout, browser back button does not show protected content

---

## Module 2: Dashboard

### Backend API Tests

```bash
TOKEN="your-access-token"
curl http://localhost:8000/api/v1/analytics/overview \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 for Admin with analytics.financial/clinical
```

**Checklist**:
- [ ] `GET /analytics/overview` with Admin token → 200, returns stats
- [ ] `GET /analytics/overview` with Therapist/Front Desk default token → 403 Forbidden
- [ ] All values are numbers (not null, not string)
- [ ] Clinic A's token cannot see Clinic B's analytics (multi-tenant isolation)

### Frontend Role-Based Tests

- [ ] **Admin**: Dashboard loads with all metric cards (financial revenue, performance, appointment queue)
- [ ] **Therapist (Default Deny-All)**: Shows "No Module Permissions Assigned" empty state banner; revenue and clinic-wide queues hidden
- [ ] **Therapist (Granted `appointments.view: own`)**: Shows only their own scheduled appointments for today
- [ ] **Front Desk (Default Deny-All)**: Shows "No Module Permissions Assigned" empty state banner
- [ ] Loading spinner shown during initial fetch
- [ ] If backend is down, error message shown (not indefinite spinner)

---

## Module 3: Patients

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
- [ ] `GET /patients` with Admin token → 200, returns all clinic patients
- [ ] `GET /patients` with Therapist token (default `none`) → 403 Forbidden
- [ ] `GET /patients` with Therapist token (scope: `own`) → 200, returns ONLY patients assigned to this therapist
- [ ] `GET /patients` with Therapist token (scope: `all`) → 200, returns all clinic patients
- [ ] `GET /patients/{id}` with valid scope → 200, returns single patient detail
- [ ] `GET /patients/{id}` of unassigned patient with Therapist scope `own` → 403 or 404
- [ ] `POST /patients` with `patients.create` granted → 201, creates patient with correct `clinic_id`
- [ ] `POST /patients` without `patients.create` → 403 Forbidden
- [ ] `PUT /patients/{id}` with `patients.edit` granted → 200, updates patient data
- [ ] `DELETE /patients/{id}` with `patients.delete` granted → 200, soft deletes to recycle bin
- [ ] `DELETE /patients/{id}` without `patients.delete` (e.g. Front Desk / Therapist) → 403 Forbidden

### Frontend Role-Based Tests

- [ ] **Admin**:
  - [ ] Patients menu item visible in sidebar
  - [ ] Patients list loads all patients
  - [ ] **+ Add Patient** button visible and functional
  - [ ] Patient detail page loads with all tabs (Timeline, Documents, Treatments, SOAP Notes, Billing)
  - [ ] Delete patient moves record to recycle bin
- [ ] **Therapist (Default Deny-All)**:
  - [ ] Patients menu item **hidden** from sidebar
  - [ ] Direct navigation to `/patients` displays `<AccessRestricted message="You do not have permission to view patients." />`
- [ ] **Therapist (Scope: `own`)**:
  - [ ] Patients menu item visible in sidebar
  - [ ] Table shows **only** their assigned patients; other patients not visible
  - [ ] If `patients.create` is `none`, **+ Add Patient** button is hidden
  - [ ] If `patients.delete` is `none`, Delete button is hidden
- [ ] **Front Desk (Granted view/create/edit, delete: none)**:
  - [ ] Patients menu item visible in sidebar
  - [ ] Table shows all clinic patients
  - [ ] **+ Add Patient** button visible and functional
  - [ ] Delete button is **hidden**

---

## Module 4: Appointments

### Backend API Tests

```bash
TOKEN="your-access-token"

# List appointments
curl http://localhost:8000/api/v1/appointments \
  -H "Authorization: Bearer $TOKEN"
```

**Checklist**:
- [ ] `GET /appointments` with Admin token → 200, returns clinic-scoped appointments
- [ ] `GET /appointments` with Therapist token (default `none`) → 403 Forbidden
- [ ] `GET /appointments` with Therapist token (scope: `own`) → 200, returns only therapist's appointments
- [ ] `GET /appointments` with Front Desk token (scope: `all`) → 200, returns all appointments
- [ ] `POST /appointments` with `appointments.create` → 201, creates appointment linked to patient + therapist
- [ ] `POST /appointments` without `appointments.create` → 403 Forbidden
- [ ] `PATCH /appointments/{id}` with `appointments.edit` → 200, reschedule works
- [ ] `DELETE /appointments/{id}` with `appointments.cancel` → 200, cancellation works

### Frontend Role-Based Tests

- [ ] **Admin**:
  - [ ] Appointments menu visible
  - [ ] Calendar and list views render all appointments
  - [ ] **+ Book Visit** button visible and functional
  - [ ] **Booking Requests** tab shows pending public booking requests
  - [ ] Approve / Reject actions update booking request status
- [ ] **Therapist (Default Deny-All)**:
  - [ ] Appointments menu **hidden** from sidebar
  - [ ] Direct navigation to `/appointments` displays `<AccessRestricted />`
- [ ] **Therapist (Scope: `own`)**:
  - [ ] Appointments menu visible
  - [ ] Calendar shows only sessions assigned to this therapist
- [ ] **Front Desk (Scope: `all`)**:
  - [ ] Appointments menu visible
  - [ ] Calendar shows all therapists' schedules
  - [ ] Can book visits and manage public booking requests

---

## Module 5: Analytics

### Backend API Tests

- [ ] `GET /analytics/overview` with Admin token → 200
- [ ] `GET /analytics/overview` with non-admin token → 403 Forbidden

### Frontend Role-Based Tests

- [ ] **Admin**: Analytics menu visible; overview charts, financial breakdown, and clinical reports render
- [ ] **Therapist (Default Deny-All)**: Analytics menu **hidden**; direct navigation to `/analytics` displays `<AccessRestricted />`
- [ ] **Front Desk (Default Deny-All)**: Analytics menu **hidden**; direct navigation to `/analytics` displays `<AccessRestricted />`

---

## Module 6: Billing & Invoices

### Backend API Tests

```bash
TOKEN="your-access-token"

# List invoices
curl http://localhost:8000/api/v1/invoices \
  -H "Authorization: Bearer $TOKEN"
```

**Checklist**:
- [ ] `GET /invoices` with Admin / Front Desk (`invoices.view: all`) → 200, returns billing records
- [ ] `GET /invoices` with Therapist (default `none`) → 403 Forbidden
- [ ] `POST /invoices` with `invoices.create` → 201, creates invoice
- [ ] `POST /invoices` without `invoices.create` → 403 Forbidden
- [ ] Billing totals match sum of individual line items
- [ ] Payment status update works (`POST /api/v1/payments`)

### Frontend Role-Based Tests

- [ ] **Admin**: Billing menu visible; Invoices, Payments, Packages tabs render; **+ Create Invoice** button works
- [ ] **Front Desk (Granted view/create)**: Billing menu visible; can view invoices, create invoices, and collect payments
- [ ] **Therapist (Negative Assertion)**: Billing menu **hidden**; direct navigation to `/billing` displays `<AccessRestricted message="Billing is restricted." />`

---

## Module 7: Leads

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

# Convert to patient
curl -X POST http://localhost:8000/api/v1/leads/{id}/convert \
  -H "Authorization: Bearer $TOKEN"
```

**Checklist**:
- [ ] `GET /leads` with Admin / Front Desk → 200, returns array
- [ ] `GET /leads` with Therapist (default `none`) → 403 Forbidden
- [ ] `POST /leads` with valid data → 201, lead created with correct `clinic_id`
- [ ] `PATCH /leads/{id}` → stage updated
- [ ] `POST /leads/{id}/convert` with `leads.convert` → 200, creates new Patient record

### Frontend Role-Based Tests

- [ ] **Admin**: Leads menu visible; List and Kanban views work; **+ Add Lead** and **Convert** buttons functional
- [ ] **Front Desk (Granted view/create/edit/convert)**: Leads menu visible; can add leads, update pipeline stages, and convert to patient
- [ ] **Therapist (Default Deny-All)**: Leads menu **hidden**; direct navigation to `/leads` displays `<AccessRestricted />`

---

## Module 8: Therapists Directory

### Backend API Tests

- [ ] `GET /users?role=therapist` with Admin token → 200, returns therapists with salary details
- [ ] `GET /users?role=therapist` with user having `users.view` but not `users.edit` → 200, salary fields omitted or masked
- [ ] `POST /users` (create staff member) without `users.create` → 403 Forbidden

### Frontend Role-Based Tests

- [ ] **Admin**:
  - [ ] Therapists menu visible in sidebar
  - [ ] Roster table lists all therapists
  - [ ] **+ Add Therapist** button is visible
  - [ ] **Monthly Salary column** is visible (Admin has `users.edit`)
- [ ] **Therapist (Granted `users.view: all`)**:
  - [ ] Therapists menu visible in sidebar
  - [ ] Colleague list visible
  - [ ] **Monthly Salary column is completely hidden**
  - [ ] **+ Add Therapist** button is hidden
- [ ] **Front Desk (Granted `users.view: all`)**:
  - [ ] Therapists menu visible in sidebar
  - [ ] **Monthly Salary column is completely hidden**
  - [ ] **+ Add Therapist** button is hidden

---

## Module 9: Recycle Bin

### Backend API Tests

- [ ] `GET /recycle-bin` with Admin token → 200, returns soft-deleted items
- [ ] `GET /recycle-bin` with Therapist/Front Desk token → 403 Forbidden
- [ ] `POST /recycle-bin/{id}/restore` with `recyclebin.restore` → 200, item restored
- [ ] `DELETE /recycle-bin/{id}` with `recyclebin.purge` → 200, item permanently purged

### Frontend Role-Based Tests

- [ ] **Admin**: Recycle Bin menu visible; deleted items list displays; **Restore** and **Purge** buttons functional
- [ ] **Therapist (Negative Assertion)**: Recycle Bin menu **hidden**; direct navigation to `/recycle-bin` displays `<AccessRestricted />`
- [ ] **Front Desk (Negative Assertion)**: Recycle Bin menu **hidden**; direct navigation to `/recycle-bin` displays `<AccessRestricted />`

---

## Module 10: Settings & User Management (Admin Exclusivity)

### Backend API Tests

```bash
TOKEN="your-admin-token"

# Update clinic branding
curl -X PUT http://localhost:8000/api/v1/settings/clinic \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Clinic Name"}'

# Update user permissions (all 64 capabilities supported)
curl -X PUT http://localhost:8000/api/v1/users/{therapist_id}/permissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"capability_key": "patients.view", "scope": "all"}]'
```

**Checklist**:
- [ ] `PUT /settings/clinic` with Admin token → 200, clinic name/logo updated
- [ ] `PUT /settings/clinic` with Therapist/Front Desk token → 403 Forbidden
- [ ] `PUT /users/{id}/permissions` with Admin token → 200, overrides saved
- [ ] `PUT /users/{id}/permissions` with Therapist/Front Desk token → 403 Forbidden (non-admin cannot edit permissions)

### Frontend Role-Based Tests

- [ ] **Admin**:
  - [ ] Settings menu visible in sidebar
  - [ ] All 3 tabs render: **Clinic Settings & Branding**, **User Management**, **Audit Log**
  - [ ] Can edit Clinic Name and Logo URL → updates sidebar branding immediately
  - [ ] In **User Management**, **Edit Permissions** button is visible for staff members
  - [ ] Clicking **Edit Permissions** opens slide-over drawer with all 64 capabilities and scopes (`NONE`, `OWN`, `ALL`)
  - [ ] Saving overrides persists and shows success toast
- [ ] **Therapist & Front Desk (Negative Assertion)**:
  - [ ] Settings menu **hidden** from sidebar
  - [ ] Direct navigation to `/settings` displays `<AccessRestricted message="Clinic settings are restricted." />`

---

## Dynamic Revocation & Real-Time Sync

- [ ] **Real-Time Revocation Flow**:
  1. Admin opens `/settings` → **User Management** → **Edit Permissions** for Therapist.
  2. Admin sets `patients.view` = `ALL` → Therapist logs in, sees "Patients" in sidebar and accesses `/patients` (200 OK).
  3. Admin changes `patients.view` = `NONE` and saves.
  4. Therapist navigates to `/patients` or refreshes → immediately blocked with `<AccessRestricted message="You do not have permission to view patients." />`, and "Patients" link disappears from sidebar.

---

## Multi-Tenant Isolation (Critical)

These tests MUST pass before any production release.

**Setup**: Use two test clinic accounts (Clinic 1 and Clinic 2).

- [ ] Clinic 1's JWT cannot fetch Clinic 2's patients (`GET /patients/{clinic2_patient_id}` returns 404, not 200)
- [ ] Clinic 1's JWT cannot fetch Clinic 2's leads
- [ ] Clinic 1's JWT cannot fetch Clinic 2's appointments
- [ ] Clinic 1's JWT cannot fetch Clinic 2's billing records
- [ ] Clinic 1 cannot convert Clinic 2's lead
- [ ] Every DB query touching tenant data filters by `clinic_id`

---

## Error States (Frontend)

- [ ] When backend is down: all list pages show error message (not blank, not spinner)
- [ ] When API returns 500: toast or error banner visible to user
- [ ] When API returns 403: meaningful `<AccessRestricted />` component displayed
- [ ] When API returns 404: "not found" state shown, not crash
- [ ] Form validation: required fields, format checks, visible inline errors
- [ ] All loading states: spinner or skeleton shown while fetching

---

## Regression Test (Run Before Every PR Merge)

1. [ ] `GET /health` → healthy
2. [ ] Login flow end-to-end for Admin, Therapist, and Front Desk
3. [ ] Dashboard loads with real data
4. [ ] Create + view + update a patient and lead
5. [ ] No console errors in browser dev tools on any page
6. [ ] No TypeScript compile errors: `cd frontend/crm && npx tsc --noEmit`
7. [ ] No Python import errors: `cd backend && python -c "from app.main import app"`
8. [ ] Pytest suite passes: `cd backend && pytest tests/test_scoped_permissions.py`
