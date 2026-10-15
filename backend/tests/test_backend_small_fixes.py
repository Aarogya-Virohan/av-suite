from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from storage3.utils import StorageException

from app.core.storage import StorageUnavailableError, SupabaseStorageClient
from app.enums.shared import Specialty
from app.models.treatment import SoapAssessment
from app.schemas.treatment import SoapAssessmentCreate, SoapAssessmentResponse


def test_specialty_schema_and_model_use_canonical_values():
    canonical_values = {specialty.value for specialty in Specialty}
    assert set(SoapAssessment.__table__.c.specialty.type.enums) == canonical_values

    payload = {
        "patient_id": "30a7dc3d-b550-4a64-8e56-27f5c0c3d00a",
        "specialty": "physiotherapy",
    }
    assessment = SoapAssessmentCreate.model_validate(payload)
    assert assessment.specialty is Specialty.PHYSIOTHERAPY
    assert assessment.model_dump(mode="json")["specialty"] == "physiotherapy"

    specialty_column = SoapAssessment.__table__.c.specialty
    bind_value = specialty_column.type.bind_processor(sqlite_dialect())(assessment.specialty)
    assert bind_value == "physiotherapy"
    stored_value = specialty_column.type.result_processor(sqlite_dialect(), None)(bind_value)
    assert stored_value is Specialty.PHYSIOTHERAPY

    response = SoapAssessmentResponse.model_validate(
        {
            **payload,
            "id": "4f8bb9d3-c27a-4b2a-a0d9-f50dc85c7fa2",
            "clinic_id": "f3a74a4f-6d17-4b49-a997-218cdfb8a2bc",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
    )
    assert response.model_dump(mode="json")["specialty"] == "physiotherapy"

    with pytest.raises(ValidationError):
        SoapAssessmentCreate.model_validate({**payload, "specialty": "not-a-specialty"})


def test_storage_provider_error_is_wrapped_without_provider_detail():
    client = SupabaseStorageClient.__new__(SupabaseStorageClient)
    client.bucket_name = "documents"

    class Storage:
        def from_(self, _bucket):
            return self

        def upload(self, *_args, **_kwargs):
            raise StorageException("sensitive provider response")

    client.client = SimpleNamespace(storage=Storage())

    with pytest.raises(StorageUnavailableError) as caught:
        client.upload_file("file.pdf", b"content", "application/pdf")

    assert "sensitive provider response" not in str(caught.value)


def test_storage_programming_errors_are_not_wrapped():
    client = SupabaseStorageClient.__new__(SupabaseStorageClient)
    client.bucket_name = "documents"

    class Storage:
        def from_(self, _bucket):
            return self

        def upload(self, *_args, **_kwargs):
            raise TypeError("programming error")

    client.client = SimpleNamespace(storage=Storage())

    with pytest.raises(TypeError, match="programming error"):
        client.upload_file("file.pdf", b"content", "application/pdf")
