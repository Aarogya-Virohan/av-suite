from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from app.core.database import get_db
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate, PrescriptionRead
from app.schemas.envelope import ResponseEnvelope, MetaPagination
from app.schemas.common import PaginationParams
from app.dependencies.pagination import get_pagination_params
from app.services import prescription_service, pdf_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "",
    response_model=ResponseEnvelope[PrescriptionRead],
    status_code=status.HTTP_201_CREATED,
    tags=["Prescriptions"]
)
async def create_prescription(
    request: Request,
    data: PrescriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        clinic_id = request.state.clinic_id
        # In a real app we would get physio_id from user context, but let's assume it's stored in state
        physio_id = getattr(request.state, "user_id", None)
        
        if not physio_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in context"
            )
            
        role = getattr(request.state, "role", None)
        if role not in ["physio", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only physios and admins can create prescriptions"
            )

        prescription = await prescription_service.create_prescription(
            db, clinic_id, physio_id, data
        )
        return ResponseEnvelope(data=prescription)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prescription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating prescription"
        )


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[PrescriptionRead],
    tags=["Prescriptions"]
)
async def get_prescription(
    request: Request,
    id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        clinic_id = request.state.clinic_id
        role = getattr(request.state, "role", None)
        if role not in ["physio", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view prescriptions"
            )

        prescription = await prescription_service.get_prescription_by_id(db, clinic_id, id)
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found"
            )
            
        return ResponseEnvelope(data=prescription)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prescription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting prescription"
        )


@router.get(
    "",
    response_model=ResponseEnvelope[List[PrescriptionRead]],
    tags=["Prescriptions"]
)
async def list_prescriptions(
    request: Request,
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    try:
        clinic_id = request.state.clinic_id
        prescriptions, total = await prescription_service.get_prescriptions(
            db, clinic_id, pagination, patient_id
        )
        
        meta = MetaPagination(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        return ResponseEnvelope(data=prescriptions, meta=meta)
    except Exception as e:
        logger.error(f"Error listing prescriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing prescriptions"
        )


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[PrescriptionRead],
    tags=["Prescriptions"]
)
async def patch_prescription(
    request: Request,
    id: str,
    data: PrescriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        clinic_id = request.state.clinic_id
        role = getattr(request.state, "role", None)
        if role not in ["physio", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update prescriptions"
            )

        prescription = await prescription_service.update_prescription(
            db, clinic_id, id, data
        )
        
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found"
            )
            
        return ResponseEnvelope(data=prescription)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prescription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating prescription"
        )


@router.post(
    "/{id}/pdf",
    response_model=ResponseEnvelope[dict],
    status_code=status.HTTP_201_CREATED,
    tags=["Prescriptions"]
)
async def generate_prescription_pdf(
    request: Request,
    id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        clinic_id = request.state.clinic_id
        role = getattr(request.state, "role", None)
        if role not in ["physio", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to generate PDF"
            )

        pdf_url = await pdf_service.generate_prescription_pdf(db, clinic_id, id)
        
        return ResponseEnvelope(data={"pdf_url": pdf_url})
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating PDF"
        )
