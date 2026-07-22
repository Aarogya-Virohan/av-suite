from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.patients import router as patients_router

api_router = APIRouter()
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])

__all__ = ["api_router"]
