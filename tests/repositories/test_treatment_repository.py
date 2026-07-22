from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.treatment import SoapAssessment, TreatmentSession
from app.repositories.treatment import SoapAssessmentRepository, TreatmentSessionRepository


@pytest.mark.asyncio
async def test_treatment_session_repository_create_and_list() -> None:
    """Test TreatmentSessionRepository create and list filtering."""

    mock_session = AsyncMock()
    clinic_id = uuid4()
    patient_id = uuid4()
    therapist_id = uuid4()

    session_obj = TreatmentSession(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        therapist_id=therapist_id,
        treatment_date=datetime.now(timezone.utc),
        treatment="Lower back physical therapy",
    )

    repo = TreatmentSessionRepository(mock_session)

    with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = session_obj
        res = await repo.create({"clinic_id": clinic_id, "treatment": "Lower back physical therapy"})
        assert res.treatment == "Lower back physical therapy"
        mock_create.assert_awaited_once()

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [session_obj]
    mock_session.scalars.return_value = mock_scalars

    sessions = await repo.list_sessions(clinic_id=clinic_id, patient_id=patient_id)
    assert len(sessions) == 1
    mock_session.scalars.assert_called_once()


@pytest.mark.asyncio
async def test_soap_assessment_repository_create_and_list() -> None:
    """Test SoapAssessmentRepository create and list filtering."""

    mock_session = AsyncMock()
    clinic_id = uuid4()
    patient_id = uuid4()

    assessment_obj = SoapAssessment(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        specialty="physiotherapy",
        diagnosis="Lumbar radiculopathy",
        is_reassessment=False,
        form_data={"subjective": "Low back pain"},
    )

    repo = SoapAssessmentRepository(mock_session)

    with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = assessment_obj
        res = await repo.create({"clinic_id": clinic_id, "specialty": "physiotherapy"})
        assert res.specialty == "physiotherapy"
        mock_create.assert_awaited_once()

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [assessment_obj]
    mock_session.scalars.return_value = mock_scalars

    assessments = await repo.list_assessments(clinic_id=clinic_id, patient_id=patient_id, specialty="physiotherapy")
    assert len(assessments) == 1
    mock_session.scalars.assert_called_once()
