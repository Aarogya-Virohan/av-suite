from datetime import date
from uuid import uuid4

import pytest

from app.enums.appointment import AppointmentStatus
from app.enums.billing import InvoiceStatus
from app.enums.document import DocumentCategory
from app.enums.lead import LeadStage
from app.enums.package import PackageStatus
from app.repositories.appointment import AppointmentRepository
from app.repositories.billing import (
    InvoiceRepository,
    PackageRepository,
    PatientPackageRepository,
    PaymentRepository,
)
from app.repositories.document import PatientDocumentRepository
from app.repositories.lead import LeadRepository
from app.repositories.treatment import SoapAssessmentRepository


class ScalarSession:
    def __init__(self, result: int = 25):
        self.result = result
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return self.result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("repository_type", "method", "filters", "expected_columns"),
    [
        (LeadRepository, "count_leads", {"stage": LeadStage.NEW, "source": "website", "search": "alex"}, ["clinic_id", "stage", "source", "name", "phone", "deleted_at"]),
        (AppointmentRepository, "count_appointments", {"scheduled_date": date(2026, 10, 1), "status": AppointmentStatus.SCHEDULED}, ["clinic_id", "scheduled_at", "status"]),
        (SoapAssessmentRepository, "count_assessments", {"specialty": "physio", "is_reassessment": True}, ["clinic_id", "specialty", "is_reassessment"]),
        (PackageRepository, "count_packages", {"status": PackageStatus.ACTIVE}, ["clinic_id", "status"]),
        (PatientPackageRepository, "count_packages", {"patient_id": uuid4(), "package_id": uuid4(), "status": PackageStatus.ACTIVE}, ["clinic_id", "patient_id", "package_id", "status"]),
        (InvoiceRepository, "count_invoices", {"patient_id": uuid4(), "status": InvoiceStatus.PAID, "start_date": date(2026, 10, 1), "end_date": date(2026, 10, 31)}, ["clinic_id", "patient_id", "status", "issue_date"]),
        (PaymentRepository, "count_payments", {"invoice_id": uuid4(), "patient_id": uuid4(), "start_date": date(2026, 10, 1), "end_date": date(2026, 10, 31)}, ["clinic_id", "invoice_id", "patient_id", "payment_date"]),
        (PatientDocumentRepository, "count_documents", {"patient_id": uuid4(), "treatment_id": uuid4(), "category": DocumentCategory.MEDICAL_REPORT}, ["clinic_id", "patient_id", "treatment_id", "category"]),
    ],
)
async def test_filtered_count_queries_are_unpaginated(
    repository_type, method, filters, expected_columns
):
    session = ScalarSession(result=25)
    repository = repository_type(session)

    total = await getattr(repository, method)(clinic_id=uuid4(), **filters)

    assert total == 25  # Greater than the API's usual page size of 10 or 20.
    sql = str(session.statement).lower()
    assert " limit " not in sql and " offset " not in sql
    for column in expected_columns:
        assert column in sql
