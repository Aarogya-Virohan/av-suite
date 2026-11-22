from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.audit import AuditLogServiceDep
from app.core.dependencies import (
    AuthenticatedContextDep,
    SessionDep,
    require_roles,
)
from app.core.config import settings
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


def _marketplace_writes_open() -> None:
    """BE-3: the marketplace is switched off for launch (M-1, AUD-12).

    Tool access is set per clinic by scripts/clinic_setup; a clinic admin can
    no longer install, enable or disable products from the API.
    """
    if not settings.MARKETPLACE_WRITES_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MARKETPLACE_CLOSED",
                "message": "Tools are managed by AV Suite. Contact support to change your plan.",
            },
        )


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
    dependencies=[Depends(_marketplace_writes_open), Depends(require_roles(UserRole.ADMIN))],
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
    dependencies=[Depends(_marketplace_writes_open), Depends(require_roles(UserRole.ADMIN))],
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
    dependencies=[Depends(_marketplace_writes_open), Depends(require_roles(UserRole.ADMIN))],
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
    dependencies=[Depends(_marketplace_writes_open), Depends(require_roles(UserRole.ADMIN))],
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
