from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.appointments import router as appointments_router
from app.api.v1.assessments import router as assessments_router
from app.api.v1.patients import router as patients_router
from app.api.v1.treatments import router as treatments_router

api_router = APIRouter()
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(appointments_router, prefix="/appointments", tags=["appointments"])
api_router.include_router(treatments_router, prefix="/treatments", tags=["treatments"])
api_router.include_router(assessments_router, prefix="/assessments", tags=["assessments"])

__all__ = ["api_router"]


