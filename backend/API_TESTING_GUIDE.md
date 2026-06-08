# 🧪 API TESTING GUIDE - AV SUITE BACKEND

**Purpose**: यह guide सभी APIs को manually test करने के लिए है | This guide helps you test all endpoints step-by-step with cURL commands and expected results.

**Last Updated**: 2026-05-18  
**Status**: Ready for testing

---

## 📋 TABLE OF CONTENTS

1. [Pre-Testing Setup](#pre-testing-setup)
2. [Authentication Testing](#authentication-testing)
3. [Patient Endpoints Testing](#patient-endpoints-testing)
4. [Exercise Endpoints Testing](#exercise-endpoints-testing)
5. [Error Scenarios](#error-scenarios)
6. [Troubleshooting](#troubleshooting)
7. [Test Results Checklist](#test-results-checklist)

---

## 🚀 PRE-TESTING SETUP

### Step 1: Start the Development Server

```bash
# Terminal 1: Navigate to backend directory
cd /home/shit/DFQ/av-suite/backend

# Start development server
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 2: Verify Server is Running

```bash
# Terminal 2: Test health endpoint
curl -X GET http://localhost:8000/health

# Expected Response:
# {"status": "ok", "timestamp": "2026-05-18T08:10:13"}
```

### Step 3: Setup Environment Variables

**Ensure .env file has:**
```
DATABASE_URL=postgresql+asyncpg://postgres.{project-id}:{password}@{region}.pooler.supabase.com:5432/postgres
JWT_SECRET_KEY=your-super-secret-jwt-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Step 4: Store Test Credentials

**Create a test file for storing responses:**
```bash
# Create a file to store tokens
touch /tmp/test_tokens.txt
```

---

## 🔐 AUTHENTICATION TESTING

### Test 1: User Registration (Create New Clinic)

**Purpose**: नया clinic account बनाना और admin user create करना | This creates a new clinic and registers the admin user.

```bash
# Test Data
CLINIC_NAME="Test Clinic Delhi"
CLINIC_EMAIL="admin@testclinic.com"
CLINIC_PHONE="9876543210"
ADMIN_EMAIL="admin@testclinic.com"
ADMIN_PASSWORD="AdminTest@123"
ADMIN_NAME="Amit Kumar"

# cURL Command
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_name": "'"$CLINIC_NAME"'",
    "clinic_email": "'"$CLINIC_EMAIL"'",
    "clinic_phone": "'"$CLINIC_PHONE"'",
    "admin_email": "'"$ADMIN_EMAIL"'",
    "admin_password": "'"$ADMIN_PASSWORD"'",
    "admin_name": "'"$ADMIN_NAME"'"
  }'
```

**Expected Response (201 Created):**
```json
{
  "clinic_id": "uuid-here",
  "clinic_name": "Test Clinic Delhi",
  "admin_email": "admin@testclinic.com",
  "message": "Clinic and admin user created successfully"
}
```

**Save Response:**
```bash
# Save clinic_id for later use
CLINIC_ID="uuid-from-response"
echo "CLINIC_ID=$CLINIC_ID" >> /tmp/test_tokens.txt
```

---

### Test 2: User Login

**Purpose**: Admin user को login करना और JWT token प्राप्त करना | This authenticates the user and returns a JWT token.

```bash
# Test Data
LOGIN_EMAIL="admin@testclinic.com"
LOGIN_PASSWORD="AdminTest@123"

# cURL Command
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$LOGIN_EMAIL"'",
    "password": "'"$LOGIN_PASSWORD"'"
  }'
```

**Expected Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "clinic_id": "uuid-here",
  "user_id": "uuid-here",
  "role": "admin"
}
```

**Save Token:**
```bash
# Extract and save the token (replace with actual token)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
CLINIC_ID="uuid-here"
USER_ID="uuid-here"

echo "TOKEN=$TOKEN" >> /tmp/test_tokens.txt
echo "CLINIC_ID=$CLINIC_ID" >> /tmp/test_tokens.txt
echo "USER_ID=$USER_ID" >> /tmp/test_tokens.txt
```

**Store for later:**
```bash
# Read from file for future requests
source /tmp/test_tokens.txt
```

---

### Test 3: Invalid Login - Wrong Password

**Purpose**: गलत password से login करने की कोशिश | Test error handling for incorrect credentials.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@testclinic.com",
    "password": "WrongPassword@123"
  }'
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Incorrect email or password"
}
```

---

### Test 4: Invalid Login - Non-existent Email

**Purpose**: ऐसी email से login करना जो database में नहीं है | Test error handling for non-existent user.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nonexistent@test.com",
    "password": "SomePassword@123"
  }'
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Incorrect email or password"
}
```

---

## 👥 PATIENT ENDPOINTS TESTING

**Note**: सभी patient endpoints के लिए JWT token की जरूरत है | All patient endpoints require JWT token in Authorization header.

### Setup: Load Saved Token

```bash
# Load credentials from previous tests
source /tmp/test_tokens.txt

# Verify token is loaded
echo "Using Token: $TOKEN"
echo "Clinic ID: $CLINIC_ID"
```

---

### Test 5: Create Patient

**Purpose**: नया patient record create करना | Add a new patient to the clinic.

```bash
# Test Data
PATIENT_FIRST_NAME="Rajesh"
PATIENT_LAST_NAME="Verma"
PATIENT_EMAIL="rajesh@example.com"
PATIENT_PHONE="9123456789"
PATIENT_DOB="1990-05-15"
PATIENT_GENDER="male"
PATIENT_HEIGHT=180
PATIENT_WEIGHT=75

# cURL Command
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "first_name": "'"$PATIENT_FIRST_NAME"'",
    "last_name": "'"$PATIENT_LAST_NAME"'",
    "email": "'"$PATIENT_EMAIL"'",
    "phone": "'"$PATIENT_PHONE"'",
    "date_of_birth": "'"$PATIENT_DOB"'",
    "gender": "'"$PATIENT_GENDER"'",
    "height_cm": '"$PATIENT_HEIGHT"',
    "weight_kg": '"$PATIENT_WEIGHT"'
  }'
```

**Expected Response (201 Created):**
```json
{
  "id": "uuid-here",
  "clinic_id": "uuid-from-token",
  "first_name": "Rajesh",
  "last_name": "Verma",
  "email": "rajesh@example.com",
  "phone": "9123456789",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "height_cm": 180,
  "weight_kg": 75,
  "created_at": "2026-05-18T08:10:13",
  "updated_at": "2026-05-18T08:10:13"
}
```

**Save Patient ID:**
```bash
# Extract and save patient ID
PATIENT_ID="uuid-from-response"
echo "PATIENT_ID=$PATIENT_ID" >> /tmp/test_tokens.txt
```

---

### Test 6: Get All Patients (Pagination)

**Purpose**: सभी patients को list करना pagination के साथ | Retrieve all patients with pagination.

```bash
# Get first page (10 patients per page)
curl -X GET "http://localhost:8000/api/v1/patients?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid-here",
      "clinic_id": "uuid-from-token",
      "first_name": "Rajesh",
      "last_name": "Verma",
      "email": "rajesh@example.com",
      "phone": "9123456789",
      "date_of_birth": "1990-05-15",
      "gender": "male",
      "height_cm": 180,
      "weight_kg": 75,
      "created_at": "2026-05-18T08:10:13",
      "updated_at": "2026-05-18T08:10:13"
    }
  ],
  "meta": {
    "pagination": {
      "total": 1,
      "page": 1,
      "page_size": 10,
      "total_pages": 1
    }
  }
}
```

**Test Pagination:**
```bash
# Get second page
curl -X GET "http://localhost:8000/api/v1/patients?page=2&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# Expected: data array should be empty if only 1 patient exists
```

---

### Test 7: Get Single Patient

**Purpose**: किसी एक patient की detailed information लेना | Retrieve details of a specific patient.

```bash
source /tmp/test_tokens.txt

curl -X GET "http://localhost:8000/api/v1/patients/$PATIENT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "id": "uuid-here",
  "clinic_id": "uuid-from-token",
  "first_name": "Rajesh",
  "last_name": "Verma",
  "email": "rajesh@example.com",
  "phone": "9123456789",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "height_cm": 180,
  "weight_kg": 75,
  "created_at": "2026-05-18T08:10:13",
  "updated_at": "2026-05-18T08:10:13"
}
```

---

### Test 8: Get Non-existent Patient

**Purpose**: ऐसे patient को access करने की कोशिश जो clinic के अंदर नहीं है | Test clinic isolation security.

```bash
# Try to get with invalid patient ID
curl -X GET "http://localhost:8000/api/v1/patients/invalid-uuid-12345" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (404 Not Found):**
```json
{
  "detail": "Patient not found"
}
```

---

### Test 9: Unauthorized Patient Access

**Purpose**: बिना token के patient endpoint को access करना | Test authentication enforcement.

```bash
# Without Authorization header
curl -X GET "http://localhost:8000/api/v1/patients"
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Not authenticated"
}
```

---

### Test 10: Invalid Token

**Purpose**: गलत token के साथ access करना | Test token validation.

```bash
curl -X GET "http://localhost:8000/api/v1/patients" \
  -H "Authorization: Bearer invalid-token-here"
```

**Expected Response (401 Unauthorized):**
```json
{
  "detail": "Invalid authentication credentials"
}
```

---

## 💪 EXERCISE ENDPOINTS TESTING

### Test 11: Create Exercise (Admin Only)

**Purpose**: नया exercise बनाना (admin के लिए) | Create a new exercise (admin only).

```bash
source /tmp/test_tokens.txt

# Test Data
EXERCISE_TITLE="Neck Rotation"
EXERCISE_BODY_PART="neck"
EXERCISE_DESCRIPTION="Rotate head slowly in circular motion"
EXERCISE_VIDEO_URL="https://example.com/videos/neck-rotation.mp4"
EXERCISE_IS_FREE=true

# cURL Command
curl -X POST http://localhost:8000/api/v1/exercises \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "'"$EXERCISE_TITLE"'",
    "body_part": "'"$EXERCISE_BODY_PART"'",
    "description": "'"$EXERCISE_DESCRIPTION"'",
    "video_url": "'"$EXERCISE_VIDEO_URL"'",
    "is_free": '"$EXERCISE_IS_FREE"'
  }'
```

**Expected Response (201 Created):**
```json
{
  "id": "uuid-here",
  "clinic_id": null,
  "title": "Neck Rotation",
  "body_part": "neck",
  "description": "Rotate head slowly in circular motion",
  "video_url": "https://example.com/videos/neck-rotation.mp4",
  "is_free": true,
  "created_at": "2026-05-18T08:10:13",
  "updated_at": "2026-05-18T08:10:13"
}
```

**Schema Details** (title बदलना बहुत जरूरी है | title field is required):
```python
# Exercise Schema Structure
{
    "title": str,                    # ✅ Required: Exercise name
    "body_part": str (optional),     # Neck, shoulder, back, knee, etc.
    "description": str (optional),   # Exercise instructions
    "video_url": str (optional),     # Link to demo video
    "is_free": bool                  # Whether exercise is free or premium
}
```

**Save Exercise ID:**
```bash
EXERCISE_ID="uuid-from-response"
echo "EXERCISE_ID=$EXERCISE_ID" >> /tmp/test_tokens.txt
```

---

### Test 12: Get All Exercises (With Filtering)

**Purpose**: सभी exercises को list करना filtering के साथ | Retrieve exercises with advanced filtering.

```bash
source /tmp/test_tokens.txt

# Get all exercises
curl -X GET "http://localhost:8000/api/v1/exercises" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "data": [
    {
      "id": "uuid-here",
      "clinic_id": "null",
      "name": "Neck Rotation",
      "body_part": "neck",
      "description": "Rotate head slowly in circular motion",
      "recommended_reps": 10,
      "recommended_sets": 3,
      "duration_seconds": 60,
      "is_free": true,
      "is_custom_to_clinic": false,
      "created_at": "2026-05-18T08:10:13",
      "updated_at": "2026-05-18T08:10:13"
    }
  ],
  "meta": {
    "pagination": {
      "total": 1,
      "page": 1,
      "page_size": 10,
      "total_pages": 1
    }
  }
}
```

---

### Test 13: Filter Exercises by Body Part

**Purpose**: किसी खास body part के exercises को filter करना | Filter exercises by body part.

```bash
# Filter by neck exercises
curl -X GET "http://localhost:8000/api/v1/exercises?body_part=neck" \
  -H "Authorization: Bearer $TOKEN"

# Filter by shoulder exercises
curl -X GET "http://localhost:8000/api/v1/exercises?body_part=shoulder" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response**: Only exercises with matching body_part

**Query Parameters**:
- `body_part` - Filter by body part (neck, shoulder, back, knee, etc.)
- `is_free` - Filter by free status (true/false)

---

### Test 14: Get Single Exercise

**Purpose**: किसी एक exercise की details लेना | Get a specific exercise.

```bash
source /tmp/test_tokens.txt

curl -X GET "http://localhost:8000/api/v1/exercises/$EXERCISE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "id": "uuid-here",
  "clinic_id": null,
  "title": "Neck Rotation",
  "body_part": "neck",
  "description": "Rotate head slowly in circular motion",
  "video_url": "https://example.com/videos/neck-rotation.mp4",
  "is_free": true,
  "created_at": "2026-05-18T08:10:13",
  "updated_at": "2026-05-18T08:10:13"
}
```

---

### Test 15: Search Exercises

**Purpose**: Exercise को search करना | Search exercises by title or description.

```bash
curl -X GET "http://localhost:8000/api/v1/exercises?search=rotation" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response**: Matching exercises

**Note**: Search अभी implement नहीं है | Currently not fully implemented - returns all exercises

---

## ⚠️ ERROR SCENARIOS

### Test 17: Missing Required Fields

**Purpose**: Required fields के बिना request भेजना | Test input validation.

```bash
source /tmp/test_tokens.txt

# Missing first_name
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "last_name": "Verma",
    "email": "test@example.com"
  }'
```

**Expected Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "first_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

### Test 18: Invalid Data Type

**Purpose**: गलत data type के साथ request भेजना | Test data type validation.

```bash
source /tmp/test_tokens.txt

# height_cm should be number, not string
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "phone": "9876543210",
    "date_of_birth": "1990-05-15",
    "gender": "male",
    "height_cm": "invalid_number",
    "weight_kg": 75
  }'
```

**Expected Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "height_cm"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

---

### Test 19: Invalid Email Format

**Purpose**: गलत format की email भेजना | Test email validation.

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_name": "Test Clinic",
    "clinic_email": "invalid-email",
    "clinic_phone": "9876543210",
    "admin_email": "invalid-email",
    "admin_password": "Password@123",
    "admin_name": "Admin Name"
  }'
```

**Expected Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "admin_email"],
      "msg": "invalid email format",
      "type": "value_error.email"
    }
  ]
}
```

---

### Test 20: Duplicate Email Registration

**Purpose**: पहले से registered email से दोबारा registration करना | Test duplicate prevention.

```bash
# First registration (should succeed)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_name": "Clinic A",
    "clinic_email": "clinica@test.com",
    "clinic_phone": "9876543210",
    "admin_email": "admin@clinica.com",
    "admin_password": "Password@123",
    "admin_name": "Admin Name"
  }'

# Second registration with same email (should fail)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_name": "Clinic B",
    "clinic_email": "clinicb@test.com",
    "clinic_phone": "9876543211",
    "admin_email": "admin@clinica.com",
    "admin_password": "Password@123",
    "admin_name": "Admin Name"
  }'
```

**Expected Response (409 Conflict):**
```json
{
  "detail": "Email already registered"
}
```

---

## 🔧 TROUBLESHOOTING

### Issue 1: Connection Refused

**Problem**: `curl: (7) Failed to connect to localhost port 8000`

**Solution**:
```bash
# Check if server is running
ps aux | grep uvicorn

# If not running, start it
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Issue 2: 404 Not Found

**Problem**: API returns 404 for valid endpoints

**Solution**:
```bash
# Check endpoint path is correct
# Should be: http://localhost:8000/api/v1/{resource}

# Verify router is registered in main.py
grep "include_router" /home/shit/DFQ/av-suite/backend/app/main.py
```

---

### Issue 3: 500 Internal Server Error

**Problem**: API returns 500 error

**Solution**:
```bash
# Check server logs in terminal where uvicorn is running
# Look for error messages

# Verify database connection
python3 /home/shit/DFQ/av-suite/backend/test_supabase_connection.py

# Check .env file for correct DATABASE_URL
cat /home/shit/DFQ/av-suite/backend/.env
```

---

### Issue 4: Invalid Token

**Problem**: `"detail": "Invalid authentication credentials"`

**Solution**:
```bash
# Token may have expired (24 hours)
# Re-login to get new token

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@testclinic.com",
    "password": "AdminTest@123"
  }'

# Copy new token and use in requests
```

---

### Issue 5: CORS Error in Browser

**Problem**: Browser shows CORS error

**Solution**:
```bash
# CORS is configured for development
# Should work for http://localhost:3000 and http://localhost:8000

# Check CORS config in app/core/config.py
grep -A 5 "allow_origins" /home/shit/DFQ/av-suite/backend/app/core/config.py
```

---

### Issue 6: Database Connection Failed

**Problem**: `"detail": "Database connection failed"`

**Solution**:
```bash
# Verify .env file
cat /home/shit/DFQ/av-suite/backend/.env

# Test connection directly
python3 /home/shit/DFQ/av-suite/backend/test_supabase_connection.py

# Verify Supabase account is active
# Visit https://supabase.com/dashboard

# Check session pooler is enabled
# Connection string should have "pooler" subdomain
```

---

## ✅ TEST RESULTS CHECKLIST

Use this checklist to verify all endpoints are working:

### Authentication Tests
- [ ] Test 1: User Registration - ✅ PASSED / ❌ FAILED
- [ ] Test 2: User Login - ✅ PASSED / ❌ FAILED
- [ ] Test 3: Invalid Password - ✅ PASSED / ❌ FAILED
- [ ] Test 4: Non-existent Email - ✅ PASSED / ❌ FAILED

### Patient Tests
- [ ] Test 5: Create Patient - ✅ PASSED / ❌ FAILED
- [ ] Test 6: Get All Patients - ✅ PASSED / ❌ FAILED
- [ ] Test 7: Get Single Patient - ✅ PASSED / ❌ FAILED
- [ ] Test 8: Get Non-existent Patient - ✅ PASSED / ❌ FAILED
- [ ] Test 9: Unauthorized Access - ✅ PASSED / ❌ FAILED
- [ ] Test 10: Invalid Token - ✅ PASSED / ❌ FAILED

### Exercise Tests
- [ ] Test 11: Create Exercise - ✅ PASSED / ❌ FAILED
- [ ] Test 12: Get All Exercises - ✅ PASSED / ❌ FAILED
- [ ] Test 13: Filter by Body Part - ✅ PASSED / ❌ FAILED
- [ ] Test 14: Filter by Free Status - ✅ PASSED / ❌ FAILED
- [ ] Test 15: Get Single Exercise - ✅ PASSED / ❌ FAILED
- [ ] Test 16: Search Exercises - ✅ PASSED / ❌ FAILED

### Error Scenario Tests
- [ ] Test 17: Missing Required Fields - ✅ PASSED / ❌ FAILED
- [ ] Test 18: Invalid Data Type - ✅ PASSED / ❌ FAILED
- [ ] Test 19: Invalid Email Format - ✅ PASSED / ❌ FAILED
- [ ] Test 20: Duplicate Email - ✅ PASSED / ❌ FAILED

---

## 📝 MANUAL TEST LOG

**Date**: _______________  
**Tester**: _______________

### Test Summary
- Total Tests Run: _____
- Passed: _____
- Failed: _____
- Notes: _____________________

### Issues Found
1. ___________________
2. ___________________
3. ___________________

### Next Steps
1. ___________________
2. ___________________

---

## 💡 QUICK REFERENCE COMMANDS

### Save Token for Reuse
```bash
# After login, save token to file
TOKEN="your-token-here"
echo $TOKEN > /tmp/token.txt

# Use in subsequent requests
curl -X GET http://localhost:8000/api/v1/patients \
  -H "Authorization: Bearer $(cat /tmp/token.txt)"
```

### Pretty Print JSON Response
```bash
# Pipe to python for readable output
curl -s http://localhost:8000/api/v1/patients | python3 -m json.tool
```

### Save Full Response to File
```bash
curl -X GET http://localhost:8000/api/v1/patients \
  -H "Authorization: Bearer $TOKEN" > /tmp/patients_response.json

# View response
cat /tmp/patients_response.json | python3 -m json.tool
```

### Test Multiple Scenarios at Once
```bash
# Create shell script for batch testing
cat > /tmp/test_apis.sh << 'EOF'
#!/bin/bash
source /tmp/test_tokens.txt

echo "Testing Auth Login..."
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@testclinic.com","password":"AdminTest@123"}'

echo "\nTesting Get Patients..."
curl -X GET "http://localhost:8000/api/v1/patients" \
  -H "Authorization: Bearer $TOKEN"

echo "\nTesting Get Exercises..."
curl -X GET "http://localhost:8000/api/v1/exercises" \
  -H "Authorization: Bearer $TOKEN"
EOF

chmod +x /tmp/test_apis.sh
/tmp/test_apis.sh
```

---

## 🎯 NEXT STEPS AFTER TESTING

Once all tests pass, you should:

1. ✅ Verify database contains created records
2. ✅ Run automated tests: `pytest tests/ -v`
3. ✅ Check code quality: Review API_DOCUMENTATION.md
4. ✅ Deploy to staging environment
5. ✅ Load test with multiple concurrent requests
6. ✅ Monitor performance and logs
7. ✅ Plan for production deployment

---

**End of API Testing Guide**

Questions? Refer to:
- API_DOCUMENTATION.md - API reference
- SETUP_GUIDE.md - Development setup
- DEPLOYMENT_GUIDE.md - Production deployment
