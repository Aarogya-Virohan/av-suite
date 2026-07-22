from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session, get_current_clinic
from app.enums.billing import InvoiceStatus
from app.enums.package import PackageStatus
from app.models.clinic import Clinic
from app.repositories.appointment import AppointmentRepository
from app.repositories.billing import (
    InvoiceItemRepository,
    InvoiceRepository,
    PackageRepository,
    PatientPackageRepository,
    PaymentRepository,
)
from app.repositories.patient import PatientRepository
from app.schemas.billing import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    PackageCreate,
    PackageListResponse,
    PackageResponse,
    PackageUpdate,
    PatientPackageCreate,
    PatientPackageListResponse,
    PatientPackageResponse,
    PatientPackageUpdate,
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
)
from app.services.billing import BillingNotFoundError, BillingService, BillingValidationError

router = APIRouter()


async def get_billing_service(
    session: AsyncSession = Depends(get_async_session),
) -> BillingService:
    """Inject BillingService with session-bound repositories."""

    return BillingService(
        package_repository=PackageRepository(session),
        patient_package_repository=PatientPackageRepository(session),
        invoice_repository=InvoiceRepository(session),
        invoice_item_repository=InvoiceItemRepository(session),
        payment_repository=PaymentRepository(session),
        patient_repository=PatientRepository(session),
        appointment_repository=AppointmentRepository(session),
    )


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]
CurrentClinicDep = Annotated[Clinic, Depends(get_current_clinic)]


# --- Package Catalog Endpoints ---

@router.post("/packages", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(
    payload: PackageCreate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PackageResponse:
    """Create a new package in the clinic catalogue."""

    try:
        package = await service.create_package(clinic.id, payload)
        return PackageResponse.model_validate(package)
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/packages", response_model=PackageListResponse)
async def list_packages(
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
    status_filter: Annotated[PackageStatus | None, Query(alias="status")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PackageListResponse:
    """List package catalogue items for the authenticated clinic."""

    packages = await service.list_packages(
        clinic.id, status=status_filter, offset=offset, limit=limit
    )
    items = [PackageResponse.model_validate(p) for p in packages]
    return PackageListResponse(items=items, total=len(items), offset=offset, limit=limit)


@router.get("/packages/{id}", response_model=PackageResponse)
async def get_package(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PackageResponse:
    """Retrieve a single package catalogue item by ID."""

    try:
        package = await service.get_package(clinic.id, id)
        return PackageResponse.model_validate(package)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/packages/{id}", response_model=PackageResponse)
async def update_package(
    id: UUID,
    payload: PackageUpdate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PackageResponse:
    """Update a package catalogue item for the authenticated clinic."""

    try:
        package = await service.update_package(clinic.id, id, payload)
        return PackageResponse.model_validate(package)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/packages/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> None:
    """Delete a package catalogue item for the authenticated clinic."""

    try:
        await service.delete_package(clinic.id, id)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# --- Patient Package Endpoints ---

@router.post("/patients/{patient_id}/packages", response_model=PatientPackageResponse, status_code=status.HTTP_201_CREATED)
async def sell_patient_package(
    patient_id: UUID,
    payload: PatientPackageCreate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PatientPackageResponse:
    """Sell or assign a treatment package to a patient."""

    if payload.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id in path does not match payload patient_id.",
        )

    try:
        patient_package = await service.sell_package(clinic.id, payload)
        return PatientPackageResponse.model_validate(patient_package)
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/patients/{patient_id}/packages", response_model=PatientPackageListResponse)
async def list_patient_packages_by_patient(
    patient_id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
    package_id: Annotated[UUID | None, Query(alias="package")] = None,
    status_filter: Annotated[PackageStatus | None, Query(alias="status")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PatientPackageListResponse:
    """List treatment packages purchased by a specific patient."""

    packages = await service.list_patient_packages(
        clinic.id, patient_id=patient_id, package_id=package_id, status=status_filter, offset=offset, limit=limit
    )
    items = [PatientPackageResponse.model_validate(p) for p in packages]
    return PatientPackageListResponse(items=items, total=len(items), offset=offset, limit=limit)


@router.get("/patient-packages/{id}", response_model=PatientPackageResponse)
async def get_patient_package(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PatientPackageResponse:
    """Retrieve a single patient package by ID."""

    try:
        package = await service.get_patient_package(clinic.id, id)
        return PatientPackageResponse.model_validate(package)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/patient-packages/{id}", response_model=PatientPackageResponse)
async def update_patient_package(
    id: UUID,
    payload: PatientPackageUpdate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PatientPackageResponse:
    """Update a patient package record."""

    try:
        package = await service.update_patient_package(clinic.id, id, payload)
        return PatientPackageResponse.model_validate(package)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/patient-packages/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_package(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> None:
    """Delete a patient package record."""

    try:
        await service.delete_patient_package(clinic.id, id)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# --- Invoice Endpoints ---

@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> InvoiceResponse:
    """Create a new invoice with line items for the clinic."""

    try:
        invoice = await service.create_invoice(clinic.id, payload)
        return InvoiceResponse.model_validate(invoice)
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/invoices/outstanding-balance")
async def get_outstanding_balance(
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
    patient_id: Annotated[UUID | None, Query(alias="patient_id")] = None,
) -> dict[str, str]:
    """Retrieve total outstanding unpaid invoice balance."""

    balance = await service.get_outstanding_balance(clinic.id, patient_id=patient_id)
    return {"outstanding_balance": str(balance)}


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
    patient_id: Annotated[UUID | None, Query(alias="patient_id")] = None,
    status_filter: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    start_date: Annotated[date | None, Query(alias="start_date")] = None,
    end_date: Annotated[date | None, Query(alias="end_date")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> InvoiceListResponse:
    """List invoices for the authenticated clinic with optional filtering."""

    invoices = await service.list_invoices(
        clinic.id,
        patient_id=patient_id,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )
    items = [InvoiceResponse.model_validate(inv) for inv in invoices]
    return InvoiceListResponse(items=items, total=len(items), offset=offset, limit=limit)


@router.get("/invoices/{id}", response_model=InvoiceResponse)
async def get_invoice(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> InvoiceResponse:
    """Retrieve an invoice by ID."""

    try:
        invoice = await service.get_invoice(clinic.id, id)
        return InvoiceResponse.model_validate(invoice)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/invoices/{id}", response_model=InvoiceResponse)
async def update_invoice(
    id: UUID,
    payload: InvoiceUpdate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> InvoiceResponse:
    """Update an existing invoice for the clinic."""

    try:
        invoice = await service.update_invoice(clinic.id, id, payload)
        return InvoiceResponse.model_validate(invoice)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/invoices/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> None:
    """Delete or soft-cancel an invoice."""

    try:
        await service.delete_invoice(clinic.id, id)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/invoices/{id}/pdf", status_code=status.HTTP_200_OK)
async def generate_invoice_pdf_endpoint(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> dict[str, str]:
    """Trigger PDF generation for an invoice."""

    try:
        _ = await service.generate_invoice_pdf(clinic.id, id)
        return {"invoice_id": str(id), "status": "generated", "download_url": f"/api/v1/billing/invoices/{id}/pdf/download"}
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/invoices/{id}/pdf/download")
async def download_invoice_pdf_endpoint(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> Response:
    """Download PDF for an invoice (authenticated, clinic-scoped)."""

    try:
        pdf_bytes = await service.generate_invoice_pdf(clinic.id, id)
        headers = {"Content-Disposition": f'attachment; filename="invoice_{id}.pdf"'}
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# --- Payment Endpoints ---

@router.post("/invoices/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment_for_invoice(
    invoice_id: UUID,
    payload: PaymentCreate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PaymentResponse:
    """Record a payment against a specific invoice."""

    if payload.invoice_id != invoice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invoice_id in path does not match payload invoice_id.",
        )

    try:
        payment = await service.record_payment(clinic.id, payload)
        return PaymentResponse.model_validate(payment)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    payload: PaymentCreate,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PaymentResponse:
    """Record a payment against an invoice."""

    try:
        payment = await service.record_payment(clinic.id, payload)
        return PaymentResponse.model_validate(payment)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BillingValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/payments", response_model=PaymentListResponse)
async def list_payments(
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
    invoice_id: Annotated[UUID | None, Query(alias="invoice_id")] = None,
    patient_id: Annotated[UUID | None, Query(alias="patient_id")] = None,
    start_date: Annotated[date | None, Query(alias="start_date")] = None,
    end_date: Annotated[date | None, Query(alias="end_date")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PaymentListResponse:
    """List payment transactions for the clinic."""

    payments = await service.list_payments(
        clinic.id,
        invoice_id=invoice_id,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )
    items = [PaymentResponse.model_validate(p) for p in payments]
    return PaymentListResponse(items=items, total=len(items), offset=offset, limit=limit)


@router.get("/payments/{id}", response_model=PaymentResponse)
async def get_payment(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> PaymentResponse:
    """Retrieve a single payment record by ID."""

    try:
        payment = await service.get_payment(clinic.id, id)
        return PaymentResponse.model_validate(payment)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/payments/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    id: UUID,
    clinic: CurrentClinicDep,
    service: BillingServiceDep,
) -> None:
    """Delete a payment record."""

    try:
        await service.delete_payment(clinic.id, id)
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
