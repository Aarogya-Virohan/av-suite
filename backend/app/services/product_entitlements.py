from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.products import CANONICAL_PRODUCTS
from app.enums.product import EntitlementSource, EntitlementStatus
from app.models.product import Product, WorkspaceProduct


def active_entitlement_clause(now: datetime):
    """Build the shared SQL predicate for an entitlement effective at a UTC instant."""

    utc_now = (
        now.replace(tzinfo=timezone.utc)
        if now.utcoffset() is None
        else now.astimezone(timezone.utc)
    )
    return and_(
        WorkspaceProduct.status == EntitlementStatus.ENABLED,
        or_(WorkspaceProduct.valid_from.is_(None), WorkspaceProduct.valid_from <= utc_now),
        or_(WorkspaceProduct.valid_until.is_(None), WorkspaceProduct.valid_until > utc_now),
    )


async def ensure_canonical_products(db: AsyncSession) -> None:
    """Ensure the canonical platform product rows exist."""

    existing_ids = set(
        (
            await db.execute(
                select(Product.id).where(
                    Product.id.in_([product["id"] for product in CANONICAL_PRODUCTS])
                )
            )
        )
        .scalars()
        .all()
    )

    for product in CANONICAL_PRODUCTS:
        if product["id"] not in existing_ids:
            db.add(Product(**product))


async def ensure_crm_entitlement(db: AsyncSession, clinic_id: UUID) -> None:
    """Grant or re-enable CRM entitlement for one workspace."""

    await ensure_canonical_products(db)

    existing = await db.scalar(
        select(WorkspaceProduct).where(
            WorkspaceProduct.clinic_id == clinic_id,
            WorkspaceProduct.product_id == "crm",
        )
    )
    if existing is None:
        db.add(
            WorkspaceProduct(
                clinic_id=clinic_id,
                product_id="crm",
                status=EntitlementStatus.ENABLED,
                source=EntitlementSource.DIRECT,
            )
        )
        return

    existing.status = EntitlementStatus.ENABLED
    existing.source = EntitlementSource.DIRECT
