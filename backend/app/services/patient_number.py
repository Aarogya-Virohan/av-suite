"""Clinic-scoped patient display-number allocation."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import PatientCounter


async def allocate_patient_display_number(session: AsyncSession, clinic_id: UUID) -> int:
    """Atomically reserve the next number in a clinic's sequence.

    The counter update and patient insert share the caller's transaction. A
    rollback undoes the reservation; a committed allocation is never decremented
    on patient deletion, so committed numbers are not reused.
    """

    insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
    statement = (
        insert(PatientCounter)
        .values(clinic_id=clinic_id, last_number=1)
        .on_conflict_do_update(
            index_elements=[PatientCounter.clinic_id],
            set_={"last_number": PatientCounter.last_number + 1},
        )
        .returning(PatientCounter.last_number)
    )
    return int((await session.execute(statement)).scalar_one())


def format_patient_id(clinic_code: str | None, display_number: int | None) -> str:
    """The Patient ID shown to people: clinic code, then the number padded to 6
    digits ("ADP-000003"). Same text as the CRM screens. Empty when either part
    is missing, so a document leaves the line out instead of printing half of it."""

    if not clinic_code or display_number is None or display_number < 0:
        return ""
    return f"{clinic_code}-{int(display_number):06d}"
