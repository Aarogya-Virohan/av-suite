"""
AV SUITE BACKEND - COMPREHENSIVE API DOCUMENTATION
===================================================

Purpose: Yeh document complete API reference aur usage patterns provide karta hai.
Jis se developers, admins, aur frontend teams API use kar sakein.

Last Updated: 2026-05-18
Version: 0.1.0
"""

# ============================================================================
# API BASE INFORMATION
# ============================================================================

/*
Base URL: http://localhost:8000 (Development)
Base URL: https://api.av-suite.example.com (Production)
API Version: v1 (/api/v1)
Response Format: JSON with ResponseEnvelope wrapper

Authentication:
- Method: JWT Bearer Token
- Header: Authorization: Bearer {token}
- Expiration: 24 hours (configurable)
- Refresh: Register/Login ke time naya token milta hai
*/


# ============================================================================
# API ENDPOINTS REFERENCE
# ============================================================================

## Authentication Endpoints (Public)

### 1. User Registration
Endpoint: POST /api/v1/auth/register
Status Code: 201 CREATED
Authentication: Not required

Request Body:
{
    "email": "admin@clinic.com",          // User email (unique, required)
    "password": "SecurePassword123!",    // Min 8 chars, required
    "clinic_name": "City Medical"        // Clinic name, required
}

Response (Success):
{
    "status": "success",
    "data": {
        "access_token": "eyJhbGc...",
        "token_type": "bearer"
    }
}

Error Cases:
- 409 Conflict: Email already registered
- 400 Bad Request: Invalid email format or weak password
- 500 Server Error: Database error

Hinglish Notes:
- Signup mein clinic automatically create hota hai
- First user hamesha admin role se create hota hai
- Password strong banao (min 8 chars, special chars recommended)


### 2. User Login
Endpoint: POST /api/v1/auth/login
Status Code: 200 OK
Authentication: Not required

Request Body:
{
    "email": "admin@clinic.com",
    "password": "SecurePassword123!"
}

Response (Success):
{
    "status": "success",
    "data": {
        "access_token": "eyJhbGc...",
        "token_type": "bearer"
    }
}

Error Cases:
- 401 Unauthorized: Incorrect email or password
- 400 Bad Request: Invalid input format
- 500 Server Error: Database error

Hinglish Notes:
- Login successful ho to token immediately store karo (localStorage/sessionStorage)
- Token har request mein Authorization header mein bhejo
- Token expire ho to re-login karna hoga


# ============================================================================
# Patient Management Endpoints (Protected)
# ============================================================================

### 1. List Patients
Endpoint: GET /api/v1/patients
Status Code: 200 OK
Authentication: Required (JWT token)
Authorization: Admin, Physio roles only

Query Parameters:
- page (default: 1): Page number for pagination
- page_size (default: 10): Results per page (max: 100)

Headers:
Authorization: Bearer {jwt_token}

Response (Success):
{
    "status": "success",
    "data": [
        {
            "id": "patient-uuid",
            "clinic_id": "clinic-uuid",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "phone": "9876543210",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ],
    "meta": {
        "total": 45,
        "page": 1,
        "page_size": 10
    }
}

Error Cases:
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: User role not authorized
- 400 Bad Request: Invalid pagination parameters


### 2. Create Patient
Endpoint: POST /api/v1/patients
Status Code: 201 CREATED
Authentication: Required
Authorization: Admin, Physio roles only

Request Body:
{
    "first_name": "John",              // Required
    "last_name": "Doe",                // Required
    "date_of_birth": "1990-01-01",     // Optional
    "phone": "9876543210"              // Optional
}

Response (Success):
{
    "status": "success",
    "data": {
        "id": "new-patient-uuid",
        "clinic_id": "clinic-uuid",
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-01-01",
        "phone": "9876543210",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
}

Validation Rules:
- first_name: Required, 1-100 characters
- last_name: Required, 1-100 characters
- date_of_birth: Optional, valid date format
- phone: Optional, 1-20 characters

Error Cases:
- 401 Unauthorized: Invalid token
- 403 Forbidden: Role not authorized
- 400 Bad Request: Validation failure
- 409 Conflict: Duplicate record


### 3. Get Patient Details
Endpoint: GET /api/v1/patients/{id}
Status Code: 200 OK
Authentication: Required
Authorization: Admin, Physio roles only

Path Parameters:
- id (string, required): Patient UUID

Response (Success):
{
    "status": "success",
    "data": {
        "id": "patient-uuid",
        "clinic_id": "clinic-uuid",
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-01-01",
        "phone": "9876543210",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
}

Error Cases:
- 401 Unauthorized: Invalid token
- 403 Forbidden: Role not authorized
- 404 Not Found: Patient not found or not in clinic


# ============================================================================
# Exercise Management Endpoints (Protected)
# ============================================================================

### 1. List Exercises
Endpoint: GET /api/v1/exercises
Status Code: 200 OK
Authentication: Required
Authorization: All authenticated users

Query Parameters:
- body_part (optional): Filter by body part (e.g., "Shoulder")
- is_free (optional): Filter by free/paid (true/false)
- search (optional): Search in title (case-insensitive)
- page (default: 1): Page number
- page_size (default: 10): Results per page (max: 100)

Headers:
Authorization: Bearer {jwt_token}

Response (Success):
{
    "status": "success",
    "data": [
        {
            "id": "exercise-uuid",
            "clinic_id": "clinic-uuid or null",
            "title": "Shoulder Rotation",
            "description": "Rotate shoulder...",
            "body_part": "Shoulder",
            "is_free": true,
            "video_url": "https://cdn.example.com/video.mp4",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ],
    "meta": {
        "total": 23,
        "page": 1,
        "page_size": 10
    }
}

Example Queries:
GET /api/v1/exercises?body_part=Shoulder
GET /api/v1/exercises?is_free=true
GET /api/v1/exercises?search=rotation
GET /api/v1/exercises?body_part=Shoulder&is_free=true&page=2


### 2. Create Exercise
Endpoint: POST /api/v1/exercises
Status Code: 201 CREATED
Authentication: Required
Authorization: Admin role only

Request Body:
{
    "title": "Shoulder Rotation",                    // Required
    "description": "Step by step instructions...",  // Optional
    "body_part": "Shoulder",                         // Optional
    "is_free": true,                                 // Optional (default: false)
    "video_url": "https://cdn.example.com/..."      // Optional
}

Response (Success):
{
    "status": "success",
    "data": {
        "id": "new-exercise-uuid",
        "clinic_id": "clinic-uuid",
        "title": "Shoulder Rotation",
        "description": "Step by step instructions...",
        "body_part": "Shoulder",
        "is_free": true,
        "video_url": "https://cdn.example.com/...",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
}

Error Cases:
- 401 Unauthorized: Invalid token
- 403 Forbidden: Only admins can create


### 3. Get Exercise Details
Endpoint: GET /api/v1/exercises/{id}
Status Code: 200 OK
Authentication: Required
Authorization: All authenticated users


# ============================================================================
# Health Check Endpoint (Public)
# ============================================================================

### Health Check
Endpoint: GET /health
Status Code: 200 OK
Authentication: Not required

Response:
{
    "status": "healthy"
}

Purpose:
- Kubernetes liveness probe
- Load balancer health check
- Monitoring system uptime verification


# ============================================================================
# COMMON RESPONSE PATTERNS
# ============================================================================

### Success Response
{
    "status": "success",
    "data": {
        // Response data here
    },
    "meta": {
        // Optional metadata (pagination, etc.)
    }
}

### Error Response
{
    "status": "error",
    "data": null,
    "meta": {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable error message"
        }
    }
}

### Pagination Response
{
    "status": "success",
    "data": [/* array of items */],
    "meta": {
        "total": 100,
        "page": 1,
        "page_size": 10
    }
}


# ============================================================================
# HTTP STATUS CODES
# ============================================================================

200 OK - Request successful
201 CREATED - Resource created successfully
400 BAD REQUEST - Invalid request parameters/body
401 UNAUTHORIZED - Missing or invalid JWT token
403 FORBIDDEN - User role not authorized for this operation
404 NOT FOUND - Resource not found
409 CONFLICT - Resource already exists (duplicate)
500 INTERNAL SERVER ERROR - Server error occurred


# ============================================================================
# AUTHENTICATION FLOW
# ============================================================================

1. Register/Login
   POST /api/v1/auth/register or /api/v1/auth/login
   ↓
2. Get JWT Token
   Response contains access_token
   ↓
3. Store Token
   Save in localStorage/sessionStorage
   ↓
4. Use Token
   Add to Authorization header: "Authorization: Bearer {token}"
   ↓
5. Access Protected Endpoints
   GET /api/v1/patients
   POST /api/v1/exercises
   etc.
   ↓
6. Token Expiration
   After 24 hours, re-login required
   Get new token


# ============================================================================
# EXAMPLE REQUESTS (cURL)
# ============================================================================

### Register
curl -X POST http://localhost:8000/api/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "admin@clinic.com",
    "password": "SecurePassword123!",
    "clinic_name": "City Medical"
  }'

### Login
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "admin@clinic.com",
    "password": "SecurePassword123!"
  }'

### List Patients (with token)
curl -X GET "http://localhost:8000/api/v1/patients?page=1&page_size=10" \\
  -H "Authorization: Bearer eyJhbGc..."

### Create Patient
curl -X POST http://localhost:8000/api/v1/patients \\
  -H "Authorization: Bearer eyJhbGc..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-01",
    "phone": "9876543210"
  }'

### Health Check
curl -X GET http://localhost:8000/health


# ============================================================================
# RATE LIMITING & BEST PRACTICES
# ============================================================================

Rate Limits (Future Enhancement):
- API: 100 requests per minute per user
- Auth: 5 login attempts per minute

Best Practices:
- Always use HTTPS in production
- Store tokens securely (don't expose in URLs)
- Refresh tokens before expiration (future)
- Use pagination for large datasets
- Cache results on client side when possible
- Handle network timeouts gracefully
- Validate input before sending requests
