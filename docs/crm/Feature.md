# Feature.md — Feature Delivery Trail
> **Purpose**: Every feature has a start-to-finish trail. Requirements, decisions, implementation
> steps, and verification — all in one place. Anyone picking this up cold knows exactly what
> was built, why, and how to verify it works.

---

## Feature Status Legend

| Symbol | Meaning |
|---|---|
| 📋 Planned | Defined, not started |
| 🔨 In Progress | Active development |
| ✅ Complete | Built + verified |
| ⏸️ Paused | Started, blocked or deferred |
| ❌ Cancelled | Decided not to build |

---

## Feature Report Template

```markdown
### [FEAT-NNN] Feature Name
- **Status**: 📋 Planned
- **Priority**: P0 / P1 / P2
- **Owner**: [Developer / AI session that owns this]
- **Started**: YYYY-MM-DD
- **Completed**: YYYY-MM-DD

#### What It Does
[User-facing description: what problem does this solve?]

#### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

#### Backend Contract
- Endpoint: `METHOD /api/v1/...`
- Request schema: (paste or reference Pydantic schema)
- Response schema: (paste or reference)
- Auth required: Yes / No / Role-gated (specify role)

#### Implementation Plan
1. Step 1
2. Step 2

#### Files Created / Modified
| File | Type | Summary |
|---|---|---|
| path/to/file | Created / Modified | What changed |

#### Verification Steps
- [ ] Step 1
- [ ] Step 2

#### Decisions Made During Implementation
- Reference Decisions.md entries: D-XXX, D-YYY
```

---

## Feature Log

---

### [FEAT-001] Lead Pipeline (Kanban / List View)
- **Status**: ✅ Complete
- **Priority**: P0
- **Owner**: CRM team + AI sessions
- **Started**: Pre-2026-08-13
- **Completed**: Pre-2026-08-13 (exact date unknown — not documented at time of build)

#### What It Does
Allows clinic staff to track prospective patients (leads) through a pipeline:
New → Contacted → Interested → Converted / Lost.

#### Acceptance Criteria
- [x] View all leads with stage filter
- [x] Create a new lead (name, contact, source, initial stage)
- [x] Update a lead's stage
- [x] Convert a lead to a patient (creates Patient record)
- [ ] Delete / archive a lead (unverified — check recycle bin)

#### Backend Contract
- `GET /api/v1/leads?stage={stage}` → list leads
- `POST /api/v1/leads` → create lead
- `PATCH /api/v1/leads/{id}` → update stage
- `POST /api/v1/leads/{id}/convert` → convert to patient
- Auth required: Yes (clinic_id injected via JWT)

#### Implementation Plan (Completed)
1. Backend: `api/v1/leads.py` — CRUD endpoints
2. Frontend: `features/leads/api.ts` — hooks: `useLeads`, `useCreateLead`, `useUpdateLeadStage`, `useConvertLead`
3. Frontend: `features/leads/components/` — UI components
4. Frontend: `app/(dashboard)/leads/page.tsx` — page assembly

#### Files Created / Modified
| File | Type | Summary |
|---|---|---|
| `backend/app/api/v1/leads.py` | Created | Lead CRUD endpoints |
| `frontend/crm/src/features/leads/api.ts` | Created | TanStack Query hooks |
| `frontend/crm/src/features/leads/components/` | Created | Lead UI components |
| `frontend/crm/src/app/(dashboard)/leads/page.tsx` | Created | Leads page |

#### Verification Steps
- [x] `GET /api/v1/leads` returns leads for the authenticated clinic
- [x] `POST /api/v1/leads` creates a lead with correct clinic_id
- [x] Stage update persists on page refresh
- [ ] Lead conversion creates a Patient record and updates lead stage to 'converted'

#### Decisions Made During Implementation
- D-003: No direct Axios calls from components
- D-005: clinic_id from JWT, not from client

---

### [FEAT-002] Dashboard Overview (KPI Cards)
- **Status**: ✅ Complete
- **Priority**: P0
- **Owner**: CRM team + AI sessions
- **Started**: Pre-2026-08-13
- **Completed**: Pre-2026-08-13

#### What It Does
Landing page for the CRM showing 4 real-time KPIs:
- Total Patients
- Today's Appointments
- Monthly Revenue
- Pending Leads

#### Acceptance Criteria
- [x] 4 KPI cards visible on dashboard load
- [x] Real-time data from backend (not mock)
- [x] Loading state shown while data fetches
- [x] Error state shown if API fails
- [ ] BUG-001: `|| 0` fallback may mask loading vs empty states

#### Backend Contract
- `GET /api/v1/analytics/overview`
- Response: `{ total_patients, active_appointments_today, monthly_revenue, pending_leads }`
- Auth required: Yes

#### Files Created / Modified
| File | Type | Summary |
|---|---|---|
| `backend/app/api/v1/analytics.py` | Created | Analytics overview endpoint |
| `frontend/crm/src/features/analytics/api.ts` | Created | `useAnalyticsOverview()` hook |
| `frontend/crm/src/app/(dashboard)/dashboard/page.tsx` | Created | Dashboard page with KPI cards |

---

### [FEAT-003] Documentation Field Guide (15 Files)
- **Status**: ✅ Complete
- **Priority**: P1 (operational infrastructure)
- **Owner**: Claude Sonnet 4.6 (Thinking) — 2026-08-13 session
- **Started**: 2026-08-13
- **Completed**: 2026-08-13

#### What It Does
Creates 15 documentation files in `docs/crm/` that form the permanent field guide for
the CRM tool. Enables any AI session or developer to understand the system cold.

#### Files Created
| File | Purpose |
|---|---|
| `Architecture.md` | System map + stack + request lifecycle |
| `Flow.md` | Exact call chains for every major action |
| `Decisions.md` | Why behind every AI decision |
| `Constraints.md` | What AI must never touch |
| `Handover.md` | Session transfer protocol |
| `Bug.md` | Bug trail (this file) |
| `Feature.md` | Feature delivery trail |
| `EntryPoints.md` | Code entry points + execution order |
| `Rollback.md` | Rollback plans for risky operations |
| `TestChecklist.md` | Test checklists per module |
| `FieldGuide.md` | The 15 practices with full reasoning |
| `AIChangelog.md` | AI-specific change log |
| `ContextVersion.md` | Model + context version pins |

---

### [FEAT-004] Patient Management
- **Status**: 📋 Planned (Partially built — needs verification)
- **Priority**: P0
- **Owner**: TBD

#### What It Does
Full CRUD for patient records. Therapist-scoped access (therapists see only their patients).

#### Acceptance Criteria
- [ ] List patients (filtered by clinic + role)
- [ ] View patient detail (demographics, history)
- [ ] Create patient
- [ ] Edit patient
- [ ] Soft-delete patient (moves to recycle bin)

#### Backend Contract
- `GET /api/v1/patients` → list
- `GET /api/v1/patients/{id}` → detail
- `POST /api/v1/patients` → create
- `PUT /api/v1/patients/{id}` → update
- `DELETE /api/v1/patients/{id}` → soft delete

---

### [FEAT-005] Appointment Booking
- **Status**: 📋 Planned (Backend exists — frontend status TBD)
- **Priority**: P0

#### What It Does
Book, view, reschedule, cancel appointments. Linked to patient + therapist.

#### Backend Contract
- Full CRUD at `/api/v1/appointments`
- Booking via `/api/v1/booking` (separate booking flow)

---

### [FEAT-006] Billing Module
- **Status**: 📋 Planned (Backend exists — frontend status TBD)
- **Priority**: P1

#### What It Does
Billing records per patient per appointment. Invoice generation. Payment status tracking.

---

### [FEAT-007] Rev3 Capability System (Per-User Permission Overrides)
- **Status**: 📋 Planned
- **Priority**: P1
- **Owner**: Tarun Sisodia (Phase 2)

#### What It Does
Replaces rigid role-based access with per-user capability overrides. Each user has a row
in `user_permissions` (`clinic_id`, `user_id`, `capability_key`, `scope`) where scope
can be `none`, `own`, or `all`. The effective access level is resolved via
`effective_scope(user, capability_key)`.

#### Acceptance Criteria
- [ ] New migration: `user_permissions` table
- [ ] Backend `effective_scope()` resolver
- [ ] `GET /api/v1/analytics/my-performance` — therapist-scoped stats
- [ ] `GET /api/v1/analytics/clinic-financials` — admin-scoped financial view
- [ ] Frontend analytics page conditionally renders based on capability
- [ ] Permission management UI for admins
- [ ] Lockout guard: cannot revoke last `permissions.manage` or `users.manage` grant

#### Backend Contract
- `GET /api/v1/permissions` → list user capabilities
- `PUT /api/v1/permissions/{user_id}/{capability_key}` → set scope
- `GET /api/v1/analytics/my-performance` → own-scoped therapist view
- `GET /api/v1/analytics/clinic-financials` → admin financial view
- Auth required: Yes (admin for grant/revoke; any role for reading own analytics)

#### Decisions Made During Implementation
- Reference D-009 (Phase 2 deferral decision)

---

*Add new features above the closing line. Never delete completed feature entries.*
*Last updated: 2026-08-21 | Branch: feature/frontend-redesign-impl*


### [FEAT-008] Supabase Bucket Document Storage & Settings
- **Status**: ✅ Complete
- **Priority**: P0
- **Started**: 2026-08-22
- **Completed**: 2026-08-22

#### What It Does
Integrates Supabase Storage buckets for storing patient documents securely. Adds a clinic-level settings toggle (`is_documents_enabled`) to enable/disable access to documents per clinic. Fully integrated into the seeding and testing infrastructure.

#### Backend Contract
- `PATCH /api/v1/settings/clinic` -> toggle documents bucket
- `GET /api/v1/documents` -> list patient documents (403 if disabled)
- `GET /api/v1/documents/{id}/download` -> generate secure download URL

#### Implementation Plan (Completed)
1. Updated Clinic model to include `is_documents_enabled`.
2. Created `documents.py` router with RBAC and feature flag checks.
3. Updated `seed.py` and `wipe_db.py` to directly push and remove dummy PDFs from the Supabase `documents` bucket.

---

## 2026-08-22
- **Feature:** Dynamic UI Branding.
  **Description:** The dashboard layout (Sidebar and Top Navigation) now fully reflects the clinic's custom branding settings, including the brand color (accent), clinic name, and logo.
