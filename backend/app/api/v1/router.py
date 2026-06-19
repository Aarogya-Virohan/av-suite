"""
Module: router.py
Purpose: API V1 endpoints को consolidate aur organize karna
Yeh module API V1 routes ko combine karta hai aur main application mein include karta hai.
Router hierarchy ke through endpoint organization manage hota hai.

API Structure:
/api/v1/
├── /auth (Authentication endpoints)
│   ├── POST /register - New user registration
│   └── POST /login - User login
├── /exercises (Exercise management)
│   ├── GET / - List exercises with filters
│   ├── POST / - Create new exercise (admin only)
│   └── GET /{id} - Get exercise details
└── /patients (Patient management)
    ├── GET / - List clinic patients
    ├── POST / - Create new patient
    └── GET /{id} - Get patient details

Router Composition:
- Authentication routes: auth.router
- Exercise routes: exercises.router
- Patient routes: patients.router

Each router independently defined aur yahan combined hota hai.
"""

from fastapi import APIRouter
from app.api.v1 import auth, exercises, patients, posture, prescriptions
import logging

logger = logging.getLogger(__name__)

# Main API V1 Router
# Sab V1 endpoints yahan organize hote hain
# Main app mein prefix ke saath include hota hai (/api/v1)
api_router = APIRouter()

# Authentication Router
# Prefix: /api/v1/auth
# Endpoints: /register, /login (public, no authentication required)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)
logger.info("Auth router included: /api/v1/auth")

# Exercises Router
# Prefix: /api/v1/exercises
# Endpoints: GET /, POST /, GET /{id}
# Authentication: Required (JWT token)
# Authorization: All authenticated users can list/read, admin only create
api_router.include_router(
    exercises.router,
    prefix="/exercises",
    tags=["Exercises"]
)
logger.info("Exercises router included: /api/v1/exercises")

# Patients Router
# Prefix: /api/v1/patients
# Endpoints: GET /, POST /, GET /{id}
# Authentication: Required (JWT token)
# Authorization: Admin and physio roles only
api_router.include_router(
    patients.router,
    prefix="/patients",
    tags=["Patients"]
)
logger.info("Patients router included: /api/v1/patients")

# Posture Router
# Prefix: /api/v1/posture
# Endpoints: POST /sessions, GET /sessions, GET /sessions/{id}
# Authentication: Required (JWT token)
api_router.include_router(
    posture.router,
    prefix="/posture",
    tags=["Posture"]
)
logger.info("Posture router included: /api/v1/posture")

# Prescriptions Router
# Prefix: /api/v1/prescriptions
# Endpoints: POST /, GET /, GET /{id}, PATCH /{id}, POST /{id}/pdf
# Authentication: Required (JWT token)
api_router.include_router(
    prescriptions.router,
    prefix="/prescriptions",
    tags=["Prescriptions"]
)
logger.info("Prescriptions router included: /api/v1/prescriptions")


