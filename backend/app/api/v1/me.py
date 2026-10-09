from __future__ import annotations

from sqlalchemy import select

from fastapi import APIRouter

from app.core.dependencies import (
    AuthenticatedContextDep,
    PermissionContextDep,
    SessionDep,
)
from app.core.products import product_for_capability
from app.core.rbac import CAPABILITY_REGISTRY
from app.enums.permission import CapabilityScope
from app.models.clinic import Clinic
from app.models.membership import Membership
from app.models.product import Product, WorkspaceProduct
from app.schemas.envelope import ResponseEnvelope
from app.schemas.platform_context import (
    ActiveProductContext,
    PlatformContextResponse,
    PlatformUserContext,
    WorkspaceContext,
)

router = APIRouter()


@router.get("/me", response_model=ResponseEnvelope[PlatformContextResponse])
async def get_platform_context(
    auth_context: AuthenticatedContextDep,
    permission_context: PermissionContextDep,
    db: SessionDep,
) -> ResponseEnvelope[PlatformContextResponse]:
    membership_rows = (
        await db.execute(
            select(Membership, Clinic)
            .join(Clinic, Clinic.id == Membership.clinic_id)
            .where(Membership.user_id == auth_context.user.id)
            .order_by(Clinic.name, Clinic.id)
        )
    ).all()
    workspaces = [
        WorkspaceContext(
            id=clinic.id,
            name=clinic.name,
            type=clinic.type,
            role=membership.role,
        )
        for membership, clinic in membership_rows
    ]
    active_workspace = WorkspaceContext(
        id=auth_context.clinic.id,
        name=auth_context.clinic.name,
        type=auth_context.clinic.type,
        role=auth_context.membership_role,
    )

    product_rows = (
        await db.execute(
            select(WorkspaceProduct, Product)
            .join(Product, Product.id == WorkspaceProduct.product_id)
            .where(WorkspaceProduct.clinic_id == auth_context.clinic.id)
            .order_by(Product.name, Product.id)
        )
    ).all()
    active_products = [
        ActiveProductContext(
            key=product.slug,
            name=product.name,
            description=product.description,
            status=entitlement.status,
            source=entitlement.source,
            valid_from=entitlement.valid_from,
            valid_until=entitlement.valid_until,
        )
        for entitlement, product in product_rows
        if permission_context.is_product_entitled(product.id)
    ]

    capabilities: list[str] = []
    for capability_key in CAPABILITY_REGISTRY:
        if permission_context.effective_scope(capability_key) == CapabilityScope.NONE:
            continue
        product_id = product_for_capability(capability_key)
        if product_id is not None and not permission_context.is_product_entitled(
            product_id
        ):
            continue
        capabilities.append(capability_key)

    user = PlatformUserContext(
        id=auth_context.user.id,
        email=auth_context.user.email,
        name=f"{auth_context.user.first_name} {auth_context.user.last_name}".strip(),
        role=auth_context.membership_role,
    )
    return ResponseEnvelope(
        data=PlatformContextResponse(
            user=user,
            workspaces=workspaces,
            active_workspace=active_workspace,
            active_products=active_products,
            capabilities=capabilities,
        )
    )
