import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, Boolean, Text
from app.enums.clinic import ClinicPlanTier, ClinicType
from app.models.base import Base, TimestampMixin


class Clinic(Base, TimestampMixin):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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
        Enum(ClinicPlanTier), nullable=False, default=ClinicPlanTier.FREE
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
