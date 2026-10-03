# AV Suite CRM — Frontend API Contract Specification

This document provides the exhaustive API contract for the **AV Suite CRM** frontend application (`frontend/crm`). It defines every API endpoint called by the frontend, including HTTP methods, URL paths, query parameters, request payloads, response structures, expected HTTP status codes, and capability permissions.

Backend developers must adhere to this specification to ensure seamless interoperability with the frontend CRM client.

---

## 1. Global Architectural Conventions

### 1.1 Base URL
- **Local Development**: `http://localhost:8000/api/v1`
- **Staging / Production (Render)**: `https://<render-service-name>.onrender.com/api/v1`

### 1.2 Authentication & Clinic Isolation
- All protected endpoints require a Bearer token in the `Authorization` header:
  ```http
  Authorization: Bearer <jwt_access_token>
  ```
- The JWT access token contains the user's `user_id`, `clinic_id`, and `role`.
- The backend `ClinicGateMiddleware` validates the JWT and automatically binds `request.state.clinic_id` and `request.state.user_id`.
- All queries must enforce multi-tenant isolation by filtering on `clinic_id`.
- Unauthenticated public endpoints:
  - `POST /api/v1/auth/login`
  - `GET /api/v1/booking/branding/{clinic_slug}`
  - `POST /api/v1/booking/request`

### 1.3 Response Envelopes

The frontend client expects standardized response envelopes:

#### Standard Entity Response:
```json
{
  "data": { ... }
}
```

#### Paginated List Response (Preferred):
```json
{
  "data": [ ... ],
  "meta": {
    "total": 42,
    "page": 1,
    "page_size": 10
  }
}
```
*Note for Legacy / Repositories returning `{ items: [...], total, offset, limit }`:*
The frontend handles both `{ data: [...], meta: ... }` and `{ items: [...], total, offset, limit }`. However, for consistency, the standard `ResponseEnvelope[T]` format should be standardized across all endpoints.

#### Error Response:
```json
{
  "detail": "Descriptive error message"
}
```
Validation error format (FastAPI standard):
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 2. Endpoints by Feature Module

---

### 2.1 Authentication (`/auth`)

#### `POST /auth/login`
- **Purpose**: Authenticate user and issue JWT token.
- **Access**: Public
- **Request Body**:
  ```json
  {
    "email": "admin@avtest.com",
    "password": "password123"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "data": {
      "access_token": "eyJhbGciOi...",
      "token_type": "bearer",
      "user": {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "admin@avtest.com",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "clinic_id": "22222222-2222-2222-2222-222222222222",
        "is_active": true
      }
    }
  }
  ```

---

### 2.2 Users & Permissions (`/users`)

#### `GET /users`
- **Purpose**: List all users belonging to the caller's clinic.
- **Capability**: `users.view` (Scope: ALL)
- **Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": "11111111-1111-1111-1111-111111111111",
        "clinic_id": "22222222-2222-2222-2222-222222222222",
        "email": "therapist@avtest.com",
        "first_name": "Tarun",
        "last_name": "Therapist",
        "role": "therapist",
        "phone": "9876543210",
        "is_active": true,
        "created_at": "2026-09-01T10:00:00Z"
      }
    ]
  }
  ```

#### `POST /users`
- **Purpose**: Create a new staff user in the caller's clinic.
- **Capability**: `users.create` (Scope: ALL)
- **Request Body**:
  ```json
  {
    "email": "newtherapist@avtest.com",
    "password": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe",
    "role": "therapist",
    "phone": "9876543210"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "33333333-3333-3333-3333-333333333333",
      "email": "newtherapist@avtest.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "therapist",
      "is_active": true
    }
  }
  ```

#### `DELETE /users/{user_id}`
- **Purpose**: Soft delete/deactivate a user.
- **Capability**: `users.delete` (Scope: ALL)
- **Guard**: Must reject deletion if caller is deleting the last remaining admin in the clinic.
- **Response (200 OK)**:
  ```json
  {
    "data": null
  }
  ```

#### `GET /users/{user_id}/permissions`
- **Purpose**: Fetch the 64-capability permission matrix and overrides for a user.
- **Capability**: `permissions.view` (Scope: ALL)
- **Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "capability": "patients.view",
        "scope": "OWN",
        "is_default": true
      },
      {
        "capability": "patients.edit",
        "scope": "OWN",
        "is_default": false
      }
    ]
  }
  ```

#### `PUT /users/{user_id}/permissions`
- **Purpose**: Update capability scopes / overrides for a user.
- **Capability**: `permissions.edit` (Scope: ALL)
- **Guard**: Admin lockout guard (prevent admin from revoking their own permission to manage permissions).
- **Request Body**:
  ```json
  [
    {
      "capability": "patients.view",
      "scope": "ALL"
    },
    {
      "capability": "billing.view",
      "scope": "NONE"
    }
  ]
  ```
- **Response (200 OK)**:
  ```json
  {
    "data": [ ... ]
  }
  ```

---

### 2.3 Patients (`/patients`)

#### `GET /patients`
- **Purpose**: Search and list patients with pagination.
- **Capability**: `patients.view` (Scope: `ALL` sees all clinic patients; `OWN` sees only patients created by or assigned to caller).
- **Query Parameters**:
  - `search` (string, optional): Search by name, 10-digit phone, or email.
  - `page` (integer, default 1)
  - `page_size` (integer, default 10)
- **Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": "44444444-4444-4444-4444-444444444444",
        "clinic_id": "22222222-2222-2222-2222-222222222222",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "first_name": "Ramesh",
        "last_name": "Kumar",
        "email": "ramesh@example.com",
        "phone": "9876543210",
        "gender": "male",
        "date_of_birth": "1985-05-15",
        "medical_history": "Lower back pain",
        "created_at": "2026-09-01T10:00:00Z"
      }
    ],
    "meta": {
      "total": 1,
      "page": 1,
      "page_size": 10
    }
  }
  ```

#### `GET /patients/{id}`
- **Purpose**: Get patient by UUID.
- **Capability**: `patients.view` (Scoped)
- **Response (200 OK)**:
  ```json
  {
    "data": {
      "id": "44444444-4444-4444-4444-444444444444",
      "first_name": "Ramesh",
      "last_name": "Kumar",
      "email": "ramesh@example.com",
      "phone": "9876543210",
      "gender": "male",
      "date_of_birth": "1985-05-15",
      "medical_history": "Lower back pain"
    }
  }
  ```

#### `POST /patients`
- **Purpose**: Create a new patient.
- **Capability**: `patients.create` (Scope: ALL)
- **Request Body**:
  ```json
  {
    "first_name": "Ramesh",
    "last_name": "Kumar",
    "email": "ramesh@example.com",
    "phone": "9876543210",
    "gender": "male",
    "date_of_birth": "1985-05-15",
    "medical_history": "Lower back pain"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "44444444-4444-4444-4444-444444444444",
      "user_id": "<caller_user_id>",
      "first_name": "Ramesh",
      "last_name": "Kumar"
    }
  }
  ```

#### `PATCH /patients/{id}`
- **Purpose**: Update patient fields.
- **Capability**: `patients.edit` (Scoped)
- **Request Body**:
  ```json
  {
    "phone": "9876543211",
    "medical_history": "Updated medical history"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "data": { ... }
  }
  ```

#### `DELETE /patients/{id}`
- **Purpose**: Soft delete patient.
- **Capability**: `patients.delete` (Scope: ALL)
- **Response (200 OK)**:
  ```json
  {
    "data": null
  }
  ```

#### `GET /patients/{id}/documents`
- **Purpose**: List documents uploaded for a patient.
- **Capability**: `documents.view`
- **Response (200 OK)**:
  ```json
  {
    "items": [
      {
        "id": "55555555-5555-5555-5555-555555555555",
        "title": "MRI Report",
        "file_name": "mri_lumbar.pdf",
        "file_size": 2048576,
        "mime_type": "application/pdf",
        "created_at": "2026-09-10T14:30:00Z"
      }
    ],
    "total": 1,
    "offset": 0,
    "limit": 50
  }
  ```

#### `POST /patients/{id}/documents`
- **Purpose**: Upload document to Supabase storage.
- **Capability**: `documents.upload`
- **Content-Type**: `multipart/form-data`
- **Payload**: `file` (binary), `title` (string)
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "55555555-5555-5555-5555-555555555555",
      "title": "MRI Report",
      "file_name": "mri_lumbar.pdf"
    }
  }
  ```

---

### 2.4 Appointments (`/appointments`)

#### `GET /appointments`
- **Purpose**: List appointments for schedule/calendar.
- **Capability**: `appointments.view` (Scoped)
- **Query Parameters**:
  - `start_date` (string, `YYYY-MM-DD`, optional)
  - `end_date` (string, `YYYY-MM-DD`, optional)
  - `offset` (integer, default 0)
  - `limit` (integer, default 50)
- **Response (200 OK)**:
  ```json
  {
    "items": [
      {
        "id": "66666666-6666-6666-6666-666666666666",
        "patient_id": "44444444-4444-4444-4444-444444444444",
        "patient_name": "Ramesh Kumar",
        "therapist_id": "11111111-1111-1111-1111-111111111111",
        "therapist_name": "Dr. Tarun",
        "appointment_date": "2026-09-20",
        "start_time": "10:00:00",
        "end_time": "10:45:00",
        "status": "scheduled",
        "service": "Physiotherapy",
        "notes": "Initial assessment"
      }
    ],
    "total": 1,
    "offset": 0,
    "limit": 50
  }
  ```

#### `POST /appointments`
- **Purpose**: Create a new appointment.
- **Capability**: `appointments.create`
- **Request Body**:
  ```json
  {
    "patient_id": "44444444-4444-4444-4444-444444444444",
    "therapist_id": "11111111-1111-1111-1111-111111111111",
    "appointment_date": "2026-09-20",
    "start_time": "10:00:00",
    "end_time": "10:45:00",
    "service": "Physiotherapy",
    "notes": "Initial consultation"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "66666666-6666-6666-6666-666666666666",
      "status": "scheduled"
    }
  }
  ```

#### `PATCH /appointments/{id}`
- **Purpose**: Update appointment details or status (reschedule/cancel/complete).
- **Capability**: `appointments.edit`
- **Request Body**:
  ```json
  {
    "status": "completed",
    "appointment_date": "2026-09-21",
    "start_time": "11:00:00",
    "end_time": "11:45:00"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "data": {
      "id": "66666666-6666-6666-6666-666666666666",
      "status": "completed"
    }
  }
  ```

---

### 2.5 Billing & Invoices (`/invoices`, `/payments`, `/packages`)

#### `GET /invoices`
- **Purpose**: List invoices for the clinic.
- **Capability**: `billing.view`
- **Response (200 OK)**:
  ```json
  {
    "items": [
      {
        "id": "77777777-7777-7777-7777-777777777777",
        "invoice_number": "INV-2026-001",
        "patient_id": "44444444-4444-4444-4444-444444444444",
        "patient_name": "Ramesh Kumar",
        "amount": "1500.00",
        "tax": "0.00",
        "total_amount": "1500.00",
        "status": "paid",
        "due_date": "2026-09-30",
        "created_at": "2026-09-19T10:00:00Z"
      }
    ],
    "total": 1,
    "offset": 0,
    "limit": 50
  }
  ```

#### `POST /invoices`
- **Purpose**: Create invoice.
- **Capability**: `billing.create`
- **Request Body**:
  ```json
  {
    "patient_id": "44444444-4444-4444-4444-444444444444",
    "amount": 1500.0,
    "items": [
      {
        "description": "Physiotherapy Session",
        "quantity": 1,
        "unit_price": 1500.0
      }
    ]
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "77777777-7777-7777-7777-777777777777",
      "invoice_number": "INV-2026-001",
      "status": "unpaid"
    }
  }
  ```

#### `POST /invoices/{invoice_id}/payments`
- **Purpose**: Record payment for an invoice.
- **Capability**: `billing.edit`
- **Request Body**:
  ```json
  {
    "amount": 1500.0,
    "payment_method": "upi",
    "transaction_ref": "UPI12345678"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "88888888-8888-8888-8888-888888888888",
      "status": "success"
    }
  }
  ```

---

### 2.6 Leads (`/leads`)

#### `GET /leads`
- **Purpose**: List leads for pipeline.
- **Capability**: `leads.view`
- **Query Parameters**:
  - `stage` (optional, e.g. `new`, `contacted`, `converted`, `lost`)
- **Response (200 OK)**:
  ```json
  {
    "data": [
      {
        "id": "99999999-9999-9999-9999-999999999999",
        "name": "Priya Sharma",
        "phone": "9811122233",
        "source": "website",
        "stage": "new",
        "notes": "Interested in back rehab",
        "created_at": "2026-09-18T12:00:00Z"
      }
    ]
  }
  ```

#### `POST /leads`
- **Purpose**: Create a new lead.
- **Capability**: `leads.create`
- **Request Body**:
  ```json
  {
    "name": "Priya Sharma",
    "phone": "9811122233",
    "source": "website",
    "notes": "Back pain inquiry"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "99999999-9999-9999-9999-999999999999",
      "stage": "new"
    }
  }
  ```

#### `PATCH /leads/{id}`
- **Purpose**: Update lead stage or details.
- **Capability**: `leads.edit`
- **Request Body**:
  ```json
  {
    "stage": "contacted"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "data": { ... }
  }
  ```

#### `POST /leads/{id}/convert`
- **Purpose**: Convert lead to registered patient.
- **Capability**: `leads.edit`
- **Response (200 OK)**:
  ```json
  {
    "data": {
      "patient_id": "44444444-4444-4444-4444-444444444444",
      "lead_id": "99999999-9999-9999-9999-999999999999",
      "status": "converted"
    }
  }
  ```

---

### 2.7 Analytics (`/analytics`)

#### `GET /analytics/overview`
- **Purpose**: Clinic-wide dashboard KPIs.
- **Capability**: `analytics.view` (Scope: ALL)
- **Response (200 OK)**:
  ```json
  {
    "data": {
      "patients": {
        "total_patients": 120,
        "new_this_month": 15
      },
      "appointments": {
        "today_appointments": 8,
        "completed_this_month": 84
      },
      "revenue": {
        "revenue_this_month": 126000.0,
        "outstanding_amount": 14500.0
      },
      "leads": {
        "total_leads": 24,
        "converted_this_month": 6
      }
    }
  }
  ```

#### `GET /analytics/my-performance`
- **Purpose**: Therapist-scoped personal KPI performance metrics.
- **Capability**: `analytics.view` (Scope: OWN)
- **Response (200 OK)**:
  ```json
  {
    "data": {
      "today_appointments": 4,
      "completed_appointments_this_month": 42,
      "cancelled_appointments_this_month": 2,
      "treatment_sessions_this_month": 38,
      "soap_notes_this_month": 38,
      "patients_seen_this_month": 18
    }
  }
  ```

---

### 2.8 Public Booking (`/booking`)

#### `GET /booking/branding/{clinic_slug}`
- **Purpose**: Public clinic profile for booking pages.
- **Access**: Public / Unauthenticated
- **Response (200 OK)**:
  ```json
  {
    "data": {
      "clinic_id": "22222222-2222-2222-2222-222222222222",
      "clinic_name": "Aarogya Clinic",
      "logo_url": "https://...",
      "phone": "9876543210",
      "address": "New Delhi",
      "services": ["Physiotherapy Consultation", "Rehabilitation"]
    }
  }
  ```

#### `POST /booking/request`
- **Purpose**: Public appointment request submission.
- **Access**: Public / Unauthenticated
- **Query Parameters**: `clinic_slug` or `clinic_id`
- **Request Body**:
  ```json
  {
    "name": "Anil Verma",
    "phone": "9876500000",
    "age": 32,
    "gender": "male",
    "chief_complaint": "Knee injury from running",
    "preferred_date": "2026-09-22",
    "preferred_slot": "11:00 AM",
    "notes": "Service Requested: Physiotherapy Consultation"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "data": {
      "id": "aaaa1111-bb22-cc33-dd44-ee55ff66aa77",
      "status": "pending",
      "message": "Appointment request submitted successfully"
    }
  }
  ```

---

## 3. Discrepancy Matrix & Required Adjustments

| Issue Area | Frontend Current State | Backend Current State | Required Fix |
|:---|:---|:---|:---|
| **Billing Envelopes** | Expects `{ items: [...] }` or `{ data: [...] }` | Returns bare `{ items: [...] }` | Frontend patch (`01a0afb1-a7d3-78db-8018-6b703c67e465.patch`) normalizes `raw = res.data?.items ?? res.data?.data ?? res.data`. |
| **Patient Ownership** | Supports viewing own or all patients | Missing `4d427c1` patient `user_id` ownership | Integrate Sparsh's `4d427c1` into `patients.py` and `patient_service.py` with `audit_service` preserved. |
| **SOAP Notes Therapist ID** | Sometimes sent without therapist ID | Backend checks `therapist_id == user.id` in `OWN` scope | Ensure frontend injects current `user.id` when calling `create_assessment`. |
| **Prescription PDF Download** | Fetched via direct Bearer token in header | Route requires authentication | Frontend uses `getStoredToken()` to download PDF blob cleanly. |
