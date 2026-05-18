"""
Module: exercises.py
Purpose: Exercise management API endpoints define karna
Yeh module exercise CRUD operations ke endpoints provide karta hai.
REST API endpoints jo exercise data ko manage aur serve karte hain.

API Endpoints:
- GET /api/v1/exercises - List exercises with filtering aur pagination
- POST /api/v1/exercises - Create new exercise (admin only)
- GET /api/v1/exercises/{id} - Get specific exercise details

Authorization:
- GET endpoints: All authenticated users (patients, physios, admins)
- POST endpoint: Admin users only
- Clinic + Global exercises: Clinic-specific aur global exercises visible

Features:
- Advanced filtering: Body part, free/paid, search
- Multi-clinic support: Clinic-specific aur global exercises
- Pagination support: Large exercise libraries handle
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid
import logging

from app.core.database import get_db
from app.schemas.exercise import ExerciseCreate, ExerciseRead
from app.schemas.envelope import ResponseEnvelope, MetaPagination
from app.schemas.common import PaginationParams
from app.dependencies.pagination import get_pagination_params
from app.services import exercise_service

logger = logging.getLogger(__name__)

# APIRouter instance jo exercise endpoints organize karta hai
# Prefix: /api/v1/exercises (main router mein define hota hai)
router = APIRouter()


@router.get(
    "",
    response_model=ResponseEnvelope[List[ExerciseRead]],
    tags=["Exercises"]
)
async def list_exercises(
    request: Request,
    body_part: Optional[str] = Query(None, description="Filter by body part"),
    is_free: Optional[bool] = Query(None, description="Filter by free/paid status"),
    search: Optional[str] = Query(None, description="Search in exercise title"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: Exercises list karna advanced filtering aur pagination ke saath
    Yeh endpoint exercise listing handle karta hai jismein:
    1. Clinic-specific + global exercises fetch karte hain
    2. Multiple filters apply karte hain (body_part, is_free, search)
    3. Pagination apply karte hain
    4. Metadata ke saath results return karte hain
    
    HTTP Method: GET
    URL: /api/v1/exercises
    Status Code: 200 OK
    
    Query Parameters:
    - body_part (str, optional): Filter exercises by body part (e.g., "Shoulder", "Knee")
    - is_free (bool, optional): Filter by pricing (true = free, false = paid)
    - search (str, optional): Search in exercise title (case-insensitive substring)
    - page (int, default: 1): Page number for pagination
    - page_size (int, default: 10): Results per page (max: 100)
    
    Request Headers:
    Authorization: Bearer {jwt_token}
    
    Response (ResponseEnvelope[List[ExerciseRead]]):
    {
        "status": "success",
        "data": [
            {
                "id": "uuid",
                "clinic_id": "uuid or null",
                "title": "Shoulder Rotation",
                "description": "Detailed description",
                "body_part": "Shoulder",
                "is_free": true,
                "video_url": "https://cdn.example.com/exercise.mp4",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            },
            ...
        ],
        "meta": {
            "total": 23,
            "page": 1,
            "page_size": 10
        }
    }
    
    Error Responses:
    - 401 UNAUTHORIZED: Missing or invalid JWT token
    - 400 BAD REQUEST: Invalid filter parameters or pagination
    - 500 INTERNAL_SERVER_ERROR: Database error
    
    Security:
    - JWT token required: All requests authenticated hone chahiye
    - Clinic isolation: Clinic-specific exercises visible + global exercises
    - No role restriction: All authenticated users can list
    
    Filtering Examples:
    - Body part filtering: GET /exercises?body_part=Shoulder
    - Free exercises only: GET /exercises?is_free=true
    - Search: GET /exercises?search=rotation
    - Combined: GET /exercises?body_part=Shoulder&is_free=true&search=rotation
    
    Pagination:
    - Server-side pagination: Large exercise libraries efficiently handle
    - Total count: Frontend pagination UI ke liye
    - Page size limit: DOS attack prevention
    
    Global Exercises:
    - clinic_id = null hote hain
    - Sab clinics ke users ko visible
    - Shared resource across platform
    
    Usage Example:
    curl -X GET "http://localhost:8000/api/v1/exercises?body_part=Shoulder&is_free=true&page=1" \\
      -H "Authorization: Bearer eyJhbGc..."
    """
    
    logger.info(f"List exercises - filters: body_part={body_part}, is_free={is_free}, search={search}")
    
    try:
        # request.state se clinic_id extract karte hain
        # JWT token decode se clinic_id set hota hai middleware mein
        clinic_id = request.state.clinic_id
        logger.debug(f"Fetching exercises for clinic: {clinic_id}")
        print("CLINIC_ID:", request.state.clinic_id)
        # Service layer ko call karte hain
        # Exercises list aur total count return hota hai with filters applied
        exercises, total = await exercise_service.get_exercises(
            db, clinic_id, pagination, body_part, is_free, search
        )
        
        # Pagination metadata prepare karte hain
        # Frontend pagination UI ke liye total aur current page info
        meta = MetaPagination(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
        logger.info(f"Retrieved {len(exercises)} exercises, total: {total}")
        return ResponseEnvelope(data=exercises, meta=meta)
        
    except Exception as e:
        logger.error(f"List exercises error: {str(e)}")
        raise


@router.post(
    "",
    response_model=ResponseEnvelope[ExerciseRead],
    status_code=201,
    tags=["Exercises"]
)
async def create_exercise(
    request: Request,
    exercise_in: ExerciseCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: New exercise create karna clinic mein (admin only)
    Yeh endpoint exercise creation handle karta hai.
    
    HTTP Method: POST
    URL: /api/v1/exercises
    Status Code: 201 CREATED (new exercise created)
    
    Request Body (ExerciseCreate):
    {
        "title": "Shoulder Rotation",                      # Required
        "description": "Step by step instructions...",     # Optional
        "body_part": "Shoulder",                          # Optional
        "is_free": true,                                   # Optional (default: false)
        "video_url": "https://cdn.example.com/video.mp4"  # Optional
    }
    
    Request Headers:
    Authorization: Bearer {jwt_token}
    Content-Type: application/json
    
    Response (ResponseEnvelope[ExerciseRead]):
    {
        "status": "success",
        "data": {
            "id": "new-uuid",
            "clinic_id": "clinic-uuid",
            "title": "Shoulder Rotation",
            "description": "Step by step instructions...",
            "body_part": "Shoulder",
            "is_free": true,
            "video_url": "https://cdn.example.com/video.mp4",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    }
    
    Error Responses:
    - 401 UNAUTHORIZED: Missing or invalid JWT token
    - 403 FORBIDDEN: User role is not admin
    - 400 BAD REQUEST: Invalid request body or validation failure
    - 500 INTERNAL_SERVER_ERROR: Database error
    
    Security:
    - JWT token required: All requests authenticated
    - Admin only: Only admin role create kar sakte hain (no physios, patients)
    - Clinic isolation: Exercise automatically current clinic se associated
    - Input validation: Pydantic schema se strict validation
    
    Authorization:
    - Admin: Can create exercises
    - Physio: Cannot create (read-only access)
    - Patient: Cannot create (no access)
    
    Business Logic:
    1. Authorization check - admin role required
    2. Request data validation (Pydantic schema)
    3. Exercise database record create
    4. Created exercise return
    
    Video URL Recommendations:
    - Use CDN URLs (AWS S3, Azure Blob, Cloudinary)
    - Support multiple formats (mp4, webm, etc.)
    - Compression for fast loading
    
    Usage Example:
    curl -X POST http://localhost:8000/api/v1/exercises \\
      -H "Authorization: Bearer eyJhbGc..." \\
      -H "Content-Type: application/json" \\
      -d '{
        "title": "Shoulder Rotation",
        "description": "Rotate your shoulder in circular motion clockwise and counterclockwise.",
        "body_part": "Shoulder",
        "is_free": true,
        "video_url": "https://cdn.example.com/exercise-shoulder-rotation.mp4"
      }'
    """
    
    logger.info(f"Create exercise request - {exercise_in.title}")
    
    try:
        # request.state se role extract karte hain
        # JWT token decode se role set hota hai middleware mein
        role = request.state.role
        
        # Admin-only check
        if role != "admin":
            logger.warning(f"Unauthorized exercise creation attempt with role: {role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create exercises"
            )
        
        logger.debug(f"Admin authorization check passed for role: {role}")
        
        # request.state se clinic_id extract karte hain
        clinic_id = request.state.clinic_id
        logger.debug(f"Creating exercise in clinic: {clinic_id}")
        
        # Service layer ko call karte hain
        # New exercise database record create hota hai
        exercise = await exercise_service.create_exercise(db, clinic_id, exercise_in)
        
        logger.info(f"Exercise created successfully: {exercise.id}")
        return ResponseEnvelope(data=exercise)
        
    except HTTPException:
        # Already handled exceptions ko re-raise karte hain
        raise
    except Exception as e:
        logger.error(f"Create exercise error: {str(e)}")
        raise


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[ExerciseRead],
    tags=["Exercises"]
)
async def get_exercise(
    request: Request,
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: Specific exercise ke details fetch karna
    Yeh endpoint exercise details retrieve karta hai by ID.
    
    HTTP Method: GET
    URL: /api/v1/exercises/{id}
    Status Code: 200 OK (found)
    
    Path Parameters:
    - id (str): Exercise UUID
    
    Request Headers:
    Authorization: Bearer {jwt_token}
    
    Response (ResponseEnvelope[ExerciseRead]):
    {
        "status": "success",
        "data": {
            "id": "exercise-uuid",
            "clinic_id": "clinic-uuid or null",
            "title": "Shoulder Rotation",
            "description": "Detailed description",
            "body_part": "Shoulder",
            "is_free": true,
            "video_url": "https://cdn.example.com/exercise.mp4",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    }
    
    Error Responses:
    - 401 UNAUTHORIZED: Missing or invalid JWT token
    - 404 NOT_FOUND: Exercise not found or not accessible to user's clinic
    - 400 BAD REQUEST: Invalid exercise ID format
    - 500 INTERNAL_SERVER_ERROR: Database error
    
    Security:
    - JWT token required: All requests authenticated
    - Clinic + Global access: User's clinic exercises + global exercises visible
    - No role restriction: All authenticated users can view
    
    Accessible Exercises:
    - Clinic-specific exercises: clinic_id matches user's clinic
    - Global exercises: clinic_id = null (shared across all clinics)
    - Other clinics' exercises: Not accessible (404)
    
    Business Logic:
    1. Exercise fetch by ID
    2. Clinic verification (clinic-specific ya global)
    3. Exercise found = return data, Not found = 404
    
    Usage Example:
    curl -X GET http://localhost:8000/api/v1/exercises/12345678-1234-5678-1234-567812345678 \\
      -H "Authorization: Bearer eyJhbGc..."
    
    Use Cases:
    - Get exercise details for patient view
    - Fetch video URL for streaming
    - Load exercise instructions
    - Retrieve exercise metadata for prescriptions
    """
    
    logger.info(f"Get exercise request - id: {id}")
    
    try:
        # request.state se clinic_id extract karte hain
        clinic_id = request.state.clinic_id
        logger.debug(f"Fetching exercise {id} for clinic {clinic_id}")
        
        # Service layer ko call karte hain
        # Exercise fetch hota hai by ID aur clinic check
        # Clinic-specific + global exercises accessible
        exercise = await exercise_service.get_exercise_by_id(db, clinic_id, id)
        
        # Exercise not found - 404 error return
        if not exercise:
            logger.warning(f"Exercise not found: {id} for clinic {clinic_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise not found or not in caller's clinic"
            )
        
        logger.info(f"Exercise found: {exercise.id}")
        return ResponseEnvelope(data=exercise)
        
    except HTTPException:
        # Already handled exceptions ko re-raise karte hain
        raise
    except Exception as e:
        logger.error(f"Get exercise error: {str(e)}")
        raise

