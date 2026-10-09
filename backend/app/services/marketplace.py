from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.product import EntitlementSource, EntitlementStatus
from app.models.product import (
    PlatformBundle,
    PlatformBundleProduct,
    Product,
    WorkspaceProduct,
)


def entitlement_response(
    product: Product, entitlement: WorkspaceProduct
) -> dict[str, object]:
    return {
        "product_key": product.slug,
        "status": entitlement.status,
        "source": entitlement.source,
        "valid_from": entitlement.valid_from,
        "valid_until": entitlement.valid_until,
    }


async def list_catalog(
    db: AsyncSession, clinic_id: UUID, workspace_type: str
) -> list[dict[str, object]]:
    statement = (
        select(Product, WorkspaceProduct)
        .outerjoin(
            WorkspaceProduct,
            and_(
                WorkspaceProduct.product_id == Product.id,
                WorkspaceProduct.clinic_id == clinic_id,
            ),
        )
        .where(Product.is_active.is_(True))
        .order_by(Product.name)
    )
    rows = (await db.execute(statement)).all()
    return [
        {
            "product_key": product.slug,
            "name": product.name,
            "description": product.description,
            "allowed_workspace_types": product.allowed_clinic_types,
            "workspace_eligible": workspace_type in product.allowed_clinic_types,
            "installed": entitlement is not None,
            "enabled": entitlement is not None
            and entitlement.status == EntitlementStatus.ENABLED,
        }
        for product, entitlement in rows
    ]


async def list_installed(db: AsyncSession, clinic_id: UUID) -> list[dict[str, object]]:
    statement = (
        select(Product, WorkspaceProduct)
        .join(WorkspaceProduct, WorkspaceProduct.product_id == Product.id)
        .where(WorkspaceProduct.clinic_id == clinic_id)
        .order_by(Product.name)
    )
    rows = (await db.execute(statement)).all()
    return [
        {
            "product_key": product.slug,
            "name": product.name,
            "status": entitlement.status,
            "source": entitlement.source,
            "valid_from": entitlement.valid_from,
            "valid_until": entitlement.valid_until,
        }
        for product, entitlement in rows
    ]


async def _get_product(db: AsyncSession, product_key: str) -> Product:
    product = await db.scalar(
        select(Product).where(
            or_(Product.id == product_key, Product.slug == product_key)
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _check_workspace_eligibility(product: Product, workspace_type: str) -> None:
    if workspace_type not in product.allowed_clinic_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This workspace type is not eligible for the product",
        )


def _entitlement_insert(db: AsyncSession, values: dict[str, object]):
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = postgresql_insert(WorkspaceProduct).values(**values)
        return statement.on_conflict_do_nothing(
            constraint="uq_workspace_products_clinic_product"
        )
    if dialect == "sqlite":
        statement = sqlite_insert(WorkspaceProduct).values(**values)
        return statement.on_conflict_do_nothing(
            index_elements=[
                WorkspaceProduct.clinic_id,
                WorkspaceProduct.product_id,
            ]
        )
    raise RuntimeError(f"Unsupported marketplace database dialect: {dialect}")


async def _fetch_entitlement(
    db: AsyncSession, clinic_id: UUID, product_id: str
) -> WorkspaceProduct:
    entitlement = await db.scalar(
        select(WorkspaceProduct).where(
            WorkspaceProduct.clinic_id == clinic_id,
            WorkspaceProduct.product_id == product_id,
        )
    )
    if entitlement is None:
        raise RuntimeError("Marketplace entitlement insert did not produce a row")
    return entitlement


async def install_product(
    db: AsyncSession,
    clinic_id: UUID,
    workspace_type: str,
    product_key: str,
) -> tuple[Product, WorkspaceProduct]:
    product = await _get_product(db, product_key)
    if not product.is_active:
        raise HTTPException(status_code=409, detail="Product is inactive")
    _check_workspace_eligibility(product, workspace_type)
    await db.execute(
        _entitlement_insert(
            db,
            {
                "clinic_id": clinic_id,
                "product_id": product.id,
                "status": EntitlementStatus.ENABLED,
                "source": EntitlementSource.DIRECT,
                "valid_from": datetime.now(timezone.utc),
            },
        )
    )
    entitlement = await _fetch_entitlement(db, clinic_id, product.id)
    await db.commit()
    return product, entitlement


async def set_product_enabled(
    db: AsyncSession,
    clinic_id: UUID,
    product_key: str,
    enabled: bool,
) -> tuple[Product, WorkspaceProduct]:
    product = await _get_product(db, product_key)
    if enabled and not product.is_active:
        raise HTTPException(status_code=409, detail="Product is inactive")
    entitlement = await db.scalar(
        select(WorkspaceProduct).where(
            WorkspaceProduct.clinic_id == clinic_id,
            WorkspaceProduct.product_id == product.id,
        )
    )
    if entitlement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product is not installed in this workspace",
        )

    entitlement.status = (
        EntitlementStatus.ENABLED if enabled else EntitlementStatus.DISABLED
    )
    await db.commit()
    return product, entitlement


async def install_bundle(
    db: AsyncSession,
    clinic_id: UUID,
    workspace_type: str,
    bundle_key: str,
) -> tuple[PlatformBundle, list[str], list[str]]:
    bundle = await db.scalar(
        select(PlatformBundle).where(PlatformBundle.slug == bundle_key)
    )
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if not bundle.is_active:
        raise HTTPException(status_code=409, detail="Bundle is inactive")

    rows = (
        await db.execute(
            select(PlatformBundleProduct, Product)
            .join(Product, Product.id == PlatformBundleProduct.product_id)
            .where(PlatformBundleProduct.bundle_id == bundle.id)
        )
    ).all()
    for _, product in rows:
        if not product.is_active:
            raise HTTPException(
                status_code=409,
                detail=f"Bundle contains inactive product: {product.slug}",
            )
        _check_workspace_eligibility(product, workspace_type)

    installed_keys: list[str] = []
    existing_keys: list[str] = []
    for link, product in rows:
        insert_result = await db.execute(
            _entitlement_insert(
                db,
                {
                    "clinic_id": clinic_id,
                    "product_id": product.id,
                    "status": EntitlementStatus.ENABLED,
                    "source": EntitlementSource.BUNDLE,
                    "bundle_id": bundle.id,
                    "valid_from": datetime.now(timezone.utc),
                    "valid_until": link.valid_until,
                },
            )
        )
        entitlement = await _fetch_entitlement(db, clinic_id, product.id)
        if insert_result.rowcount == 1:
            installed_keys.append(product.slug)
        else:
            existing_keys.append(product.slug)
            if (
                entitlement.valid_until is not None
                and link.valid_until is not None
                and _as_utc(entitlement.valid_until) < _as_utc(link.valid_until)
            ):
                entitlement.valid_until = link.valid_until

    await db.flush()
    await db.commit()
    return bundle, installed_keys, existing_keys


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
