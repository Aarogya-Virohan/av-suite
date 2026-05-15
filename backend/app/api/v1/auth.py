from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.envelope import ResponseEnvelope
from app.services import auth_service

router = APIRouter()

@router.post("/register", response_model=ResponseEnvelope[TokenResponse], status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    token_response = await auth_service.register_user(db, request)
    return ResponseEnvelope(data=token_response)

@router.post("/login", response_model=ResponseEnvelope[TokenResponse])
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    token_response = await auth_service.login_user(db, request)
    return ResponseEnvelope(data=token_response)
