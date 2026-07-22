from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.appointments import router as appointments_router
from app.api.v1.patients import router as patients_router

api_router = APIRouter()
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(appointments_router, prefix="/appointments", tags=["appointments"])

__all__ = ["api_router"]

