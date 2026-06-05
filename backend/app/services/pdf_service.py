import os
import uuid
import logging
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import prescription_service

logger = logging.getLogger(__name__)

async def generate_prescription_pdf(db: AsyncSession, clinic_id: str, prescription_id: str) -> str:
    # Fetch prescription data
    prescription = await prescription_service.get_prescription_by_id(db, clinic_id, prescription_id)
    if not prescription:
        raise ValueError("Prescription not found")

    # Load Jinja2 template
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("prescription.html")

    # Render HTML
    html_out = template.render(
        clinic_name=prescription.clinic.name if prescription.clinic else "AV Suite Clinic",
        patient_name=f"{prescription.patient.first_name} {prescription.patient.last_name}",
        patient_id=str(prescription.patient.id),
        patient_age=prescription.patient.date_of_birth.strftime("%Y-%m-%d") if prescription.patient.date_of_birth else "N/A",
        patient_gender="Not Specified",
        exercises=prescription.items,
        generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # Setup static dir for serving PDFs
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "pdfs")
    os.makedirs(static_dir, exist_ok=True)
    
    pdf_filename = f"prescription_{prescription_id}.pdf"
    pdf_path = os.path.join(static_dir, pdf_filename)
    
    # Generate PDF using WeasyPrint
    HTML(string=html_out).write_pdf(pdf_path)
    logger.info(f"PDF generated successfully at {pdf_path}")
    
    # Generate URL (Assuming static files are served at /static)
    pdf_url = f"/static/pdfs/{pdf_filename}"
    
    # Update prescription with pdf_key
    prescription.pdf_key = pdf_url
    await db.commit()
    
    return pdf_url
