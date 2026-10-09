from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.enums.product import EntitlementSource, EntitlementStatus


class ProductCatalogItem(BaseModel):
    product_key: str
    name: str
    description: str | None
    allowed_workspace_types: list[str]
    workspace_eligible: bool
    installed: bool
    enabled: bool


class InstalledProductItem(BaseModel):
    product_key: str
    name: str
    status: EntitlementStatus
    source: EntitlementSource
    valid_from: datetime | None
    valid_until: datetime | None


class MarketplaceEntitlementResponse(BaseModel):
    product_key: str
    status: EntitlementStatus
    source: EntitlementSource
    valid_from: datetime | None
    valid_until: datetime | None


class BundleInstallResponse(BaseModel):
    bundle_key: str
    installed_products: list[str]
    existing_products: list[str]