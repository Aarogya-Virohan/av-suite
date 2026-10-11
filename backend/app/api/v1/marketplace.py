from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.audit import AuditLogServiceDep
from app.core.dependencies import (
    AuthenticatedContextDep,
    SessionDep,
    require_roles,
)
from app.enums.user import UserRole
from app.schemas.envelope import ResponseEnvelope
from app.schemas.marketplace import (
    BundleInstallResponse,
    InstalledProductItem,
    MarketplaceEntitlementResponse,
    ProductCatalogItem,
)
from app.services import marketplace as marketplace_service

router = APIRouter()


@router.get("/products", response_model=ResponseEnvelope[list[ProductCatalogItem]])
async def get_products(
    auth_context: AuthenticatedContextDep,
    db: SessionDep,
) -> ResponseEnvelope[list[ProductCatalogItem]]:
    products = await marketplace_service.list_catalog(
        db, auth_context.clinic.id, auth_context.clinic.type.value
    )
    return ResponseEnvelope(data=products)


@router.get("/installed", response_model=ResponseEnvelope[list[InstalledProductItem]])
async def get_installed_products(
    auth_context: AuthenticatedContextDep,
    db: SessionDep,
) -> ResponseEnvelope[list[InstalledProductItem]]:
    products = await marketplace_service.list_installed(db, auth_context.clinic.id)
    return ResponseEnvelope(data=products)


@router.post(
    "/products/{product_key}/install",
    response_model=ResponseEnvelope[MarketplaceEntitlementResponse],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def install_product(
    product_key: str,
    auth_context: AuthenticatedContextDep,
    db: SessionDep,
    audit_service: AuditLogServiceDep,
) -> ResponseEnvelope[MarketplaceEntitlementResponse]:
    product, entitlement = await marketplace_service.install_product(
        db,
        auth_context.clinic.id,
        auth_context.clinic.type.value,
        product_key,
    )
    await audit_service.log_event(
        clinic_id=auth_context.clinic.id,
        user_id=auth_context.user.id,
        action="product_installed",
        entity_type="marketplace_product",
        details={"product_key": product.slug, "source": "direct"},
    )
    return ResponseEnvelope(
        data=marketplace_service.entitlement_response(product, entitlement)
    )


@router.post(
    "/products/{product_key}/enable",
    response_model=ResponseEnvelope[MarketplaceEntitlementResponse],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def enable_product(
    product_key: str,
    auth_context: AuthenticatedContextDep,
    db: SessionDep,
    audit_service: AuditLogServiceDep,
) -> ResponseEnvelope[MarketplaceEntitlementResponse]:
    product, entitlement = await marketplace_service.set_product_enabled(
        db, auth_context.clinic.id, product_key, True
    )
    await audit_service.log_event(
        clinic_id=auth_context.clinic.id,
        user_id=auth_context.user.id,
        action="product_enabled",
        entity_type="marketplace_product",
        details={"product_key": product.slug},
    )
    return ResponseEnvelope(
        data=marketplace_service.entitlement_response(product, entitlement)
    )


@router.post(
    "/products/{product_key}/disable",
    response_model=ResponseEnvelope[MarketplaceEntitlementResponse],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def disable_product(
    product_key: str,
    auth_context: AuthenticatedContextDep,
    db: SessionDep,
    audit_service: AuditLogServiceDep,
) -> ResponseEnvelope[MarketplaceEntitlementResponse]:
    product, entitlement = await marketplace_service.set_product_enabled(
        db, auth_context.clinic.id, product_key, False
    )
    await audit_service.log_event(
        clinic_id=auth_context.clinic.id,
        user_id=auth_context.user.id,
        action="product_disabled",
        entity_type="marketplace_product",
        details={"product_key": product.slug},
    )
    return ResponseEnvelope(
        data=marketplace_service.entitlement_response(product, entitlement)
    )


@router.post(
    "/bundles/{bundle_key}/install",
    response_model=ResponseEnvelope[BundleInstallResponse],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def install_bundle(
    bundle_key: str,
    auth_context: AuthenticatedContextDep,
    db: SessionDep,
    audit_service: AuditLogServiceDep,
) -> ResponseEnvelope[BundleInstallResponse]:
    bundle, installed_keys, existing_keys = await marketplace_service.install_bundle(
        db,
        auth_context.clinic.id,
        auth_context.clinic.type.value,
        bundle_key,
    )
    await audit_service.log_event(
        clinic_id=auth_context.clinic.id,
        user_id=auth_context.user.id,
        action="bundle_installed",
        entity_type="marketplace_bundle",
        entity_id=bundle.id,
        details={
            "bundle_key": bundle.slug,
            "installed_products": installed_keys,
            "existing_products": existing_keys,
        },
    )
    return ResponseEnvelope(
        data={
            "bundle_key": bundle.slug,
            "installed_products": installed_keys,
            "existing_products": existing_keys,
        }
    )
