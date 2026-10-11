from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.product import EntitlementSource, EntitlementStatus
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.clinic import Clinic


def _entitlement_status_values(enum_cls: type[EntitlementStatus]) -> list[str]:
    return [member.value for member in enum_cls]


def _entitlement_source_values(enum_cls: type[EntitlementSource]) -> list[str]:
    return [member.value for member in enum_cls]


class Product(TimestampMixin, Base):
    """Canonical platform product that can entitle workspace capabilities."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    allowed_clinic_types: Mapped[list[str]] = mapped_column(
        ARRAY(String()).with_variant(JSON(), "sqlite"),
        nullable=False,
        default=lambda: ["clinic"],
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    bundle_links: Mapped[list[PlatformBundleProduct]] = relationship(
        "PlatformBundleProduct",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    workspace_entitlements: Mapped[list[WorkspaceProduct]] = relationship(
        "WorkspaceProduct",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class PlatformBundle(UUIDMixin, TimestampMixin, Base):
    """Named bundle of platform products."""

    __tablename__ = "platform_bundles"

    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product_links: Mapped[list[PlatformBundleProduct]] = relationship(
        "PlatformBundleProduct",
        back_populates="bundle",
        cascade="all, delete-orphan",
    )
    workspace_entitlements: Mapped[list[WorkspaceProduct]] = relationship(
        "WorkspaceProduct",
        back_populates="bundle",
    )


class PlatformBundleProduct(UUIDMixin, TimestampMixin, Base):
    """Join row connecting bundles to canonical products."""

    __tablename__ = "platform_bundle_products"
    __table_args__ = (
        UniqueConstraint(
            "bundle_id",
            "product_id",
            name="uq_platform_bundle_products_bundle_product",
        ),
        Index("ix_platform_bundle_products_product_id", "product_id"),
    )

    bundle_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("platform_bundles.id", ondelete="CASCADE"),
        nullable=False,
    )
    bundle: Mapped[PlatformBundle] = relationship(back_populates="product_links")

    product_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    product: Mapped[Product] = relationship(back_populates="bundle_links")
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WorkspaceProduct(UUIDMixin, TimestampMixin, Base):
    """Product entitlement for one clinic/workspace."""

    __tablename__ = "workspace_products"
    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "product_id",
            name="uq_workspace_products_clinic_product",
        ),
        Index("ix_workspace_products_clinic_status", "clinic_id", "status"),
        Index("ix_workspace_products_product_id", "product_id"),
    )

    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic: Mapped[Clinic] = relationship(back_populates="workspace_products")

    product_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    product: Mapped[Product] = relationship(back_populates="workspace_entitlements")

    status: Mapped[EntitlementStatus] = mapped_column(
        Enum(
            EntitlementStatus,
            name="entitlement_status",
            values_callable=_entitlement_status_values,
        ),
        nullable=False,
        default=EntitlementStatus.ENABLED,
    )
    source: Mapped[EntitlementSource] = mapped_column(
        Enum(
            EntitlementSource,
            name="entitlement_source",
            values_callable=_entitlement_source_values,
        ),
        nullable=False,
        default=EntitlementSource.DIRECT,
    )
    bundle_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("platform_bundles.id", ondelete="SET NULL"),
        nullable=True,
    )
    bundle: Mapped[PlatformBundle | None] = relationship(
        back_populates="workspace_entitlements"
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
