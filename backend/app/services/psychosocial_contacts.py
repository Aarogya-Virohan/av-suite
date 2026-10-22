"""Referral contact directory (SRS 4.3.1, S-D-029).

Clinic-level list of people and services patients are referred to. No
patient data. Contacts are archived, never deleted, so referral actions that
named one keep making sense; those actions also keep their own copy of the
name and role.
"""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.psychosocial import PsychosocialReferralContact
from app.services.psychosocial import audit, error, utcnow

EDITABLE = ("name", "role", "phone", "email", "note")


async def list_contacts(
    db: AsyncSession, clinic_id: uuid.UUID, *, include_archived: bool
) -> list[PsychosocialReferralContact]:
    query = select(PsychosocialReferralContact).where(PsychosocialReferralContact.clinic_id == clinic_id)
    if not include_archived:
        query = query.where(PsychosocialReferralContact.archived_at.is_(None))
    # Active first, then by name; id breaks ties so the order is stable.
    query = query.order_by(
        PsychosocialReferralContact.archived_at.is_not(None),
        func.lower(PsychosocialReferralContact.name),
        PsychosocialReferralContact.id,
    )
    return list((await db.scalars(query)).all())


async def get_contact(db: AsyncSession, clinic_id: uuid.UUID, contact_id: uuid.UUID) -> PsychosocialReferralContact:
    contact = await db.scalar(
        select(PsychosocialReferralContact).where(
            PsychosocialReferralContact.id == contact_id,
            PsychosocialReferralContact.clinic_id == clinic_id,
        )
    )
    if contact is None:
        raise error(status.HTTP_404_NOT_FOUND, "CONTACT_NOT_FOUND", "Referral contact not found.")
    return contact


async def active_contact_for_referral(
    db: AsyncSession, clinic_id: uuid.UUID, contact_id: uuid.UUID
) -> PsychosocialReferralContact:
    contact = await db.scalar(
        select(PsychosocialReferralContact).where(
            PsychosocialReferralContact.id == contact_id,
            PsychosocialReferralContact.clinic_id == clinic_id,
        )
    )
    if contact is None or contact.archived_at is not None:
        raise error(
            422,
            "CONTACT_UNAVAILABLE",
            "This referral contact is not in the clinic's active list.",
        )
    return contact


async def create_contact(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, values: dict
) -> PsychosocialReferralContact:
    contact = PsychosocialReferralContact(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        created_by=user_id,
        updated_by=user_id,
        **{k: values.get(k) for k in EDITABLE},
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.referral_contact_created",
        entity_type="psychosocial_referral_contact",
        entity_id=contact.id,
        details={"name": contact.name, "role": contact.role},
    )
    return contact


async def update_contact(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, contact_id: uuid.UUID, values: dict
) -> PsychosocialReferralContact:
    contact = await get_contact(db, clinic_id, contact_id)
    changed = [k for k in EDITABLE if getattr(contact, k) != values.get(k)]
    if not changed:
        return contact
    for key in changed:
        setattr(contact, key, values.get(key))
    contact.updated_by = user_id
    await db.commit()
    await db.refresh(contact)
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.referral_contact_updated",
        entity_type="psychosocial_referral_contact",
        entity_id=contact.id,
        details={"fields": changed},
    )
    return contact


async def set_archived(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, contact_id: uuid.UUID, archived: bool
) -> PsychosocialReferralContact:
    contact = await get_contact(db, clinic_id, contact_id)
    if (contact.archived_at is not None) == archived:
        return contact
    contact.archived_at = utcnow() if archived else None
    contact.updated_by = user_id
    await db.commit()
    await db.refresh(contact)
    await audit(
        db,
        clinic_id=clinic_id,
        user_id=user_id,
        action="psychosocial.referral_contact_archived" if archived else "psychosocial.referral_contact_restored",
        entity_type="psychosocial_referral_contact",
        entity_id=contact.id,
        details={"name": contact.name},
    )
    return contact
