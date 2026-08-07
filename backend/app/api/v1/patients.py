"""
Module: patients.py
Purpose: Patient management API endpoints define karna
Yeh module patient CRUD operations ke endpoints provide karta hai.
REST API endpoints jo patient data ko manage karte hain.

API Endpoints:
- GET /api/v1/patients - List all clinic patients with pagination
- POST /api/v1/patients - Create new patient
- GET /api/v1/patients/{id} - Get specific patient details

Authorization:
- All endpoints require valid JWT token
- check_therapist_or_admin: Therapists aur admins ko access
- Clinic isolation: Patient data sirf user ke clinic mein accessible

Response Format:
All responses ResponseEnvelope mein wrapped hote hain with pagination metadata.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import logging
from app.enums.user import UserRole

from app.core.database import get_db
from app.core.dependencies import require_roles, require_admin
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.schemas.envelope import ResponseEnvelope, MetaPagination
from app.schemas.common import PaginationParams
from app.dependencies.pagination import get_pagination_params
from app.services import patient_service

logger = logging.getLogger(__name__)

# APIRouter instance jo patient endpoints organize karta hai
# Prefix: /api/v1/patients (main router mein define hota hai)
router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.THERAPIST, UserRole.FRONT_DESK))])




@router.get(
    "",
    response_model=ResponseEnvelope[List[PatientRead]],
    tags=["Patients"]
)
async def list_patients(
    request: Request,
    search: Optional[str] = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: Clinic ke sare patients ko list karna pagination ke saath
    Yeh endpoint patient listing handle karta hai jismein:
    1. Authorization check (therapist ya admin)
    2. Clinic-specific patients fetch karte hain
    3. Pagination apply karte hain
    4. Metadata ke saath results return karte hain
    
    HTTP Method: GET
    URL: /api/v1/patients
    Status Code: 200 OK
    
    Query Parameters (PaginationParams):
    - page: Page number (1-based, default: 1)
    - page_size: Results per page (default: 10, max: 100)
    
    Request Headers:
    Authorization: Bearer {jwt_token}
    
    Response (ResponseEnvelope[List[PatientRead]]):
    {
        "status": "success",
        "data": [
            {
                "id": "uuid",
                "clinic_id": "uuid",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-01",
                "phone": "9876543210",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            ...
        ],
        "meta": {
            "total": 45,
            "page": 1,
            "page_size": 10
        }
    }
    
    Error Responses:
    - 401 UNAUTHORIZED: Missing or invalid JWT token
    - 403 FORBIDDEN: User role (patient, nurse) is not authorized
    - 400 BAD REQUEST: Invalid pagination parameters
    - 500 INTERNAL_SERVER_ERROR: Database error
    
    Security:
    - JWT token required: All requests authenticated hone chahiye
    - Clinic isolation: Sirf user ke clinic ke patients visible
    - Role check: Only admin/therapist access kar sakte hain
    
    Pagination:
    - Server-side pagination: Large datasets efficiently handle
    - Total count: Frontend pagination UI ke liye
    - Page size limit: DOS attack prevention
    
    Usage Example:
    curl -X GET "http://localhost:8000/api/v1/patients?page=1&page_size=10" \\
      -H "Authorization: Bearer eyJhbGc..."
    """
    
    logger.info(f"List patients request - page: {pagination.page}, size: {pagination.page_size}")
    
    try:
        # Authorization check is handled by Depends
        
        # request.state se clinic_id extract karte hain
        # JWT token decode se clinic_id set hota hai middleware mein
        clinic_id = request.state.clinic_id
        logger.debug(f"Fetching patients for clinic: {clinic_id}")
        
        # Service layer ko call karte hain
        # Patients list aur total count return hota hai
        if search:
            patients, total = await patient_service.search_patients(db, clinic_id, search, pagination)
        else:
            patients, total = await patient_service.get_patients(db, clinic_id, pagination)
        
        # Pagination metadata prepare karte hain
        # Frontend pagination UI ke liye total aur current page info
        meta = MetaPagination(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        logger.info(f"Retrieved {len(patients)} patients, total: {total}")
        return ResponseEnvelope(data=patients, meta=meta)
        
    except Exception as e:
        logger.error(f"List patients error: {str(e)}")
        raise


@router.post(
    "",
    response_model=ResponseEnvelope[PatientRead],
    status_code=201,
    tags=["Patients"]
)
async def create_patient(
    request: Request,
    patient_in: PatientCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: New patient create karna clinic mein
    Yeh endpoint patient registration handle karta hai.
    
    HTTP Method: POST
    URL: /api/v1/patients
    Status Code: 201 CREATED (new patient created)
    
    Request Body (PatientCreate):
    {
        "first_name": "John",              # Required
        "last_name": "Doe",                # Required
        "date_of_birth": "1990-01-01",     # Optional
        "phone": "9876543210"              # Optional
    }
    
    Request Headers:
    Authorization: Bearer {jwt_token}
    Content-Type: application/json
    
    Response (ResponseEnvelope[PatientRead]):
    {
        "status": "success",
        "data": {
            "id": "new-uuid",
            "clinic_id": "clinic-uuid",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "phone": "9876543210",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    }
    
    Error Responses:
    - 401 UNAUTHORIZED: Missing or invalid JWT token
    - 403 FORBIDDEN: User role not authorized for patient creation
    - 400 BAD REQUEST: Invalid request body or validation failure
    - 500 INTERNAL_SERVER_ERROR: Database error
    
    Security:
    - JWT token required: All requests authenticated
    - Clinic isolation: Patient automatically current clinic se associated
    - Role check: Only admin/therapist create kar sakte hain
    
    Business Logic:
    1. Authorization check - therapist ya admin
    2. Request data validation (Pydantic schema)
    3. Patient database record create
    4. Created patient return
    
    Usage Example:
    curl -X POST http://localhost:8000/api/v1/patients \\
      -H "Authorization: Bearer eyJhbGc..." \\
      -H "Content-Type: application/json" \\
      -d '{
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-01-01",
        "phone": "9876543210"
      }'
    """
    
    logger.info(f"Create patient request - {patient_in.first_name} {patient_in.last_name}")
    
    try:
        # Authorization check is handled by Depends
        
        # request.state se clinic_id extract karte hain
        clinic_id = request.state.clinic_id
        logger.debug(f"Creating patient in clinic: {clinic_id}")
        
        # Service layer ko call karte hain
        # New patient database record create hota hai
        patient = await patient_service.create_patient(db, clinic_id, patient_in)
        
        logger.info(f"Patient created successfully: {patient.id}")
        return ResponseEnvelope(data=patient)
        
    except Exception as e:
        logger.error(f"Create patient error: {str(e)}")
        raise


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[PatientRead],
    tags=["Patients"]
)
async def get_patient(
    request: Request,
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: Specific patient ke details fetch karna
    Yeh endpoint patient details retrieve karta hai by ID.
    
    HTTP Method: GET
    URL: /api/v1/patients/{id}
    Status Code: 200 OK (found)
    
    Path Parameters:
    - id (str): Patient UUID
    
    Request Headers:
    Authorization: Bearer {jwt_token}
    
    Response (ResponseEnvelope[PatientRead]):
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
    
    Error Responses:
    - 401 UNAUTHORIZED: Missing or invalid JWT token
    - 403 FORBIDDEN: User role not authorized
    - 404 NOT_FOUND: Patient not found or not in user's clinic
    - 400 BAD REQUEST: Invalid patient ID format
    - 500 INTERNAL_SERVER_ERROR: Database error
    
    Security:
    - JWT token required: All requests authenticated
    - Clinic isolation: Patient sirf user ke clinic mein
    - Role check: Only admin/therapist access kar sakte hain
    - Cross-clinic prevention: Can't access other clinic's patients
    
    Business Logic:
    1. Authorization check - therapist ya admin
    2. Patient fetch by ID aur clinic check
    3. Patient found = return data, Not found = 404
    
    Usage Example:
    curl -X GET http://localhost:8000/api/v1/patients/12345678-1234-5678-1234-567812345678 \\
      -H "Authorization: Bearer eyJhbGc..."
    """
    
    logger.info(f"Get patient request - id: {id}")
    
    try:
        # Authorization check is handled by Depends
        
        # request.state se clinic_id extract karte hain
        clinic_id = request.state.clinic_id
        logger.debug(f"Fetching patient {id} from clinic {clinic_id}")
        
        # Service layer ko call karte hain
        # Patient fetch hota hai by ID aur clinic check
        patient = await patient_service.get_patient_by_id(db, clinic_id, id)
        
        # Patient not found - 404 error return
        if not patient:
            logger.warning(f"Patient not found: {id} in clinic {clinic_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found or not in caller's clinic"
            )
        
        logger.info(f"Patient found: {patient.id}")
        return ResponseEnvelope(data=patient)
        
    except HTTPException:
        # Already handled exceptions ko re-raise karte hain
        raise
    except Exception as e:
        logger.error(f"Get patient error: {str(e)}")
        raise

@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[PatientRead],
    tags=["Patients"]
)
async def update_patient(
    request: Request,
    id: str,
    patient_in: PatientUpdate,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Update patient request - id: {id}")
    try:
        clinic_id = request.state.clinic_id
        
        patient = await patient_service.update_patient(db, clinic_id, id, patient_in)
        return ResponseEnvelope(data=patient)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update patient error: {str(e)}")
        raise

@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[None],
    tags=["Patients"]
)
async def delete_patient(
    request: Request,
    id: str,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_admin)
):
    logger.info(f"Delete patient request - id: {id}")
    try:
        clinic_id = request.state.clinic_id
        user_id = request.state.user_id
        
        await patient_service.delete_patient(db, clinic_id, id, user_id)
        return ResponseEnvelope(data=None)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete patient error: {str(e)}")
        raise


