from __future__ import annotations

from typing import Optional, Tuple, List
from uuid import UUID

from sqlalchemy import String, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exercise import Exercise
from app.models.patient import Patient
from app.models.prescription import Prescription, PrescriptionItem
from app.repositories.base import BaseRepository
from app.schemas.prescription import PrescriptionCreate, PrescriptionPatch


class PrescriptionRepository(BaseRepository[Prescription]):
    """Repository for clinic-scoped prescription operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Create a prescription repository bound to the active session."""
        super().__init__(session, Prescription)

    async def create_prescription(
        self, clinic_id: UUID, physio_id: UUID, prescription_in: PrescriptionCreate
    ) -> Prescription:
        db_prescription = Prescription(
            clinic_id=clinic_id,
            patient_id=prescription_in.patient_id,
            physio_id=physio_id,
            physio_notes=prescription_in.physio_notes,
            status=prescription_in.status,
        )
        self.session.add(db_prescription)
        await self.session.flush()

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
                    note=item.note,
                )
            )

        if db_items:
            self.session.add_all(db_items)

        await self.session.commit()
        await self.session.refresh(db_prescription)
        return db_prescription

    async def get_prescription_by_id(
        self, clinic_id: UUID, prescription_id: UUID
    ) -> Optional[Prescription]:
        query = (
            select(Prescription)
            .where(
                Prescription.id == prescription_id, Prescription.clinic_id == clinic_id
            )
            .options(
                selectinload(Prescription.items).selectinload(
                    PrescriptionItem.exercise
                ),
                selectinload(Prescription.patient),
                selectinload(Prescription.physio),
                selectinload(Prescription.clinic),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_prescriptions(
        self,
        clinic_id: UUID,
        physio_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Prescription], int]:
        query = select(Prescription).where(Prescription.clinic_id == clinic_id)
        if physio_id:
            query = query.where(Prescription.physio_id == physio_id)
        if patient_id:
            query = query.where(Prescription.patient_id == patient_id)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = (
                query.outerjoin(Prescription.patient)
                .outerjoin(Prescription.items)
                .outerjoin(PrescriptionItem.exercise)
                .where(
                    or_(
                        Patient.first_name.ilike(search_pattern),
                        Patient.last_name.ilike(search_pattern),
                        func.concat(Patient.first_name, " ", Patient.last_name).ilike(
                            search_pattern
                        ),
                        Exercise.title.ilike(search_pattern),
                        Prescription.physio_notes.ilike(search_pattern),
                        Prescription.status.ilike(search_pattern),
                        Prescription.id.cast(String).ilike(search_pattern),
                    )
                )
            )

        count_subquery = query.with_only_columns(Prescription.id).distinct().subquery()
        count_query = select(func.count()).select_from(count_subquery)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            query.options(
                selectinload(Prescription.items).selectinload(
                    PrescriptionItem.exercise
                ),
                selectinload(Prescription.patient),
            )
            .distinct(Prescription.created_at, Prescription.id)
            .order_by(Prescription.created_at.desc(), Prescription.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update_prescription_items(
        self, prescription_id: UUID, patch: PrescriptionPatch
    ) -> None:
        await self.session.execute(
            delete(PrescriptionItem).where(
                PrescriptionItem.prescription_id == prescription_id
            )
        )

        db_items = []
        for item in patch.items:
            db_items.append(
                PrescriptionItem(
                    prescription_id=prescription_id,
                    exercise_id=item.exercise_id,
                    sets=item.sets,
                    reps=item.reps,
                    hold=item.hold,
                    frequency=item.frequency,
                    hold_angle=item.hold_angle,
                    note=item.note,
                )
            )
        if db_items:
            self.session.add_all(db_items)

    async def update_pdf_key(self, rx: Prescription, pdf_filename: str) -> None:
        rx.pdf_key = pdf_filename
        await self.session.commit()

    async def delete_prescription(self, prescription: Prescription) -> None:
        await self.delete(prescription)
        await self.session.commit()
