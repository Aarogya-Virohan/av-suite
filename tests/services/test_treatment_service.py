from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.patient import Patient
from app.models.treatment import SoapAssessment, TreatmentSession
from app.models.user import User
from app.schemas.treatment import (
    SoapAssessmentCreate,
    SoapAssessmentUpdate,
    TreatmentSessionCreate,
    TreatmentSessionUpdate,
)
from app.services.treatment import (
    SoapAssessmentService,
    TreatmentNotFoundError,
    TreatmentSessionService,
    TreatmentValidationError,
)


@pytest.mark.asyncio
async def test_create_treatment_session_success() -> None:
    """Test creating a treatment session with valid relations."""

    mock_repo = AsyncMock()
    mock_patient_repo = AsyncMock()
    mock_appt_repo = AsyncMock()
    mock_user_repo = AsyncMock()

    clinic_id = uuid4()
    patient_id = uuid4()
    therapist_id = uuid4()

    mock_patient_repo.get_by_patient_id.return_value = Patient(id=patient_id, clinic_id=clinic_id)
    mock_user_repo.get_by_id.return_value = User(id=therapist_id, clinic_id=clinic_id)

    mock_session = TreatmentSession(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        therapist_id=therapist_id,
        treatment_date=datetime.now(timezone.utc),
        pain_score=5,
        treatment="Spinal mobilization",
    )
    mock_repo.create.return_value = mock_session

    service = TreatmentSessionService(mock_repo, mock_patient_repo, mock_appt_repo, mock_user_repo)
    payload = TreatmentSessionCreate(
        patient_id=patient_id,
        therapist_id=therapist_id,
        treatment_date=datetime.now(timezone.utc),
        pain_score=5,
        treatment="Spinal mobilization",
    )

    result = await service.create_session(clinic_id, payload)
    assert result.pain_score == 5
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_treatment_session_invalid_pain_score() -> None:
    """Test pain score outside 0-10 raises TreatmentValidationError."""

    service = TreatmentSessionService(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())
    payload = TreatmentSessionCreate.model_construct(
        patient_id=uuid4(),
        therapist_id=uuid4(),
        treatment_date=datetime.now(timezone.utc),
        pain_score=15,
        treatment="Invalid pain score",
    )

    with pytest.raises(TreatmentValidationError, match="pain_score must be between 0 and 10"):
        await service.create_session(uuid4(), payload)


@pytest.mark.asyncio
async def test_create_soap_assessment_success() -> None:
    """Test creating a SOAP assessment with JSONB form_data."""

    mock_repo = AsyncMock()
    mock_patient_repo = AsyncMock()
    mock_appt_repo = AsyncMock()

    clinic_id = uuid4()
    patient_id = uuid4()

    mock_patient_repo.get_by_patient_id.return_value = Patient(id=patient_id, clinic_id=clinic_id)

    mock_assessment = SoapAssessment(
        id=uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        specialty="physiotherapy",
        diagnosis="Cervical spondylosis",
        is_reassessment=False,
        form_data={"subjective": "Neck stiffness"},
    )
    mock_repo.create.return_value = mock_assessment

    service = SoapAssessmentService(mock_repo, mock_patient_repo, mock_appt_repo)
    payload = SoapAssessmentCreate(
        patient_id=patient_id,
        specialty="physiotherapy",
        diagnosis="Cervical spondylosis",
        form_data={"subjective": "Neck stiffness"},
    )

    result = await service.create_assessment(clinic_id, payload)
    assert result.specialty == "physiotherapy"
    assert result.form_data["subjective"] == "Neck stiffness"
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_assessment_not_found() -> None:
    """Test get_assessment raises TreatmentNotFoundError when missing."""

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None

    service = SoapAssessmentService(mock_repo, AsyncMock(), AsyncMock())
    assessment_id = uuid4()
    clinic_id = uuid4()

    with pytest.raises(TreatmentNotFoundError, match=f"SOAP assessment '{assessment_id}' not found"):
        await service.get_assessment(clinic_id, assessment_id)
