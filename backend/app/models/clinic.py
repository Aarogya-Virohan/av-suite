import uuid
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, Boolean
from app.models.base import Base, TimestampMixin


class ClinicPlanTier(str, enum.Enum):
    free = "free"
    practice = "practice"
    clinical_pro = "clinical_pro"


class Clinic(Base, TimestampMixin):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    branding_logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    branding_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plan_tier: Mapped[ClinicPlanTier] = mapped_column(Enum(ClinicPlanTier), nullable=False, default=ClinicPlanTier.free)
    is_partner_clinic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    users = relationship("User", back_populates="clinic")
    patients = relationship("Patient", back_populates="clinic")
    exercises = relationship("Exercise", back_populates="clinic")
    prescriptions = relationship("Prescription", back_populates="clinic")
    posture_sessions = relationship("PostureSession", back_populates="clinic")
