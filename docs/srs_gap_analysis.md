# SRS Gap Analysis

Source of truth: `AV_Suite_CRM_SRS.pdf`.

Review scope: backend only, before any feature implementation.

Legend:

- ✅ Already compliant
- 🟡 Needs modification
- 🔴 Missing

## Summary

The backend is only partially aligned with the SRS. The current codebase has the FastAPI scaffold, async SQLAlchemy foundation, Alembic, base mixins, generic repository/service abstractions, and a single Clinic model. However, the SRS requires a multi-tenant, clinic-scoped CRM with shared auth, middleware, routing, and a much larger data model. Most feature-level requirements are still missing.

The biggest gaps are:

- clinic-scoped multi-tenant enforcement
- shared JWT/bcrypt auth flow
- ClinicGateMiddleware integration
- SRS-aligned data model for Clinics, Users, Patients, Leads, Appointments, Billing, Documents, and Audit Logs
- API router surface under `/api/v1/`
- soft-delete/recycle-bin support
- audit logging
- response-envelope pattern

## Requirement Review

### 1. Project structure

| Requirement | Status | Notes |
|---|---:|---|
| Shared backend layout in `backend/app/` with routers registered through `api/v1/__init__.py` | 🟡 | The package structure exists, but `app/api/v1/__init__.py` is empty and no routers are registered. `app/main.py` is still a thin scaffold with only a root health route. |
| Reuse the shared backend instead of recreating the app | ✅ | The repository is using the shared backend workspace and does not duplicate the monorepo app entrypoint. |

### 2. Database models

| Requirement | Status | Notes |
|---|---:|---|
| Clinics foundation table with `id`, `name`, `branding_logo_url`, `branding_color`, `plan_tier`, `is_partner_clinic`, `created_at`, `updated_at` | 🟡 | A `Clinic` model exists, but its fields do not match the SRS foundation schema. It currently contains contact-oriented fields and a `ClinicStatus` enum that the SRS does not define. |
| Users foundation table with `clinic_id`, `name`, `email`, `phone`, `password_hash`, `role`, `is_active`, timestamps | 🔴 | No `User` model exists. |
| Patients table extending the shared model with `clinic_id`, intake fields, and status | 🔴 | No `Patient` model exists. |
| Leads table | 🔴 | Missing. |
| Appointments table | 🔴 | Missing. |
| AppointmentRequests table | 🔴 | Missing. |
| Assessments and Treatments tables for SOAP notes | 🔴 | Missing. |
| Packages and PatientPackages tables | 🔴 | Missing. |
| Invoices and Payments tables | 🔴 | Missing. |
| PatientDocuments table | 🔴 | Missing. |
| AuditLogs table | 🔴 | Missing. |

### 3. Enums

| Requirement | Status | Notes |
|---|---:|---|
| Clinic plan tier enum: `free`, `practice`, `clinical_pro` | 🔴 | Not present. |
| User role enum: `admin`, `therapist`, `front_desk` | 🔴 | Not present. |
| Patient status enum: `active`, `inactive`, `discharged` | 🔴 | Not present. |
| Lead stage enum: `new`, `contacted`, `qualified`, `converted`, `lost` | 🔴 | Not present. |
| Appointment status enum: `scheduled`, `completed`, `cancelled`, `no_show` | 🔴 | Not present. |
| Appointment source enum: `manual`, `public_booking` | 🔴 | Not present. |
| AppointmentRequest status enum: `pending`, `approved`, `rejected` | 🔴 | Not present. |
| Invoice status enum: `unpaid`, `paid`, `partial` | 🔴 | Not present. |
| Payment method enum: `cash`, `upi`, `card` | 🔴 | Not present. |
| Current `ClinicStatus` enum | 🟡 | The enum exists, but it is not part of the SRS schema and should be replaced or removed in favor of the required SRS enums. |

### 4. Repository pattern

| Requirement | Status | Notes |
|---|---:|---|
| Generic `BaseRepository` exists | ✅ | Present. |
| Repository layer is async and database-only | ✅ | Present at the abstraction level. |
| Repositories must be clinic-scoped and support SRS tables | 🟡 | The base abstraction exists, but there are no entity repositories or clinic-filtered query methods yet. The current generic API is not enough for SRS requirements because every query must be scoped by `clinic_id`. |
| Repositories must not commit or contain business logic | ✅ | Present in the base design. |

### 5. Service pattern

| Requirement | Status | Notes |
|---|---:|---|
| Generic `BaseService` exists | ✅ | Present. |
| Services own transactions and business rules | 🟡 | The abstraction exists, but no domain services exist yet and no transaction ownership is implemented. |
| Services should coordinate repositories and stay SQLAlchemy-free | ✅ | Present in the base design. |

### 6. Migrations

| Requirement | Status | Notes |
|---|---:|---|
| Single Alembic head before continuing | ✅ | `alembic heads` currently reports one head only. |
| Migration history matches SRS foundation schema | 🟡 | There is one initial clinic migration, but it does not match the SRS clinic foundation fields and does not add Users or the rest of the CRM schema. |

### 7. Middleware

| Requirement | Status | Notes |
|---|---:|---|
| Existing `ClinicGateMiddleware` must be reused | 🔴 | No clinic gate middleware is implemented in this backend. |
| Every CRM request touching patient data must pass through clinic scoping | 🔴 | Missing because the middleware and supporting dependencies do not exist. |

### 8. Authentication

| Requirement | Status | Notes |
|---|---:|---|
| JWT + bcrypt auth reused from the shared backend | 🔴 | `app/core/security.py` is empty, so the shared auth flow is not present here yet. |
| Login endpoint issuing JWT with `clinic_id` and role claims | 🔴 | Missing. |
| Passwords stored only as bcrypt hashes | 🔴 | Not implemented because the `User` model and auth flow are missing. |

### 9. Dependency injection

| Requirement | Status | Notes |
|---|---:|---|
| Async session dependency | ✅ | The database module already provides an async session factory and FastAPI dependency. |
| Clinic-aware auth/current-user dependencies | 🔴 | Missing. `app/core/dependencies.py` is empty. |
| Dependencies should feed routers and services without FastAPI leakage into services | 🟡 | The architectural direction is correct, but the actual dependency layer is not implemented. |

### 10. API routing

| Requirement | Status | Notes |
|---|---:|---|
| `/api/v1/` router surface with patients, leads, appointments, booking, treatments, billing, documents, analytics | 🔴 | Missing. `app/api/v1/__init__.py` is empty and `app/main.py` registers no API routers. |
| Patients endpoints | 🔴 | Missing. |
| Leads endpoints | 🔴 | Missing. |
| Appointments endpoints | 🔴 | Missing. |
| Public booking endpoints | 🔴 | Missing. |
| Treatments / SOAP endpoints | 🔴 | Missing. |
| Billing endpoints | 🔴 | Missing. |
| Patient document endpoints | 🔴 | Missing. |
| Recycle bin, audit logs, analytics endpoints | 🔴 | Missing. |
| Response-envelope pattern | 🔴 | Missing. The current root route returns a plain dict, not the SRS envelope pattern. |

### 11. Database schema

| Requirement | Status | Notes |
|---|---:|---|
| Real foreign keys throughout | 🔴 | Only the initial Clinic migration exists; the rest of the relational schema is missing. |
| Clinic scoping via `clinic_id` on all tenant-owned tables | 🔴 | Missing. |
| Proper enums instead of free-text dropdown values | 🔴 | Missing for SRS enums. |
| Timestamps on all required tables | 🔴 | Missing across the SRS tables that do not yet exist. |

### 12. Soft delete support

| Requirement | Status | Notes |
|---|---:|---|
| Soft delete via `deleted_at` for recycle-bin items | 🔴 | Missing. |
| Recycle bin list and restore flow | 🔴 | Missing. |
| No hard delete for patient-related records | 🔴 | Not enforced yet. |

### 13. Clinic scoping

| Requirement | Status | Notes |
|---|---:|---|
| Every table and every query scoped by `clinic_id` | 🔴 | Not implemented anywhere in the current backend. |
| ClinicGateMiddleware enforces tenant separation | 🔴 | Missing. |
| Tests proving clinic isolation | 🔴 | No tests exist yet for isolation. |

### 14. Audit logging

| Requirement | Status | Notes |
|---|---:|---|
| AuditLog model | 🔴 | Missing. |
| Write audit log entries on create/update/delete of Patients, Invoices, Appointments | 🔴 | Missing. |
| Audit log visible in settings | 🔴 | Missing. |

### 15. File and document handling

| Requirement | Status | Notes |
|---|---:|---|
| Private Supabase Storage only | 🔴 | Missing. |
| No public file/document routes | 🔴 | Missing. |
| Authenticated clinic-scoped download endpoints for PDFs/documents | 🔴 | Missing. |
| WeasyPrint invoice PDF generation reused | 🔴 | The PDF service is not wired into any billing flow yet. |

### 16. Non-functional requirements

| Requirement | Status | Notes |
|---|---:|---|
| Security: JWT on patient data routes | 🔴 | Missing. |
| Security: bcrypt only | 🔴 | Missing auth implementation. |
| Performance: indexes on `clinic_id`, `patient_id`, and WHERE-filtered columns | 🔴 | Missing on SRS tables because those tables do not yet exist. |
| Data integrity: DB-enforced foreign keys | 🔴 | Missing for the SRS schema. |
| Testing: isolation tests for every new endpoint | 🔴 | Missing. |

### 17. Deliverables and process

| Requirement | Status | Notes |
|---|---:|---|
| PR to `dev` branch | 🔴 | Not part of the current backend state. |
| Validation notes for billing math | 🔴 | Not applicable yet because billing is not implemented. |
| Screen recordings of end-to-end flow | 🔴 | Not applicable yet. |
| Phase checklist in PR description | 🔴 | Not applicable yet. |

## Architecture assessment

### BaseRepository

Status: ✅ Keep, but modify for tenant-aware query helpers as the domain grows.

Reasoning: The SRS wants a layered architecture with repositories below services. A generic async base repository is useful and aligns with that pattern. It should remain the foundation, but entity repositories must add clinic-scoped query methods and soft-delete-aware helpers.

### BaseService

Status: ✅ Keep, but modify.

Reasoning: The SRS explicitly separates services from repositories and expects business rules to live in services. A generic base service is a good fit, but actual clinic-aware and transaction-aware services still need to be implemented.

### Repository pattern

Status: ✅ Keep.

Reasoning: The SRS architecture is service/repository layered and the data model is relational. Repositories are the right place for tenant-scoped persistence logic.

### Service pattern

Status: ✅ Keep.

Reasoning: The SRS requires business rules, authorization checks, and cross-repository orchestration in the service layer. The pattern matches the spec and should remain.

### Generic CRUD

Status: 🟡 Modify.

Reasoning: Generic CRUD is useful for foundation operations, but the SRS requires tenant scoping, soft delete, audit logging, and domain-specific behavior. Pure generic CRUD must not become the entire implementation model.

### Mixins

Status: 🟡 Modify.

Reasoning: UUID and timestamp mixins are useful and should remain. A soft-delete mixin should be added once recycle-bin requirements are implemented. The current mixins are incomplete for the SRS.

### Current Clinic model

Status: 🟡 Modify heavily.

Reasoning: The current model does not match the SRS foundation schema. The SRS clinic table needs branding and plan fields, not the current contact/status layout. The model should be reshaped, not removed.

## Migration review

Current state:

- Alembic has a single head: `c64933c10bdd`
- Only one migration exists
- The migration creates a clinic table that does not match the SRS clinic foundation schema

Assessment:

- The migration history is not safe to build phase 1 on as-is if the goal is SRS fidelity.
- The current initial migration should be treated as provisional and likely recreated or replaced before implementation continues.
- A new migration is definitely required for the missing foundation tables, but the SRS review instruction was not to create it yet.

## Ordered list of required code changes

1. Replace the current clinic model schema with the SRS clinic foundation schema and introduce the SRS enum set.
2. Add the `User` model and the shared auth foundation needed for clinic-scoped JWTs.
3. Add `clinic_id` to all tenant-owned models and implement query scoping rules.
4. Implement `ClinicGateMiddleware` integration and the supporting dependency layer.
5. Implement `Patient` plus the Phase 1 CRUD routes and services.
6. Extend the API router registration in `app/api/v1/__init__.py` and keep `main.py` thin.
7. Add soft-delete support and recycle-bin behavior for eligible records.
8. Implement audit logging for Patients, Appointments, and Invoices.
9. Implement billing, documents, booking, treatments, and analytics in SRS order.
10. Add isolation tests for every new endpoint and model scope.

## Conclusion

The backend currently provides the technical scaffolding for the SRS, but not the SRS itself. The main architectural shapes are present, yet the shared auth, middleware, routing, data model, and tenant-scoping requirements are still missing or incomplete. The safest next step is to implement Phase 1 from the SRS in order, starting with foundation models and clinic-scoped auth/scoping infrastructure.