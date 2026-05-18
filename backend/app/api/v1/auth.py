"""
Module: auth.py
Purpose: Authentication API endpoints define karna
Yeh module user registration aur login endpoints provide karta hai.
REST API endpoints jo authentication flow handle karte hain.

API Endpoints:
- POST /api/v1/auth/register - New user registration aur clinic creation
- POST /api/v1/auth/login - User login with email/password

Response Format:
All responses ResponseEnvelope mein wrapped hote hain consistency ke liye.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.envelope import ResponseEnvelope
from app.services import auth_service
import logging

logger = logging.getLogger(__name__)

# APIRouter instance jo auth endpoints organize karta hai
# Prefix: /api/v1/auth (main router mein define hota hai)
router = APIRouter()


@router.post(
    "/register",
    response_model=ResponseEnvelope[TokenResponse],
    status_code=201,
    tags=["Authentication"]
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: New user aur clinic ko register karna signup flow mein
    Yeh endpoint signup process handle karta hai jo:
    1. New clinic create karta hai
    2. Admin user create karta hai clinic owner ke taur par
    3. JWT token generate karta hai authentication ke liye
    
    HTTP Method: POST
    URL: /api/v1/auth/register
    Status Code: 201 CREATED (successful registration)
    
    Request Body (RegisterRequest):
    {
        "email": "admin@clinic.com",           # Admin user ka email (unique)
        "password": "SecurePassword123!",      # Strong password required
        "clinic_name": "City Medical Clinic"   # New clinic ka name
    }
    
    Response (ResponseEnvelope[TokenResponse]):
    {
        "status": "success",
        "data": {
            "access_token": "eyJhbGc...",      # JWT bearer token
            "token_type": "bearer"
        }
    }
    
    Error Responses:
    - 409 CONFLICT: Email already registered (duplicate email)
    - 400 BAD REQUEST: Invalid input format or validation failure
    - 500 INTERNAL_SERVER_ERROR: Database or server error
    
    Security Considerations:
    - Password hashing: Plain password kabhi stored nahi hota
    - Clinic isolation: New clinic automatic create hota hai
    - Admin role: First user always admin role se create hota hai
    - HTTPS required: Production mein plain HTTP allow nahi
    
    Usage Pattern:
    1. Frontend signup form fill karta hai
    2. POST request send karta hai email, password, clinic_name ke saath
    3. Backend clinic create karta hai aur admin user add karta hai
    4. JWT token return hota hai mobile/client ko
    5. Token localStorage/sessionStorage mein save hota hai
    6. Future requests ke headers mein token include hota hai
    
    Example cURL:
    curl -X POST http://localhost:8000/api/v1/auth/register \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "admin@clinic.com",
        "password": "SecurePassword123!",
        "clinic_name": "City Medical Clinic"
      }'
    """
    
    logger.info(f"Registration request received for email: {request.email}")
    
    try:
        # Service layer ko call karte hain registration logic ke liye
        # Service database operations handle karta hai
        token_response = await auth_service.register_user(db, request)
        
        # ResponseEnvelope mein wrap karte hain consistent format ke liye
        # All API responses same structure follow karte hain
        logger.info(f"User registered successfully: {request.email}")
        return ResponseEnvelope(data=token_response)
        
    except Exception as e:
        # Exceptions service layer se propagate hote hain
        # FastAPI automatically error responses generate karta hai
        logger.error(f"Registration failed: {str(e)}")
        raise


@router.post(
    "/login",
    response_model=ResponseEnvelope[TokenResponse],
    tags=["Authentication"]
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint ka purpose: Existing user ko authenticate karna login flow mein
    Yeh endpoint login process handle karta hai jo:
    1. Email se user database mein search karta hai
    2. Password verification karta hai (bcrypt comparison)
    3. JWT token generate karta hai successful auth par
    
    HTTP Method: POST
    URL: /api/v1/auth/login
    Status Code: 200 OK (successful login)
    
    Request Body (LoginRequest):
    {
        "email": "admin@clinic.com",          # Registered user email
        "password": "SecurePassword123!"      # Correct password
    }
    
    Response (ResponseEnvelope[TokenResponse]):
    {
        "status": "success",
        "data": {
            "access_token": "eyJhbGc...",    # JWT bearer token
            "token_type": "bearer"
        }
    }
    
    Error Responses:
    - 401 UNAUTHORIZED: Incorrect email or password (generic message)
    - 400 BAD REQUEST: Invalid input format
    - 500 INTERNAL_SERVER_ERROR: Database or server error
    
    Security Considerations:
    - Generic error message: "Incorrect email or password" (no user enumeration)
    - Password verification: Constant-time comparison (timing attack prevention)
    - Failed attempts logging: Security auditing ke liye
    - HTTPS required: Production mein plain HTTP allow nahi
    
    Token Usage:
    - Token response milne ke baad
    - Authorization header mein include karte hain: "Authorization: Bearer {token}"
    - Token 24 hours valid hota hai (default expiration)
    - Token refresh endpoint use karte hain expiration par (future feature)
    
    Usage Pattern:
    1. Frontend login form fill karta hai
    2. POST request send karta hai email aur password ke saath
    3. Backend email/password verify karta hai
    4. JWT token generate aur return karta hai
    5. Token client store karta hai (localStorage, sessionStorage)
    6. Protected endpoints ke liye token use karte hain
    
    Example cURL:
    curl -X POST http://localhost:8000/api/v1/auth/login \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "admin@clinic.com",
        "password": "SecurePassword123!"
      }'
    
    Example with Authorization:
    curl -X GET http://localhost:8000/api/v1/patients \\
      -H "Authorization: Bearer eyJhbGc..."
    """
    
    logger.info(f"Login request received for email: {request.email}")
    
    try:
        # Service layer ko call karte hain authentication logic ke liye
        # Service password verification aur token generation handle karta hai
        token_response = await auth_service.login_user(db, request)
        
        # ResponseEnvelope mein wrap karte hain consistent format ke liye
        logger.info(f"User logged in successfully: {request.email}")
        return ResponseEnvelope(data=token_response)
        
    except Exception as e:
        # Exceptions service layer se propagate hote hain
        # FastAPI automatically error responses generate karta hai
        logger.error(f"Login failed: {str(e)}")
        raise

