import logging
import uuid
import os
import asyncio
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prescription import Prescription
from app.schemas.prescription import PrescriptionCreate, PrescriptionPatch
from app.repositories.prescription import PrescriptionRepository
from app.utils.whatsapp import build_whatsapp_link
from app.services.prescription_pdf import (
    RxDoc,
    RxItem,
    ist_date,
    pdf_filename,
    render_prescription_pdf,
)

logger = logging.getLogger(__name__)


async def create_prescription(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    physio_id: uuid.UUID,
    prescription_in: PrescriptionCreate,
) -> Prescription:
    """
    Creates a new exercise prescription for a patient within a clinic context.
    """
    try:
        logger.info(
            f"Creating prescription for patient: {prescription_in.patient_id} in clinic: {clinic_id}"
        )

        repo = PrescriptionRepository(db)
        db_prescription = await repo.create_prescription(
            clinic_id, physio_id, prescription_in
        )

        # Return prescription with relationships loaded
        return await get_prescription_by_id(db, clinic_id, db_prescription.id)
    except Exception as e:
        logger.error(f"Error creating prescription: {str(e)}")
        await db.rollback()
        raise


async def get_prescription_by_id(
    db: AsyncSession, clinic_id: uuid.UUID, prescription_id: uuid.UUID
) -> Optional[Prescription]:
    """
    Retrieves a specific prescription by ID, ensuring clinic scoping.
    """
    try:
        logger.info(f"Fetching prescription: {prescription_id} in clinic: {clinic_id}")
        repo = PrescriptionRepository(db)
        return await repo.get_prescription_by_id(clinic_id, prescription_id)
    except Exception as e:
        logger.error(f"Error fetching prescription {prescription_id}: {str(e)}")
        raise


async def get_prescriptions(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    physio_id: Optional[uuid.UUID] = None,
    patient_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> Tuple[List[Prescription], int]:
    """
    Lists paginated prescriptions for a clinic, optionally filtered by patient.
    """
    try:
        logger.info(f"Listing prescriptions for clinic: {clinic_id}, page: {page}")

        repo = PrescriptionRepository(db)
        return await repo.get_prescriptions(
            clinic_id, physio_id, patient_id, search, page, page_size
        )
    except Exception as e:
        logger.error(f"Error listing prescriptions: {str(e)}")
        raise


async def delete_prescription(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    prescription_id: uuid.UUID,
) -> bool:
    """Delete a prescription scoped to clinic; returns False when not found."""

    try:
        repo = PrescriptionRepository(db)
        prescription = await repo.get_prescription_by_id(clinic_id, prescription_id)
        if not prescription:
            return False

        await repo.delete_prescription(prescription)
        return True
    except Exception as e:
        logger.error(f"Error deleting prescription {prescription_id}: {str(e)}")
        await db.rollback()
        raise


async def patch_prescription(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    prescription_id: uuid.UUID,
    patch: PrescriptionPatch,
) -> Optional[Prescription]:
    """
    Updates prescription notes, status, and optionally replaces prescription items.
    """
    try:
        logger.info(f"Patching prescription: {prescription_id} in clinic: {clinic_id}")
        rx = await get_prescription_by_id(db, clinic_id, prescription_id)
        if not rx:
            return None

        if patch.physio_notes is not None:
            rx.physio_notes = patch.physio_notes
        if patch.status is not None:
            rx.status = patch.status

        if patch.items is not None:
            repo = PrescriptionRepository(db)
            await repo.update_prescription_items(prescription_id, patch)

        await db.commit()
        # Fetch again to ensure all relationships are fresh and loaded
        return await get_prescription_by_id(db, clinic_id, prescription_id)
    except Exception as e:
        logger.error(f"Error updating prescription {prescription_id}: {str(e)}")
        await db.rollback()
        raise


PDF_LOCAL_DIR = os.path.join("static", "prescriptions")
PDF_STORAGE_PREFIX = "prescriptions"


def _storage_key(rx: Prescription) -> str:
    return f"{PDF_STORAGE_PREFIX}/{rx.clinic_id}/{rx.id}.pdf"


def _storage_client():
    """The shared Supabase client, or None when storage is not configured
    (local runs, tests). Imported lazily, as in api/v1/documents.py."""
    try:
        from app.core.storage import storage_client

        return storage_client
    except Exception as exc:  # bad or missing Supabase settings
        logger.warning("Document storage not available: %s", type(exc).__name__)
        return None


def _rx_doc(rx: Prescription) -> RxDoc:
    patient = rx.patient
    physio = rx.physio
    physio_name = (
        f"{physio.first_name or ''} {physio.last_name or ''}".strip() or physio.email
        if physio
        else ""
    )
    items = []
    for item in rx.items:
        ex = item.exercise
        items.append(
            RxItem(
                title=(ex.title if ex and ex.title else "Exercise"),
                body_part=(ex.body_part if ex and ex.body_part else "General"),
                instructions=(ex.description if ex and ex.description else ""),
                sets=item.sets,
                reps=item.reps,
                hold=item.hold,
                frequency=item.frequency,
                note=item.note,
                image_url=(ex.video_url if ex and ex.video_url else None),
            )
        )
    return RxDoc(
        rx_id=str(rx.id),
        clinic_name=(rx.clinic.name if rx.clinic else ""),
        clinic_logo=(rx.clinic.branding_logo_url if rx.clinic else None),
        physio_name=physio_name,
        patient_name=(
            f"{patient.first_name} {patient.last_name}".strip() if patient else "Patient"
        ),
        patient_phone=(patient.phone if patient else None),
        patient_dob=(patient.date_of_birth if patient else None),
        prescribed_on=rx.created_at,
        physio_notes=rx.physio_notes,
        items=items,
    )


def prescription_pdf_filename(rx: Prescription) -> str:
    """Name the browser saves the file under, e.g. Rx_PriyaSharma_20Oct2026.pdf."""
    name = (
        f"{rx.patient.first_name} {rx.patient.last_name}" if rx.patient else "Patient"
    )
    return pdf_filename(name, ist_date(rx.created_at))


async def generate_prescription_pdf(
    db: AsyncSession, clinic_id: uuid.UUID, prescription_id: uuid.UUID
) -> str:
    """
    Render the prescription PDF and store it. Returns the authenticated
    download path.

    Stored in the Supabase bucket under prescriptions/<clinic_id>/<rx_id>.pdf
    so it survives redeploys (Railway's disk is wiped on every deploy). When
    storage is unavailable the file goes to the local disk instead, as before,
    and the download endpoint regenerates it if it is gone later.
    """
    rx = await get_prescription_by_id(db, clinic_id, prescription_id)
    if not rx:
        raise ValueError("Prescription not found")

    pdf_bytes = await render_prescription_pdf(_rx_doc(rx))
    pdf_key = await _store_pdf(rx, pdf_bytes)

    repo = PrescriptionRepository(db)
    await repo.update_pdf_key(rx, pdf_key)
    logger.info(
        "Prescription PDF generated: %s (%d bytes, key %s)", rx.id, len(pdf_bytes), pdf_key
    )
    return f"/api/v1/prescriptions/{rx.id}/pdf/download"


async def _store_pdf(rx: Prescription, pdf_bytes: bytes) -> str:
    client = _storage_client()
    if client is not None:
        from app.core.storage import StorageUnavailableError

        key = _storage_key(rx)
        try:
            await asyncio.to_thread(client.upload_file, key, pdf_bytes, "application/pdf")
            return key
        except StorageUnavailableError:
            logger.warning("Prescription PDF upload failed, keeping it on local disk")

    os.makedirs(PDF_LOCAL_DIR, exist_ok=True)
    filename = f"prescription_{rx.id}.pdf"
    path = os.path.join(PDF_LOCAL_DIR, filename)
    await asyncio.to_thread(_write_file, path, pdf_bytes)
    return filename


def _write_file(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)


def _read_file(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


async def load_prescription_pdf(
    db: AsyncSession, clinic_id: uuid.UUID, rx: Prescription
) -> bytes:
    """
    Bytes of the stored PDF. A key with a "/" lives in the bucket, a bare
    filename on the local disk (older prescriptions). If the file is gone
    (redeploy, storage outage) it is generated again rather than failing.
    """
    key = rx.pdf_key
    if key and "/" in key:
        client = _storage_client()
        if client is not None:
            from app.core.storage import StorageUnavailableError

            try:
                return await asyncio.to_thread(client.download_file, key)
            except StorageUnavailableError:
                logger.warning("Prescription PDF download from storage failed, regenerating")
    elif key:
        path = os.path.join(PDF_LOCAL_DIR, os.path.basename(key))
        if os.path.exists(path):
            return await asyncio.to_thread(_read_file, path)

    await generate_prescription_pdf(db, clinic_id, rx.id)
    fresh = await get_prescription_by_id(db, clinic_id, rx.id)
    if fresh and fresh.pdf_key and "/" not in fresh.pdf_key:
        return await asyncio.to_thread(
            _read_file, os.path.join(PDF_LOCAL_DIR, fresh.pdf_key)
        )
    if fresh and fresh.pdf_key:
        client = _storage_client()
        if client is not None:
            return await asyncio.to_thread(client.download_file, fresh.pdf_key)
    raise ValueError("PDF could not be generated")


def _build_prescription_message(patient_name: str, clinic_name: str) -> str:
    """
    WhatsApp text that goes with the prescription. It carries no link: the
    download path needs a login, and a public link would put health data on
    an open URL. The physiotherapist attaches the PDF in WhatsApp
    (decided by Onkar, 20 October 2026).
    """
    return (
        f"Hello {patient_name},\n\n"
        f"Your home exercise programme from {clinic_name} is attached as a PDF. "
        "Please follow the sets and reps as prescribed and contact us if anything hurts."
    )


async def generate_prescription_pdf_response(
    db: AsyncSession, clinic_id: uuid.UUID, prescription_id: uuid.UUID
) -> dict[str, object]:
    """Generate the PDF and return its download path, file name and WhatsApp link."""

    pdf_url = await generate_prescription_pdf(db, clinic_id, prescription_id)
    rx = await get_prescription_by_id(db, clinic_id, prescription_id)
    if not rx or not rx.patient:
        raise ValueError("Prescription not found")

    patient_name = (
        f"{rx.patient.first_name} {rx.patient.last_name}".strip() or "Patient"
    )
    clinic_name = rx.clinic.name if rx.clinic else "your clinic"
    whatsapp_link = build_whatsapp_link(
        rx.patient.phone or "", _build_prescription_message(patient_name, clinic_name)
    )

    return {
        "pdf_url": pdf_url,
        "whatsapp_link": whatsapp_link,
        "filename": prescription_pdf_filename(rx),
    }
