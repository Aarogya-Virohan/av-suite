from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.clinic import Clinic
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import get_password_hash, verify_password, create_access_token

async def register_user(db: AsyncSession, request: RegisterRequest) -> TokenResponse:
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create new clinic
    new_clinic = Clinic(name=request.clinic_name)
    db.add(new_clinic)
    await db.flush()  # To get new_clinic.id

    # Create admin user
    new_user = User(
        clinic_id=new_clinic.id,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=UserRole.admin
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate token
    access_token = create_access_token(
        subject=new_user.id,
        clinic_id=new_clinic.id,
        role=new_user.role.value
    )
    
    return TokenResponse(access_token=access_token)

async def login_user(db: AsyncSession, request: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(
        subject=user.id,
        clinic_id=user.clinic_id,
        role=user.role.value
    )
    
    return TokenResponse(access_token=access_token)
