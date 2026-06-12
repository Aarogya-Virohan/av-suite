import logging
import uuid
import os
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app.models.prescription import Prescription, PrescriptionItem
from app.models.exercise import Exercise
from app.models.patient import Patient
from app.models.user import User
from app.schemas.prescription import PrescriptionCreate, PrescriptionPatch
from weasyprint import HTML

logger = logging.getLogger(__name__)

async def create_prescription(
    db: AsyncSession, clinic_id: uuid.UUID, physio_id: uuid.UUID, prescription_in: PrescriptionCreate
) -> Prescription:
    """
    Creates a new exercise prescription for a patient within a clinic context.
    """
    try:
        logger.info(f"Creating prescription for patient: {prescription_in.patient_id} in clinic: {clinic_id}")
        
        db_prescription = Prescription(
            clinic_id=clinic_id,
            patient_id=prescription_in.patient_id,
            physio_id=physio_id,
            physio_notes=prescription_in.physio_notes,
            status=prescription_in.status
        )
        db.add(db_prescription)
        await db.flush()  # Generate prescription ID
        
        db_items = []
        for item in prescription_in.items:
            db_items.append(
                PrescriptionItem(
                    prescription_id=db_prescription.id,
                    exercise_id=item.exercise_id,
                    sets=item.sets,
                    reps=item.reps,
                    hold=item.hold,
                    frequency=item.frequency,
                    hold_angle=item.hold_angle,
                    note=item.note
                )
            )
        
        if db_items:
            db.add_all(db_items)
            
        await db.commit()
        await db.refresh(db_prescription)
        
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
        query = (
            select(Prescription)
            .where(Prescription.id == prescription_id, Prescription.clinic_id == clinic_id)
            .options(
                selectinload(Prescription.items).selectinload(PrescriptionItem.exercise),
                selectinload(Prescription.patient),
                selectinload(Prescription.physio)
            )
        )
        result = await db.execute(query)
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching prescription {prescription_id}: {str(e)}")
        raise

async def get_prescriptions(
    db: AsyncSession,
    clinic_id: uuid.UUID,
    patient_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 10
) -> Tuple[List[Prescription], int]:
    """
    Lists paginated prescriptions for a clinic, optionally filtered by patient.
    """
    try:
        logger.info(f"Listing prescriptions for clinic: {clinic_id}, page: {page}")
        
        query = select(Prescription).where(Prescription.clinic_id == clinic_id)
        if patient_id:
            query = query.where(Prescription.patient_id == patient_id)
            
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate and order by created_at desc
        query = (
            query.options(
                selectinload(Prescription.items).selectinload(PrescriptionItem.exercise),
                selectinload(Prescription.patient)
            )
            .order_by(Prescription.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        
        result = await db.execute(query)
        return list(result.scalars().all()), total
    except Exception as e:
        logger.error(f"Error listing prescriptions: {str(e)}")
        raise

async def patch_prescription(
    db: AsyncSession, clinic_id: uuid.UUID, prescription_id: uuid.UUID, patch: PrescriptionPatch
) -> Optional[Prescription]:
    """
    Updates prescription notes or status.
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
            
        await db.commit()
        await db.refresh(rx)
        return rx
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
        items_html = ""
        for index, item in enumerate(rx.items):
            ex = item.exercise
            img_src = ex.video_url if ex and ex.video_url else "https://via.placeholder.com/150"
            note_text = f"<p class='note'><strong>Special Notes:</strong> {item.note}</p>" if item.note else ""
            items_html += f"""
            <div class="exercise-card">
                <div class="exercise-header">
                    <span class="exercise-num">#{index + 1}</span>
                    <span class="exercise-title">{ex.title if ex else 'Rehab Exercise'}</span>
                    <span class="exercise-part">{ex.body_part if ex and ex.body_part else 'General'}</span>
                </div>
                <div class="exercise-body">
                    <div class="exercise-img-container">
                        <img src="{img_src}" class="exercise-img" alt="{ex.title if ex else 'Exercise'}" />
                    </div>
                    <div class="exercise-details">
                        <div class="dosage-grid">
                            <div class="dosage-cell"><span class="label">Sets</span><span class="value">{item.sets}</span></div>
                            <div class="dosage-cell"><span class="label">Reps</span><span class="value">{item.reps}</span></div>
                            <div class="dosage-cell"><span class="label">Hold Time</span><span class="value">{item.hold}s</span></div>
                            <div class="dosage-cell"><span class="label">Frequency</span><span class="value">{item.frequency}</span></div>
                        </div>
                        <p class="desc"><strong>Instructions:</strong> {ex.description if ex else 'Perform as advised by therapist.'}</p>
                        {note_text}
                    </div>
                </div>
            </div>
            """

        date_str = rx.created_at.strftime("%B %d, %Y") if rx.created_at else datetime.now().strftime("%B %d, %Y")
        patient_name = f"{rx.patient.first_name} {rx.patient.last_name}" if rx.patient else "Patient"
        patient_phone = rx.patient.phone if rx.patient and rx.patient.phone else "N/A"
        physio_email = rx.physio.email if rx.physio else "therapist@avsuite.com"
        clinic_name = rx.clinic.name if rx.clinic else "Aarogya-Virohan Clinic"
        general_notes = f"<div class='general-notes'><h3>Clinical Notes & Guidance</h3><p>{rx.physio_notes}</p></div>" if rx.physio_notes else ""

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
                    <td class="label">Prescribed Date</td>
                    <td class="value">{date_str}</td>
                </tr>
                <tr>
                    <td class="label">Contact Phone</td>
                    <td class="value">{patient_phone}</td>
                    <td class="label">Lead Therapist</td>
                    <td class="value">{physio_email}</td>
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
        rx.pdf_key = pdf_filename
        await db.commit()
        
        logger.info(f"PDF successfully generated for prescription: {rx.id} at {pdf_path}")
        return f"/static/prescriptions/{pdf_filename}"
    except Exception as e:
        logger.error(f"Error generating PDF for prescription {prescription_id}: {str(e)}")
        raise
