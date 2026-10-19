"""
Module: router.py
Purpose: API V1 endpoints ko consolidate aur organize karna.
"""

from fastapi import APIRouter
from app.api.v1 import (
    auth,
    exercises,
    patients,
    prescriptions,
    leads,
    appointments,
    billing,
    booking,
    documents,
    treatments,
    assessments,
    audit,
    recycle_bin,
    settings,
    analytics,
    users,
    marketplace,
    me,
    psychosocial,
    # memory,
)
import logging

logger = logging.getLogger(__name__)

api_router = APIRouter()

# --- Existing routers (unchanged) ---
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["Exercises"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
# Posture is mounted once in main.py at /posture (the include that was
# here served a duplicate /api/v1/posture/posture/* path; dev removed it).
api_router.include_router(
    prescriptions.router, prefix="/prescriptions", tags=["Prescriptions"]
)

# --- New CRM routers: paths start empty (""), so they need an explicit prefix ---
api_router.include_router(leads.router, prefix="/leads", tags=["Leads"])
api_router.include_router(
    appointments.router, prefix="/appointments", tags=["Appointments"]
)
api_router.include_router(treatments.router, prefix="/treatments", tags=["Treatments"])
api_router.include_router(
    assessments.router, prefix="/assessments", tags=["Assessments"]
)
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# --- New CRM routers: paths already include their own full resource path, NO extra prefix ---
api_router.include_router(billing.router, tags=["Billing"])
api_router.include_router(booking.router, tags=["Booking"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(audit.router, tags=["Audit"])
api_router.include_router(recycle_bin.router, tags=["Recycle Bin"])
api_router.include_router(settings.router, tags=["Settings"])
api_router.include_router(analytics.router, tags=["Analytics"])
api_router.include_router(
    marketplace.router, prefix="/marketplace", tags=["Marketplace"]
)
api_router.include_router(me.router, tags=["Platform Context"])
api_router.include_router(psychosocial.router, tags=["Psycho-Social Screening"])
# api_router.include_router(memory.router, prefix="/memory", tags=["Memory"])

logger.info("All API v1 routers registered (existing + CRM)")
