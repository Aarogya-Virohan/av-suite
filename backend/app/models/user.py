import uuid
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, ForeignKey
from app.models.base import Base, TimestampMixin

class UserRole(str, enum.Enum):
    admin = "admin"
    physio = "physio"
    patient = "patient"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    clinic = relationship("Clinic", back_populates="users")
    patient_profile = relationship("Patient", back_populates="user", uselist=False)
    prescriptions_given = relationship("Prescription", back_populates="physio")
