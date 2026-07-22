from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.assessments import router as assessments_router
from app.api.v1.audit import router as audit_router
from app.api.v1.billing import router as billing_router
from app.api.v1.booking import router as booking_router
from app.api.v1.documents import router as documents_router
from app.api.v1.leads import router as leads_router
from app.api.v1.patients import router as patients_router
from app.api.v1.recycle_bin import router as recycle_bin_router
from app.api.v1.treatments import router as treatments_router

api_router = APIRouter()
api_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_router.include_router(appointments_router, prefix="/appointments", tags=["appointments"])
api_router.include_router(treatments_router, prefix="/treatments", tags=["treatments"])
api_router.include_router(assessments_router, prefix="/assessments", tags=["assessments"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(billing_router, prefix="", tags=["billing"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(documents_router, prefix="", tags=["documents"])
api_router.include_router(leads_router, prefix="/leads", tags=["leads"])
api_router.include_router(booking_router, prefix="", tags=["booking"])
api_router.include_router(analytics_router, prefix="", tags=["analytics"])
api_router.include_router(recycle_bin_router, prefix="", tags=["recycle-bin"])
api_router.include_router(audit_router, prefix="", tags=["audit-logs"])

__all__ = ["api_router"]
