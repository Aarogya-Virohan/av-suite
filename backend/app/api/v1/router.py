"""
Module: router.py
Purpose: API V1 endpoints ko consolidate aur organize karna.
"""

from fastapi import APIRouter
from app.api.v1 import (
    auth,
    exercises,
    patients,
    posture,
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
)
import logging

logger = logging.getLogger(__name__)

api_router = APIRouter()

# --- Existing routers (unchanged) ---
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["Exercises"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(posture.router, prefix="/posture", tags=["Posture"])
api_router.include_router(prescriptions.router, prefix="/prescriptions", tags=["Prescriptions"])

# --- New CRM routers: paths start empty (""), so they need an explicit prefix ---
api_router.include_router(leads.router, prefix="/leads", tags=["Leads"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(treatments.router, prefix="/treatments", tags=["Treatments"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])

# --- New CRM routers: paths already include their own full resource path, NO extra prefix ---
api_router.include_router(billing.router, tags=["Billing"])
api_router.include_router(booking.router, tags=["Booking"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(audit.router, tags=["Audit"])
api_router.include_router(recycle_bin.router, tags=["Recycle Bin"])
api_router.include_router(settings.router, tags=["Settings"])
api_router.include_router(analytics.router, tags=["Analytics"])

logger.info("All API v1 routers registered (existing + CRM)")
