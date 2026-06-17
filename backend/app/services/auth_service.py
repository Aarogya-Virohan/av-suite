"""
Module: auth_service.py
Purpose: User authentication business logic operations
Yeh module user registration, login, aur token generation logic handle karta hai.
Authentication system ke core operations yahan centralized hain.

Key Components:
- register_user: New user aur clinic create karta hai
- login_user: Email/password verification aur token generation
- TokenResponse: Authentication ka successful response

Security Considerations:
- Password hashing: Plain passwords kabhi stored nahi hote
- JWT tokens: Stateless authentication taaki scalability ho
- Error messages: Generic error messages security leak prevent karte hain
- Clinic isolation: Multi-tenant separation ensure karta hai
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.clinic import Clinic
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import get_password_hash, verify_password, create_access_token
import logging
import uuid

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, request: RegisterRequest) -> TokenResponse:
    """
    Function ka purpose: New user aur clinic ko register karna
    Yeh function signup flow handle karta hai - new clinic create karta hai,
    admin user add karta hai, aur authentication token return karta hai.
    
    Input:
    - db (AsyncSession): Database session connection
    - request (RegisterRequest): User registration details
      - email: User email (unique identifier)
      - password: Plain password (hash mein convert hoga)
      - clinic_name: Naye clinic ka name
    
    Output: TokenResponse
    - access_token: JWT token authentication ke liye
    
    Error:
    - HTTPException 409: Email already registered hai (duplicate email)
    - HTTPException 500: Database transaction failure
    
    Business Logic Flow:
    1. Email uniqueness check - duplicate registration prevent karte hain
    2. Clinic creation - naya clinic record create karte hain
    3. Admin user creation - clinic owner user banate hain
    4. Token generation - authentication token issue karte hain
    
    Security Notes:
    - Password immediately hash ho jata hai (plain text kabhi save nahi hota)
    - Clinic automatically create hota hai (admin user = clinic owner)
    - First user hamesha admin role se create hota hai
    - Token 24 hours validity se create hota hai (default)
    
    Transaction Handling:
    - flush() use karte hain clinic ID get karne ke liye
    - commit() transaction finalize karte hain
    - Agar koi error aaye to transaction automatically rollback hota hai
    
    Usage:
    request = RegisterRequest(
        email="user@hospital.com",
        password="SecurePassword123!",
        clinic_name="City Medical Clinic"
    )
    token_response = await register_user(db, request)
    return token_response
    """
    
    try:
        logger.info(f"Attempting registration for email: {request.email}")
        
        # Email uniqueness validation
        # Duplicate email check karte hain database mein
        # Yeh prevent karta hai multiple accounts same email se
        result = await db.execute(select(User).where(User.email == request.email))
        if result.scalars().first():
            logger.warning(f"Registration failed: Email already exists - {request.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create new clinic
        # Clinic naya user ke liye naya clinic create karta hai
        # Multi-tenant architecture: Har clinic isolated data rakhta hai
        new_clinic = Clinic(name=request.clinic_name)
        db.add(new_clinic)
        
        # flush() call karte hain clinic ID get karne ke liye
        # Flush: Database mein temporary add karta hai ID generation ke liye
        # Commit nahi karte, sirf ID generate karne ke liye
        await db.flush()
        logger.info(f"New clinic created with ID: {new_clinic.id}")

        # Create admin user
        # First user always admin role se create hota hai
        # User clinic owner = admin user
        # Password immediately hash ho jata hai security ke liye
        new_user = User(
            clinic_id=new_clinic.id,
            email=request.email,
            password_hash=get_password_hash(request.password),  # Hash karte hain, plain nahi store
            role=UserRole.admin,  # First user = admin
            first_name=request.first_name,
            last_name=request.last_name
        )
        db.add(new_user)
        
        # commit() transaction finalize karte hain
        # Database mein permanent add hota hai clinic aur user
        await db.commit()
        
        # refresh() user ko latest database values se load karte hain
        # ID aur other auto-generated fields ensure karte hain
        await db.refresh(new_user)
        logger.info(f"User registered successfully: {new_user.id}")

        # Generate JWT token
        # Token user authentication ke liye issue karte hain
        # Subject: User ID, Clinic ID, aur Role token mein include hote hain
        access_token = create_access_token(
            subject=new_user.id,
            clinic_id=new_clinic.id,
            role=new_user.role.value  # Enum value se string le lete hain
        )
        
        logger.info(f"Access token generated for new user: {new_user.id}")
        return TokenResponse(access_token=access_token)
        
    except HTTPException:
        # Already processed exceptions ko re-raise karte hain
        raise
    except Exception as e:
        # Unexpected errors ko log karte hain
        logger.error(f"Registration error: {str(e)}")
        await db.rollback()  # Transaction rollback karte hain
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


async def login_user(db: AsyncSession, request: LoginRequest) -> TokenResponse:
    """
    Function ka purpose: Existing user ko authenticate karna aur token issue karna
    Yeh function login flow handle karta hai - email/password verify karta hai,
    credentials match hone par JWT token return karta hai.
    
    Input:
    - db (AsyncSession): Database session connection
    - request (LoginRequest): Login credentials
      - email: User email address
      - password: Plain password (comparison ke liye)
    
    Output: TokenResponse
    - access_token: JWT token authentication ke liye
    
    Error:
    - HTTPException 401: Incorrect email or password (combined message)
    
    Authentication Flow:
    1. Email se user database mein search karte hain
    2. Password verification (bcrypt constant-time comparison)
    3. Token generation successful credentials par
    
    Security Notes:
    - Generic error message (email OR password) - specific info leak prevent karte hain
    - Password hashing: Plain password bytes convert karke compare karte hain
    - Constant-time comparison: Timing attacks prevent karte hain
    - Failed login attempt log hota hai security auditing ke liye
    
    Token Generation:
    - Subject: User ID (who is logging in)
    - Clinic ID: User's clinic association (multi-tenant)
    - Role: User's access level (authorization)
    
    Usage:
    request = LoginRequest(
        email="user@hospital.com",
        password="SecurePassword123!"
    )
    token_response = await login_user(db, request)
    return token_response
    """
    
    try:
        logger.info(f"Login attempt for email: {request.email}")
        
        # Email se user fetch karte hain
        # Database query execute karte hain email match par
        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalars().first()

        # Password verification aur user existence check
        # Dono checks combined error message se (no info leakage)
        # verify_password: Bcrypt constant-time comparison
        if not user or not verify_password(request.password, user.password_hash):
            logger.warning(f"Failed login attempt for email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"  # Generic message - no specificity
            )

        # Generate JWT token after successful authentication
        # Token user ke clinic aur role information include karta hai
        access_token = create_access_token(
            subject=user.id,
            clinic_id=user.clinic_id,
            role=user.role.value  # Enum value se string
        )
        
        logger.info(f"Successful login for user: {user.id}")
        return TokenResponse(access_token=access_token)
        
    except HTTPException:
        # Already processed exceptions ko re-raise karte hain
        raise
    except Exception as e:
        # Unexpected errors ko log karte hain
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

