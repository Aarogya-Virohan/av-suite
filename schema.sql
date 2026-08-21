-- =============================================================================
-- Aarogya-Virohan (AV Suite) - PostgreSQL Database Schema Design
-- Target Database: PostgreSQL 14+
-- Last Updated: August 2026
-- =============================================================================
--
-- ⚠️  REFERENCE ONLY — ARCHITECTURAL DESIGN SPECIFICATION
-- This file is NOT the source of truth for the live database schema.
-- Alembic migrations in backend/alembic/versions/ are the SINGLE SOURCE OF TRUTH.
-- This file exists for human reference and design review purposes only.
-- DO NOT run this file against any database directly — it will conflict with
-- existing Alembic migration history.
-- =============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUM TYPES DEFINITIONS
-- =============================================================================

-- Clinic plan tiers
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'clinicplantier') THEN
        CREATE TYPE clinicplantier AS ENUM ('free', 'practice', 'clinical_pro');
    END IF;
END $$;

-- Patient status tracking
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'patientstatus') THEN
        CREATE TYPE patientstatus AS ENUM ('active', 'inactive', 'discharged');
    END IF;
END $$;

-- Public booking request status
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_request_status') THEN
        CREATE TYPE appointment_request_status AS ENUM ('pending', 'approved', 'rejected');
    END IF;
END $$;

-- Package catalog and patient package status
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'package_status') THEN
        CREATE TYPE package_status AS ENUM ('active', 'inactive', 'completed', 'expired', 'cancelled');
    END IF;
END $$;

-- Appointment scheduling states
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_status') THEN
        CREATE TYPE appointment_status AS ENUM ('scheduled', 'completed', 'cancelled', 'no_show');
    END IF;
END $$;

-- Appointment origin/source
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_source') THEN
        CREATE TYPE appointment_source AS ENUM ('manual', 'public_booking');
    END IF;
END $$;

-- CRM Lead lifecycle stages
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_stage') THEN
        CREATE TYPE lead_stage AS ENUM ('new', 'contacted', 'qualified', 'converted', 'lost');
    END IF;
END $$;

-- Billing invoice status
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invoice_status') THEN
        CREATE TYPE invoice_status AS ENUM ('unpaid', 'paid', 'partial', 'draft', 'issued', 'cancelled', 'overdue');
    END IF;
END $$;

-- Document category tags
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_category') THEN
        CREATE TYPE document_category AS ENUM ('medical_report', 'prescription', 'lab_result', 'consent_form', 'x_ray_scan', 'id_proof', 'other');
    END IF;
END $$;

-- Payment methods supported
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_method') THEN
        CREATE TYPE payment_method AS ENUM ('cash', 'upi', 'card', 'bank_transfer', 'insurance', 'other');
    END IF;
END $$;


-- =============================================================================
-- CORE DOMAIN TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: clinics
-- Description: Top-level multi-tenant container for clinics in the system.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clinics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    branding_logo_url VARCHAR(2048) DEFAULT NULL,
    branding_color VARCHAR(32) DEFAULT NULL,
    plan_tier clinicplantier NOT NULL DEFAULT 'free',
    is_partner_clinic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Table: users
-- Description: System user accounts (Admins, Therapists, Front Desk, Patients).
-- Rules & Constraints:
--   - Role constrained via CHECK constraint ck_users_role
--   - Email must be unique across all users
--   - Cascades deletion if clinic is deleted
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(32) DEFAULT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_users_role CHECK (role IN ('admin', 'therapist', 'front_desk', 'patient'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- -----------------------------------------------------------------------------
-- Table: patients
-- Description: Clinical patient profiles linked to a clinic and optionally a user account.
-- Rules & Constraints:
--   - clinic_id: Foreign key -> clinics(id) ON DELETE CASCADE
--   - user_id: Optional foreign key -> users(id) ON DELETE SET NULL
--   - Supports soft deletion (deleted_at)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    user_id UUID DEFAULT NULL REFERENCES users(id) ON DELETE SET NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    age INTEGER DEFAULT NULL,
    gender VARCHAR(32) DEFAULT NULL,
    chief_complaint TEXT DEFAULT NULL,
    referral_source VARCHAR(255) DEFAULT NULL,
    status patientstatus NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- -----------------------------------------------------------------------------
-- Table: exercises
-- Description: Rehabilitation exercises library (clinic-specific or global if clinic_id IS NULL).
-- Rules & Constraints:
--   - clinic_id: Optional FK -> clinics(id) ON DELETE CASCADE (NULL indicates system-wide global exercise)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID DEFAULT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    body_part VARCHAR(100) DEFAULT NULL,
    is_free BOOLEAN NOT NULL DEFAULT FALSE,
    video_url VARCHAR(1024) DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Table: packages
-- Description: Treatment package master catalog offered by clinics.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    name VARCHAR(255) NOT NULL,
    total_sessions INTEGER NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    validity_days INTEGER NOT NULL,
    status package_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_packages_clinic_id ON packages(clinic_id);
CREATE INDEX IF NOT EXISTS ix_packages_status ON packages(status);

-- -----------------------------------------------------------------------------
-- Table: patient_packages
-- Description: Active/purchased multi-session treatment packages assigned to patients.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    package_id UUID DEFAULT NULL REFERENCES packages(id),
    package_name VARCHAR(255) NOT NULL,
    total_sessions INTEGER NOT NULL,
    completed_sessions INTEGER NOT NULL DEFAULT 0,
    price NUMERIC(10, 2) NOT NULL,
    status package_status NOT NULL DEFAULT 'active',
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_patient_packages_clinic_id ON patient_packages(clinic_id);
CREATE INDEX IF NOT EXISTS ix_patient_packages_patient_id ON patient_packages(patient_id);
CREATE INDEX IF NOT EXISTS ix_patient_packages_package_id ON patient_packages(package_id);
CREATE INDEX IF NOT EXISTS ix_patient_packages_status ON patient_packages(status);

-- -----------------------------------------------------------------------------
-- Table: leads
-- Description: CRM sales leads representing potential patients.
-- Rules & Constraints:
--   - assigned_to: FK -> users(id)
--   - converted_patient_id: FK -> patients(id)
--   - Supports soft deletion (deleted_at, deleted_by)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255) DEFAULT NULL,
    source VARCHAR(100) DEFAULT NULL,
    stage lead_stage NOT NULL DEFAULT 'new',
    assigned_to UUID DEFAULT NULL REFERENCES users(id),
    notes TEXT DEFAULT NULL,
    converted_patient_id UUID DEFAULT NULL REFERENCES patients(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    deleted_by UUID DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS ix_leads_clinic_id ON leads(clinic_id);
CREATE INDEX IF NOT EXISTS ix_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS ix_leads_assigned_to ON leads(assigned_to);
CREATE INDEX IF NOT EXISTS ix_leads_converted_patient_id ON leads(converted_patient_id);
CREATE INDEX IF NOT EXISTS ix_leads_phone ON leads(phone);

-- -----------------------------------------------------------------------------
-- Table: appointment_requests
-- Description: Public appointment booking requests prior to staff approval.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointment_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    age INTEGER DEFAULT NULL,
    gender VARCHAR(20) DEFAULT NULL,
    chief_complaint TEXT DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    preferred_date DATE DEFAULT NULL,
    preferred_slot VARCHAR(50) DEFAULT NULL,
    status appointment_request_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_appointment_requests_clinic_id ON appointment_requests(clinic_id);
CREATE INDEX IF NOT EXISTS ix_appointment_requests_status ON appointment_requests(status);
CREATE INDEX IF NOT EXISTS ix_appointment_requests_phone ON appointment_requests(phone);
CREATE INDEX IF NOT EXISTS ix_appointment_requests_preferred_date ON appointment_requests(preferred_date);

-- -----------------------------------------------------------------------------
-- Table: appointments
-- Description: Scheduled clinical consultation appointments.
-- Rules & Constraints:
--   - FK to clinic_id, patient_id, therapist_id (users.id)
--   - Supports soft deletion (deleted_at, deleted_by)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    therapist_id UUID NOT NULL REFERENCES users(id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    status appointment_status NOT NULL DEFAULT 'scheduled',
    source appointment_source NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    deleted_by UUID DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS ix_appointments_clinic_id ON appointments(clinic_id);
CREATE INDEX IF NOT EXISTS ix_appointments_patient_id ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS ix_appointments_therapist_id ON appointments(therapist_id);
CREATE INDEX IF NOT EXISTS ix_appointments_scheduled_at ON appointments(scheduled_at);
CREATE INDEX IF NOT EXISTS ix_appointments_status ON appointments(status);

-- -----------------------------------------------------------------------------
-- Table: treatment_sessions
-- Description: Records of physical therapy treatment provided during appointments or walk-ins.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS treatment_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    appointment_id UUID DEFAULT NULL REFERENCES appointments(id),
    therapist_id UUID NOT NULL REFERENCES users(id),
    treatment_date TIMESTAMPTZ NOT NULL,
    pain_score INTEGER DEFAULT NULL,
    treatment TEXT NOT NULL,
    home_advice TEXT DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_treatment_sessions_clinic_id ON treatment_sessions(clinic_id);
CREATE INDEX IF NOT EXISTS ix_treatment_sessions_patient_id ON treatment_sessions(patient_id);
CREATE INDEX IF NOT EXISTS ix_treatment_sessions_appointment_id ON treatment_sessions(appointment_id);
CREATE INDEX IF NOT EXISTS ix_treatment_sessions_therapist_id ON treatment_sessions(therapist_id);
CREATE INDEX IF NOT EXISTS ix_treatment_sessions_treatment_date ON treatment_sessions(treatment_date);

-- -----------------------------------------------------------------------------
-- Table: soap_assessments
-- Description: Dynamic SOAP (Subjective, Objective, Assessment, Plan) clinical notes stored as JSONB.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS soap_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    appointment_id UUID DEFAULT NULL REFERENCES appointments(id),
    specialty VARCHAR(100) NOT NULL,
    diagnosis TEXT DEFAULT NULL,
    is_reassessment BOOLEAN NOT NULL DEFAULT FALSE,
    form_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_soap_assessments_clinic_id ON soap_assessments(clinic_id);
CREATE INDEX IF NOT EXISTS ix_soap_assessments_patient_id ON soap_assessments(patient_id);
CREATE INDEX IF NOT EXISTS ix_soap_assessments_appointment_id ON soap_assessments(appointment_id);
CREATE INDEX IF NOT EXISTS ix_soap_assessments_specialty ON soap_assessments(specialty);

-- -----------------------------------------------------------------------------
-- Table: prescriptions
-- Description: Exercise prescription master headers given to patients by therapists.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prescriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    physio_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    physio_notes TEXT DEFAULT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    pdf_key VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Table: prescription_items
-- Description: Individual exercises prescribed with sets, reps, frequency, and hold angle.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prescription_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    sets INTEGER NOT NULL DEFAULT 1,
    reps INTEGER NOT NULL DEFAULT 10,
    hold INTEGER NOT NULL DEFAULT 0,
    frequency VARCHAR(100) NOT NULL DEFAULT 'Daily',
    hold_angle INTEGER DEFAULT NULL,
    note TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Table: posture_sessions
-- Description: Computer-vision posture analysis sessions for patients.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS posture_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    overall_confidence FLOAT DEFAULT NULL,
    annotated_front_image VARCHAR(1024) DEFAULT NULL,
    annotated_back_image VARCHAR(1024) DEFAULT NULL,
    annotated_side_image VARCHAR(1024) DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Table: posture_measurements
-- Description: Individual anatomical angle and vector metrics calculated in a posture session.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS posture_measurements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES posture_sessions(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    unit VARCHAR(50) DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    severity VARCHAR(50) DEFAULT NULL,
    visibility VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Table: invoices
-- Description: Financial billing invoices for patient treatments, products, or packages.
-- Rules & Constraints:
--   - Line items stored as JSONB along with normalized line items table
--   - Supports soft deletion (deleted_at, deleted_by)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    appointment_id UUID DEFAULT NULL REFERENCES appointments(id),
    invoice_number VARCHAR(64) NOT NULL,
    issue_date TIMESTAMPTZ NOT NULL,
    due_date TIMESTAMPTZ DEFAULT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(10, 2) NOT NULL,
    paid_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status invoice_status NOT NULL DEFAULT 'issued',
    line_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    deleted_by UUID DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS ix_invoices_clinic_id ON invoices(clinic_id);
CREATE INDEX IF NOT EXISTS ix_invoices_patient_id ON invoices(patient_id);
CREATE INDEX IF NOT EXISTS ix_invoices_appointment_id ON invoices(appointment_id);
CREATE INDEX IF NOT EXISTS ix_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices(status);

-- -----------------------------------------------------------------------------
-- Table: invoice_items
-- Description: Itemized detail lines within an invoice.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    description VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL,
    total_price NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_invoice_items_clinic_id ON invoice_items(clinic_id);
CREATE INDEX IF NOT EXISTS ix_invoice_items_invoice_id ON invoice_items(invoice_id);

-- -----------------------------------------------------------------------------
-- Table: patient_documents
-- Description: Patient file attachments (x-rays, MRI scans, lab reports, ID proofs, consent forms).
-- Rules & Constraints:
--   - Supports soft deletion (deleted_at, deleted_by)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    uploaded_by UUID DEFAULT NULL REFERENCES users(id),
    treatment_id UUID DEFAULT NULL REFERENCES treatment_sessions(id),
    file_url VARCHAR(1024) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_size INTEGER DEFAULT NULL,
    label VARCHAR(255) NOT NULL,
    category document_category NOT NULL DEFAULT 'other',
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    deleted_by UUID DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS ix_patient_documents_clinic_id ON patient_documents(clinic_id);
CREATE INDEX IF NOT EXISTS ix_patient_documents_patient_id ON patient_documents(patient_id);
CREATE INDEX IF NOT EXISTS ix_patient_documents_treatment_id ON patient_documents(treatment_id);
CREATE INDEX IF NOT EXISTS ix_patient_documents_uploaded_by ON patient_documents(uploaded_by);
CREATE INDEX IF NOT EXISTS ix_patient_documents_category ON patient_documents(category);

-- -----------------------------------------------------------------------------
-- Table: payments
-- Description: Financial payment settlement transactions recorded against invoices.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    patient_id UUID NOT NULL REFERENCES patients(id),
    amount NUMERIC(10, 2) NOT NULL,
    payment_method payment_method NOT NULL,
    payment_date TIMESTAMPTZ NOT NULL,
    transaction_reference VARCHAR(255) DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_payments_clinic_id ON payments(clinic_id);
CREATE INDEX IF NOT EXISTS ix_payments_invoice_id ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS ix_payments_patient_id ON payments(patient_id);

-- -----------------------------------------------------------------------------
-- Table: audit_logs
-- Description: Audit trail tracking system actions, security events, and modifications.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    user_id UUID DEFAULT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID DEFAULT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_clinic_id ON audit_logs(clinic_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
