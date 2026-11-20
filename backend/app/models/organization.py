from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.enums.clinic import ClinicType
from app.enums.organization import (
    OrganizationStatus,
    OrganizationType,
)
from app.models.base import Base, TimestampMixin, UUIDMixin


class Organization(UUIDMixin, TimestampMixin, Base):
    """Customer account that groups one or more clinics."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "type IN ('individual', 'clinic', 'chain', 'franchise', 'hospital', 'government', 'partner_platform')",
            name="ck_organizations_type",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended')", name="ck_organizations_status"
        ),
        UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OrganizationStatus.ACTIVE,
        server_default=OrganizationStatus.ACTIVE.value,
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    clinics = relationship("Clinic", back_populates="organization")
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMembership(UUIDMixin, TimestampMixin, Base):
    """A user's role at the organization level."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "organization_id", name="uq_organization_memberships_user_org"
        ),
        CheckConstraint(
            "role IN ('org_owner', 'org_admin', 'org_viewer')",
            name="ck_organization_memberships_role",
        ),
        Index(
            "ix_organization_memberships_organization_id", "organization_id"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    user = relationship("User", back_populates="organization_memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


def _organization_type_for_clinic(clinic_type: object) -> OrganizationType:
    value = getattr(clinic_type, "value", clinic_type)
    if value in (ClinicType.SOLO.value, ClinicType.PERSONAL.value):
        return OrganizationType.INDIVIDUAL
    return OrganizationType.CLINIC


@event.listens_for(Session, "before_flush")
def _create_organization_for_new_clinics(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Attach a default organization to each new clinic without one."""

    from app.models.clinic import Clinic

    for clinic in session.new:
        if not isinstance(clinic, Clinic):
            continue
        if clinic.organization_id is not None or clinic.organization is not None:
            continue

        organization = Organization(
            name=clinic.name,
            slug=clinic.slug,
            type=_organization_type_for_clinic(clinic.type),
        )
        session.add(organization)
        clinic.organization = organization
