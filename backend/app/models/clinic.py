import uuid
import re
import unicodedata
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, Boolean, Text, event
from app.enums.clinic import ClinicPlanTier, ClinicType
from app.models.base import Base, TimestampMixin


class Clinic(Base, TimestampMixin):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    type: Mapped[ClinicType] = mapped_column(
        Enum(
            ClinicType,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
            name="clinic_type",
            length=20,
        ),
        nullable=False,
        default=ClinicType.CLINIC,
    )
    branding_logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    branding_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plan_tier: Mapped[ClinicPlanTier] = mapped_column(
        Enum(
            ClinicPlanTier,
            values_callable=lambda e: [member.value for member in e],
            name="clinicplantier",
        ),
        nullable=False,
        default=ClinicPlanTier.FREE,
    )
    is_partner_clinic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_documents_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    users = relationship("User", back_populates="clinic", foreign_keys="User.clinic_id")
    memberships = relationship(
        "Membership", back_populates="clinic", cascade="all, delete-orphan"
    )
    patients = relationship("Patient", back_populates="clinic")
    exercises = relationship("Exercise", back_populates="clinic")
    prescriptions = relationship("Prescription", back_populates="clinic")
    posture_sessions = relationship("PostureSession", back_populates="clinic")
    user_permissions = relationship(
        "UserPermission", back_populates="clinic", cascade="all, delete-orphan"
    )
    workspace_products = relationship(
        "WorkspaceProduct", back_populates="clinic", cascade="all, delete-orphan"
    )


@event.listens_for(Clinic, "init")
def _set_default_clinic_slug(target, args, kwargs) -> None:
    """Give newly constructed clinics a stable, unique public slug by default."""
    if kwargs.get("slug"):
        return
    clinic_id = kwargs.get("id") or uuid.uuid4()
    kwargs.setdefault("id", clinic_id)
    name = kwargs.get("name", "clinic")
    normalized = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "clinic"
    kwargs["slug"] = f"{base[:107].rstrip('-')}-{str(clinic_id).replace('-', '')[:12]}"
