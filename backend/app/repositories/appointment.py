from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.appointment import AppointmentStatus
from app.models.appointment import Appointment
from app.repositories.base import BaseRepository


class AppointmentRepository(BaseRepository[Appointment]):
    """Repository for clinic-scoped appointment persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Create an appointment repository bound to the active session."""

        super().__init__(session, Appointment)

    async def get_by_id(self, id: UUID, **kwargs) -> Appointment | None:
        statement = select(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.therapist)
        ).where(Appointment.id == id)
        
        for key, value in kwargs.items():
            statement = statement.where(getattr(Appointment, key) == value)
            
        result = await self.session.scalars(statement)
        return result.first()

    async def list_appointments(
        self,
        *,
        clinic_id: UUID | None = None,
        scheduled_date: date | None = None,
        patient_id: UUID | None = None,
        therapist_id: UUID | None = None,
        status: AppointmentStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Appointment]:
        """Return clinic-scoped appointments with optional date, patient, therapist, and status filters."""

        effective_limit = min(limit, 500)
        statement = select(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.therapist)
        )

        if scheduled_date is not None:
            start_dt = datetime.combine(scheduled_date, time.min, tzinfo=timezone.utc)
            end_dt = datetime.combine(scheduled_date, time.max, tzinfo=timezone.utc)
            statement = statement.where(Appointment.scheduled_at >= start_dt, Appointment.scheduled_at <= end_dt)

        if patient_id is not None:
            statement = statement.where(Appointment.patient_id == patient_id)

        if therapist_id is not None:
            statement = statement.where(Appointment.therapist_id == therapist_id)

        if status is not None:
            statement = statement.where(Appointment.status == status)

        statement = self._apply_clinic_scope(statement, clinic_id).offset(offset).limit(effective_limit)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def soft_cancel(self, db_obj: Appointment) -> Appointment:
        """Soft-cancel an appointment by setting status to CANCELLED."""

        return await self.update(db_obj, {"status": AppointmentStatus.CANCELLED})
