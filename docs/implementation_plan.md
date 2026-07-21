# Implementation Plan

This plan is derived from `AV_Suite_CRM_SRS.pdf` and the current backend review.

It intentionally follows the SRS phase order and assumes the current codebase is only a foundation.

## Milestone 1: Foundation and tenant isolation

Objective:

Establish the clinic/user foundation, tenant scoping, and the shared auth/middleware path required for every later CRM feature.

Files affected:

- `app/models/clinic.py`
- `app/models/user.py`
- `app/enums/*`
- `app/core/security.py`
- `app/core/dependencies.py`
- `app/middleware/clinic_gate.py`
- `app/api/v1/__init__.py`
- `app/main.py`
- `alembic/versions/*`

Dependencies:

- Existing FastAPI app scaffold
- Existing async SQLAlchemy setup
- Existing Alembic history

Migration impact:

- High. This milestone introduces the SRS foundation schema and the clinic-scoping enforcement path.

Estimated implementation order:

1. Align the Clinic model with the SRS foundation schema.
2. Add the User model and required enums.
3. Implement auth issuance with `clinic_id` and role claims.
4. Wire ClinicGateMiddleware and the dependency layer.
5. Register routers through `app/api/v1/__init__.py`.
6. Update migrations to reflect the foundation schema.

## Milestone 2: Core clinical records

Objective:

Implement the core day-to-day CRM objects: Patients, Leads, and Appointments.

Files affected:

- `app/models/patient.py`
- `app/models/lead.py`
- `app/models/appointment.py`
- `app/repositories/*`
- `app/services/*`
- `app/api/v1/patients.py`
- `app/api/v1/leads.py`
- `app/api/v1/appointments.py`
- `alembic/versions/*`

Dependencies:

- Milestone 1 foundation
- Clinic scoping infrastructure

Migration impact:

- High. These tables carry `clinic_id` and are the first operational tenant-scoped records.

Estimated implementation order:

1. Create Patients model and CRUD flows.
2. Create Leads model and kanban-style status transitions.
3. Create Appointments model and scheduling flows.
4. Add list/search/filter endpoints.
5. Add clinic-isolation tests.

## Milestone 3: Clinical documentation and billing

Objective:

Implement treatments/assessments, packages, invoices, payments, and patient documents with PDF support.

Files affected:

- `app/models/treatment.py`
- `app/models/assessment.py`
- `app/models/package.py`
- `app/models/patient_package.py`
- `app/models/invoice.py`
- `app/models/payment.py`
- `app/models/patient_document.py`
- `app/services/pdf/*`
- `app/api/v1/treatments.py`
- `app/api/v1/billing.py`
- `app/api/v1/documents.py`
- `alembic/versions/*`

Dependencies:

- Milestone 1 foundation
- Milestone 2 patient and appointment records
- Existing WeasyPrint service
- Private storage integration

Migration impact:

- High. Billing and document tables are tenant-scoped and require relational integrity.

Estimated implementation order:

1. Add treatment and assessment records.
2. Add packages and patient packages.
3. Add invoices and payments.
4. Wire invoice PDF generation.
5. Add private document upload/download flows.
6. Add audit logging for finance and clinical records.

## Milestone 4: Public booking and intake workflow

Objective:

Implement the public booking entry point and appointment request approval flow.

Files affected:

- `app/models/appointment_request.py`
- `app/api/v1/booking.py`
- `app/api/v1/appointment_requests.py`
- `app/core/security.py`
- `app/core/dependencies.py`
- `app/middleware/clinic_gate.py`

Dependencies:

- Milestone 1 foundation
- Milestone 2 appointments

Migration impact:

- Moderate to high. The public form is unauthenticated but still resolves to a clinic-scoped request record.

Estimated implementation order:

1. Add appointment request model.
2. Add public clinic-branding endpoint.
3. Add booking request creation with validation and rate limiting.
4. Add approval/rejection endpoints.
5. Add clinic-isolation tests for the approval flow.

## Milestone 5: Recycle bin, analytics, and audit trails

Objective:

Implement soft delete, restore flows, analytics overview cards, and audit log visibility.

Files affected:

- `app/models/audit_log.py`
- `app/services/*`
- `app/api/v1/analytics.py`
- `app/api/v1/recycle_bin.py`
- `app/api/v1/settings.py`
- `app/common/mixins.py`
- `alembic/versions/*`

Dependencies:

- Milestone 2 clinical records
- Milestone 3 billing and documents

Migration impact:

- Moderate. Soft delete usually requires schema augmentation and backfilling logic.

Estimated implementation order:

1. Add soft-delete fields and logic.
2. Add recycle-bin listing and restore endpoints.
3. Add audit log model and write-path hooks.
4. Add analytics aggregates.
5. Surface audit logs in settings.

## Milestone 6: Test coverage and merge hygiene

Objective:

Prove clinic isolation and protect the shared backend from regression before broader feature rollout.

Files affected:

- `tests/**/*.py`
- Any touched application files from earlier milestones

Dependencies:

- Prior milestones complete

Migration impact:

- None directly, but tests should validate every migration-backed tenant boundary.

Estimated implementation order:

1. Add clinic-isolation tests for the foundation models.
2. Add endpoint tests for each new route.
3. Add billing math assertions where applicable.
4. Verify a single Alembic head before merges.

## Current architecture recommendation

Keep:

- `BaseRepository`
- `BaseService`
- repository pattern
- service pattern
- UUID and timestamp mixins

Modify:

- Clinic model
- generic CRUD usage so it remains clinic-aware and soft-delete-aware
- mixins so soft delete can be introduced cleanly

Remove:

- `ClinicStatus` enum, unless it maps to an external SRS-defined concept later

## Notes on sequencing

The SRS is explicit that Phase 1 is the foundation. The implementation order should therefore not jump to billing, booking, or analytics before the tenant model, auth, and clinic scoping are in place. The shared backend also means `main.py` should remain thin and router registration should move through `app/api/v1/__init__.py` rather than growing ad hoc.