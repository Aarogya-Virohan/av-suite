import logging
import uuid
import os
import html
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prescription import Prescription
from app.schemas.prescription import PrescriptionCreate, PrescriptionPatch
from app.repositories.prescription import PrescriptionRepository
from app.utils.whatsapp import build_whatsapp_link
from weasyprint import HTML

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


async def generate_prescription_pdf(
    db: AsyncSession, clinic_id: uuid.UUID, prescription_id: uuid.UUID
) -> str:
    """
    Generates a professional PDF using WeasyPrint and saves it to static files.
    Returns the file path / static URL path.
    """
    try:
        rx = await get_prescription_by_id(db, clinic_id, prescription_id)
        if not rx:
            raise ValueError("Prescription not found")

        # Create output directory
        os.makedirs("static/prescriptions", exist_ok=True)
        pdf_filename = f"prescription_{rx.id}.pdf"
        pdf_path = os.path.join("static/prescriptions", pdf_filename)

        # Formulate HTML content
        # Inline SVG fallback (no network dependency — avoids relying on external
        # placeholder services that can be slow, down, or removed in production)
        FALLBACK_IMG_SRC = (
            "data:image/svg+xml;utf8,"
            "<svg xmlns='http://www.w3.org/2000/svg' width='150' height='150'>"
            "<rect width='150' height='150' fill='%23f1f5f9'/>"
            "<text x='50%25' y='50%25' font-family='Helvetica, Arial, sans-serif' "
            "font-size='12' fill='%2394a3b8' text-anchor='middle' dominant-baseline='middle'>"
            "No Image</text></svg>"
        )

        items_html = ""
        for index, item in enumerate(rx.items):
            ex = item.exercise
            img_src = ex.video_url if ex and ex.video_url else FALLBACK_IMG_SRC

            # Escape all user-supplied / DB text before interpolating into HTML,
            # since WeasyPrint renders raw HTML — unescaped text could break the
            # layout or inject markup (e.g. via a note field with "<" or ">").
            ex_title = html.escape(ex.title) if ex and ex.title else "Rehab Exercise"
            ex_body_part = (
                html.escape(ex.body_part) if ex and ex.body_part else "General"
            )
            ex_description = (
                html.escape(ex.description)
                if ex and ex.description
                else "Perform as advised by therapist."
            )
            item_note_escaped = html.escape(item.note) if item.note else None

            note_text = (
                f"<p class='note'><strong>Special Notes:</strong> {item_note_escaped}</p>"
                if item_note_escaped
                else ""
            )
            items_html += f"""
            <div class="exercise-card">
                <div class="exercise-header">
                    <span class="exercise-num">#{index + 1}</span>
                    <span class="exercise-title">{ex_title}</span>
                    <span class="exercise-part">{ex_body_part}</span>
                </div>
                <div class="exercise-body">
                    <div class="exercise-img-container">
                        <img src="{img_src}" class="exercise-img" alt="{ex_title}" />
                    </div>
                    <div class="exercise-details">
                        <div class="dosage-grid">
                            <div class="dosage-cell"><span class="label">Sets</span><span class="value">{item.sets}</span></div>
                            <div class="dosage-cell"><span class="label">Reps</span><span class="value">{item.reps}</span></div>
                            <div class="dosage-cell"><span class="label">Hold Time</span><span class="value">{item.hold}s</span></div>
                            <div class="dosage-cell"><span class="label">Frequency</span><span class="value">{item.frequency}</span></div>
                        </div>
                        <p class="desc"><strong>Instructions:</strong> {ex_description}</p>
                        {note_text}
                    </div>
                </div>
            </div>
            """

        date_str = (
            rx.created_at.strftime("%B %d, %Y")
            if rx.created_at
            else datetime.now().strftime("%B %d, %Y")
        )
        patient_name = (
            html.escape(f"{rx.patient.first_name} {rx.patient.last_name}")
            if rx.patient
            else "Patient"
        )
        patient_phone = (
            html.escape(rx.patient.phone) if rx.patient and rx.patient.phone else "N/A"
        )
        patient_dob = (
            rx.patient.date_of_birth.strftime("%B %d, %Y")
            if rx.patient and rx.patient.date_of_birth
            else "N/A"
        )
        clinic_name = (
            html.escape(rx.clinic.name) if rx.clinic else "Aarogya-Virohan Clinic"
        )
        physio_name = html.escape(
            f"{rx.physio.first_name} {rx.physio.last_name}".strip()
            if rx.physio and rx.physio.first_name
            else (rx.physio.email if rx.physio else "N/A")
        )
        physio_notes_escaped = html.escape(rx.physio_notes) if rx.physio_notes else None
        general_notes = (
            f"<div class='general-notes'><h3>Clinical Notes & Guidance</h3><p>{physio_notes_escaped}</p></div>"
            if physio_notes_escaped
            else ""
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Exercise Prescription - {patient_name}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 20mm;
                    @bottom-right {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-family: 'Outfit', sans-serif;
                        font-size: 8pt;
                        color: #64748b;
                    }}
                    @bottom-left {{
                        content: "{clinic_name} — Clinical Biometrics";
                        font-family: 'Outfit', sans-serif;
                        font-size: 8pt;
                        color: #64748b;
                    }}
                }}
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #0f172a;
                    margin: 0;
                    padding: 0;
                    line-height: 1.5;
                }}
                .header-container {{
                    border-bottom: 2px solid #ff7a00;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }}
                .clinic-title {{
                    font-size: 24pt;
                    font-weight: bold;
                    color: #ff7a00;
                    margin: 0 0 5px 0;
                }}
                .clinic-subtitle {{
                    font-size: 10pt;
                    color: #475569;
                    margin: 0;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .meta-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                }}
                .meta-table td {{
                    padding: 6px 10px;
                    vertical-align: top;
                    font-size: 10pt;
                }}
                .meta-table .label {{
                    font-weight: bold;
                    color: #475569;
                    width: 15%;
                    text-transform: uppercase;
                    font-size: 8pt;
                }}
                .meta-table .value {{
                    color: #0f172a;
                    width: 35%;
                }}
                .exercise-card {{
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    page-break-inside: avoid;
                    overflow: hidden;
                }}
                .exercise-header {{
                    background-color: #fff5eb;
                    border-bottom: 1px solid #ffe0c2;
                    padding: 10px 15px;
                    font-weight: bold;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .exercise-num {{
                    color: #ff7a00;
                    font-size: 11pt;
                }}
                .exercise-title {{
                    font-size: 12pt;
                    color: #0f172a;
                    margin-left: 10px;
                    flex-grow: 1;
                }}
                .exercise-part {{
                    font-size: 9pt;
                    background-color: #ff7a00;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 4px;
                    text-transform: uppercase;
                }}
                .exercise-body {{
                    display: table;
                    width: 100%;
                }}
                .exercise-img-container {{
                    display: table-cell;
                    width: 30%;
                    padding: 15px;
                    vertical-align: top;
                    text-align: center;
                }}
                .exercise-img {{
                    max-width: 100%;
                    max-height: 120px;
                    border-radius: 6px;
                }}
                .exercise-details {{
                    display: table-cell;
                    width: 70%;
                    padding: 15px;
                    vertical-align: top;
                }}
                .dosage-grid {{
                    display: table;
                    width: 100%;
                    margin-bottom: 10px;
                    background-color: #f8fafc;
                    border-radius: 6px;
                }}
                .dosage-cell {{
                    display: table-cell;
                    padding: 8px;
                    text-align: center;
                    border-right: 1px solid #e2e8f0;
                }}
                .dosage-cell:last-child {{
                    border-right: none;
                }}
                .dosage-cell .label {{
                    display: block;
                    font-size: 7pt;
                    color: #64748b;
                    text-transform: uppercase;
                    font-weight: bold;
                    margin-bottom: 3px;
                }}
                .dosage-cell .value {{
                    font-size: 11pt;
                    font-weight: bold;
                    color: #ff7a00;
                }}
                .desc {{
                    font-size: 9.5pt;
                    color: #334155;
                    margin: 8px 0 0 0;
                }}
                .note {{
                    font-size: 9pt;
                    color: #d97706;
                    margin: 8px 0 0 0;
                    background-color: #fef3c7;
                    padding: 6px 10px;
                    border-radius: 4px;
                }}
                .general-notes {{
                    background-color: #f8fafc;
                    border-left: 4px solid #ff7a00;
                    padding: 15px;
                    border-radius: 0 6px 6px 0;
                    margin-bottom: 30px;
                    page-break-inside: avoid;
                }}
                .general-notes h3 {{
                    margin: 0 0 8px 0;
                    font-size: 11pt;
                    color: #ff7a00;
                    text-transform: uppercase;
                }}
                .general-notes p {{
                    margin: 0;
                    font-size: 10pt;
                    color: #475569;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="header-container">
                <h1 class="clinic-title">{clinic_name}</h1>
                <p class="clinic-subtitle">Personalized Rehabilitation & Kinematic Recovery</p>
            </div>
            
            <table class="meta-table">
                <tr>
                    <td class="label">Patient Name</td>
                    <td class="value">{patient_name}</td>
                    <td class="label">Date of Birth</td>
                    <td class="value">{patient_dob}</td>
                </tr>
                <tr>
                    <td class="label">Contact Phone</td>
                    <td class="value">{patient_phone}</td>
                    <td class="label">Prescribed Date</td>
                    <td class="value">{date_str}</td>
                </tr>
                <tr>
                    <td class="label">Therapist</td>
                    <td class="value">{physio_name}</td>
                    <td class="label"></td>
                    <td class="value"></td>
                </tr>
            </table>

            {general_notes}

            <div style="margin-top: 10px;">
                {items_html}
            </div>
        </body>
        </html>
        """

        # Generate PDF using WeasyPrint
        HTML(string=html_content).write_pdf(pdf_path)

        # Save pdf key back to the database
        repo = PrescriptionRepository(db)
        await repo.update_pdf_key(rx, pdf_filename)

        logger.info(
            f"PDF successfully generated for prescription: {rx.id} at {pdf_path}"
        )
        return f"/api/v1/prescriptions/{rx.id}/pdf/download"
    except Exception as e:
        logger.error(
            f"Error generating PDF for prescription {prescription_id}: {str(e)}"
        )
        raise


def _build_prescription_message(patient_name: str, pdf_url: str) -> str:
    """Format the WhatsApp message that accompanies a prescription download."""

    return (
        f"Hello {patient_name},\n\n"
        "Your prescription is ready.\n\n"
        "Download:\n\n"
        f"{pdf_url}"
    )


async def generate_prescription_pdf_response(
    db: AsyncSession, clinic_id: uuid.UUID, prescription_id: uuid.UUID
) -> dict[str, object]:
    """Generate the prescription PDF and return the download URL plus WhatsApp deep link."""

    pdf_url = await generate_prescription_pdf(db, clinic_id, prescription_id)
    rx = await get_prescription_by_id(db, clinic_id, prescription_id)
    if not rx or not rx.patient:
        raise ValueError("Prescription not found")

    patient_name = (
        f"{rx.patient.first_name} {rx.patient.last_name}".strip() or "Patient"
    )
    whatsapp_link = build_whatsapp_link(
        rx.patient.phone or "", _build_prescription_message(patient_name, pdf_url)
    )

    return {"pdf_url": pdf_url, "whatsapp_link": whatsapp_link}
