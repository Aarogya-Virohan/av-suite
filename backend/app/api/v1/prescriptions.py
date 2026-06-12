from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import logging

from app.core.database import get_db
from app.schemas.prescription import PrescriptionCreate, PrescriptionRead, PrescriptionPatch
from app.schemas.envelope import ResponseEnvelope, MetaPagination
from app.schemas.common import PaginationParams
from app.dependencies.pagination import get_pagination_params
from app.services import prescription_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "",
    response_model=ResponseEnvelope[PrescriptionRead],
    status_code=201,
    tags=["Prescriptions"]
)
async def create_prescription(
    request: Request,
    prescription_in: PrescriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new exercise prescription for a patient.
    Strictly scoped to the clinician's clinic_id and logged-in user_id.
    """
    logger.info(f"Received create prescription request for patient {prescription_in.patient_id}")
    try:
        clinic_id = request.state.clinic_id
        physio_id = request.state.user_id
        
        # Verify role is admin or physio (though gate handles basic auth)
        role = request.state.role
        if role not in ["admin", "physio"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only therapists or admins can prescribe exercises"
            )
            
        prescription = await prescription_service.create_prescription(
            db, uuid.UUID(clinic_id), uuid.UUID(physio_id), prescription_in
        )
        return ResponseEnvelope(data=prescription)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prescription: {str(e)}")
        raise

@router.get(
    "",
    response_model=ResponseEnvelope[List[PrescriptionRead]],
    tags=["Prescriptions"]
)
async def list_prescriptions(
    request: Request,
    patient_id: Optional[uuid.UUID] = Query(None, description="Filter by patient ID"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    """
    List prescriptions in a clinic, optionally filtered by patient.
    """
    logger.info(f"Listing prescriptions. Filter by patient: {patient_id}")
    try:
        clinic_id = request.state.clinic_id
        prescriptions, total = await prescription_service.get_prescriptions(
            db, uuid.UUID(clinic_id), patient_id, pagination.page, pagination.page_size
        )
        meta = MetaPagination(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        return ResponseEnvelope(data=prescriptions, meta=meta)
    except Exception as e:
        logger.error(f"Error listing prescriptions: {str(e)}")
        raise

@router.get(
    "/{id}",
    response_model=ResponseEnvelope[PrescriptionRead],
    tags=["Prescriptions"]
)
async def get_prescription(
    request: Request,
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches a specific prescription by ID.
    """
    logger.info(f"Fetching prescription: {id}")
    try:
        clinic_id = request.state.clinic_id
        prescription = await prescription_service.get_prescription_by_id(
            db, uuid.UUID(clinic_id), id
        )
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found or not in user's clinic"
            )
        return ResponseEnvelope(data=prescription)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prescription {id}: {str(e)}")
        raise

@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[PrescriptionRead],
    tags=["Prescriptions"]
)
async def update_prescription(
    request: Request,
    id: uuid.UUID,
    patch_in: PrescriptionPatch,
    db: AsyncSession = Depends(get_db)
):
    """
    Patches/updates prescription details.
    """
    logger.info(f"Patching prescription: {id}")
    try:
        clinic_id = request.state.clinic_id
        prescription = await prescription_service.patch_prescription(
            db, uuid.UUID(clinic_id), id, patch_in
        )
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found or not in user's clinic"
            )
        return ResponseEnvelope(data=prescription)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prescription {id}: {str(e)}")
        raise

@router.post(
    "/{id}/pdf",
    response_model=ResponseEnvelope[dict],
    tags=["Prescriptions"]
)
async def generate_pdf(
    request: Request,
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a PDF for the prescription and returns the static file URL.
    """
    logger.info(f"Generating PDF for prescription: {id}")
    try:
        clinic_id = request.state.clinic_id
        pdf_url = await prescription_service.generate_prescription_pdf(
            db, uuid.UUID(clinic_id), id
        )
        return ResponseEnvelope(data={"pdf_url": pdf_url})
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating PDF for prescription {id}: {str(e)}")
        raise
