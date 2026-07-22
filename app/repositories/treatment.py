from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.treatment import SoapAssessment, TreatmentSession
from app.repositories.base import BaseRepository


class TreatmentSessionRepository(BaseRepository[TreatmentSession]):
    """Repository for clinic-scoped TreatmentSession operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, TreatmentSession)

    async def list_by_patient(
        self,
        patient_id: UUID,
        *,
        clinic_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TreatmentSession]:
        """List treatment sessions for a patient scoped to clinic."""

        effective_limit = min(limit, 500)
        statement = select(TreatmentSession).where(
            TreatmentSession.patient_id == patient_id
        )
        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())


class SoapAssessmentRepository(BaseRepository[SoapAssessment]):
    """Repository for clinic-scoped SoapAssessment operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository bound to session."""

        super().__init__(session, SoapAssessment)

    async def list_by_patient(
        self,
        patient_id: UUID,
        *,
        clinic_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> list[SoapAssessment]:
        """List SOAP assessments for a patient scoped to clinic."""

        effective_limit = min(limit, 500)
        statement = select(SoapAssessment).where(
            SoapAssessment.patient_id == patient_id
        )
        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())
